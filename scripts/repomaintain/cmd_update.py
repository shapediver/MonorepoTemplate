import functools
import json
import os.path
import re
import typing as t

import git
import semantic_version as semver

from utils import (
    LernaComponent, PrintMessageError, app_on_error, ask_user, cmd_helper, copy, echo,
    join_paths, link_npmrc_file, move, reinstall_dependencies, remove, run_process,
    unlink_npmrc_file)

# Type of single Lerna component version.
ComponentVersion = t.TypedDict('ComponentVersion', {
    'name': str,
    'version': str,
})
InternalDependency = t.TypedDict('InternalDependency', {
    'name': str,
    'location': str,
    'dependencies': t.List[ComponentVersion]
})


def run(no_git: bool) -> bool:
    # Initialize repo object and search for Lerna components.
    repo, root, components = cmd_helper()

    # Stop processing when open changes in package.json files have been detected.
    if not no_git:
        check_open_changes(repo)

    # Register cleanup handler for error case. We want to undo the update call as much as possible
    # (node_modules changes persist however).
    app_on_error.append(functools.partial(cleanup_on_error, components))

    # Create backups of package.json and package-lock.json files, and link .npmrc file.
    backup_package_files(components)
    link_npmrc_file(root, components)

    # Prepare Lerna components for dependency updates and auditing. Remove Lerna managed components
    # from package.json files to ignore them during updating and auditing.
    prepare_components(components)

    for component in components:
        echo(f"\nUpdating and auditing dependencies of component {component['name']}:")

        if os.path.exists(join_paths(component['location'], "node_modules")):
            try:
                # Shows general information about newer versions if possible.
                run_process("npm outdated", component['location'])
            except RuntimeError:
                # npm-outdated returns code `1` when updates are available...
                # But since this command is just used to show additional information about
                # dependency versions anyway, we just ignore all runtime errors here.
                pass

        # Update all dependencies according to semver constraints and installs missing packages.
        # The new versions are updated in package.json and package-lock.json.
        run_process("npm update --save --no-fund --no-audit", component['location'])

        try:
            # Tries to fix known vulnerabilities in dependencies.
            run_process("npm audit fix --audit-level=high --no-fund", component['location'])
        except RuntimeError:
            # Vulnerabilities where found that could not be fixed automatically and require manual
            # intervention. Prints a warning message and wait for further input.
            echo(
                """
WARNING:
  NPM audit was unable to fix all vulnerabilities of level 'high' or 'critical'.
  The logging output above should provide more information.

  Please fix this issue manually before continuing this script.
""",
                'wrn')
            answers = ask_user([{
                'type': "confirm",
                'name': "proceed",
                'message': "Proceed?",
                'default': True,
            }])
            if not answers['proceed']:
                echo("Process got stopped by the user.", 'wrn')
                return False

    # Cleanup - We have to add previously removed internal dependencies again.
    cleanup_on_success(components)

    # Unfortunately, `npm update` always installs dependencies inside each component, which causes
    # problems with Lerna. Thus, we remove the `node_modules` folders and reinstall dependencies.
    echo("\nInstalling updated dependencies:")
    reinstall_dependencies(root)

    # Commit changes
    if not no_git:
        commit_changes(repo, components)

    return True


def check_open_changes(repo: git.Repo) -> None:
    """ Checks if there are any open changes in package.json files. """
    # Regex to extract the prefix of a semver (e.g. '~', '<=')
    regex = re.compile(r'.*package\.json$')

    changed_and_new_files = repo.index.diff(None) + repo.index.diff("HEAD")
    for item in changed_and_new_files:
        if regex.match(item.a_path):
            raise PrintMessageError(
                """ERROR:
  Your index contains uncommitted changes in package.json files.
  Please commit or stash them.
""")


def backup_package_files(components: t.List[LernaComponent]) -> None:
    """ Creates backups of all component's package and lock files. """
    for component in components:
        # Backup package.json file
        pkg_json_file = join_paths(component['location'], "package.json")
        copy(pkg_json_file, pkg_json_file + ".bak", must_exist=True)

        # Backup package-lock.json file
        pkg_lock_file = join_paths(component['location'], "package-lock.json")
        copy(pkg_lock_file, pkg_lock_file + ".bak")


def prepare_components(components: t.List[LernaComponent]) -> None:
    """
    Remove linked internal dependencies from package.json files.

    Modifies the package.json file of all Lerna components. When a component depends on another
    internally managed component (dependency or dev-dependency), the dependency reference is
    removed. Since internal dependencies are always managed directly by Lerna, we do not want to
    include them in the NPM update process.

    An exception to this is when an old version of an internal dependency is referenced.
    """
    echo("\nAnalyzing Lerna components ...")

    component_map: t.Dict[str, LernaComponent] = {cmp['name']: cmp for cmp in components}

    def update_internal_dependency(pkg_json_dep_ref: t.Dict[str, t.Any]) -> None:
        """
        Helper function to process a linked internal dependency.

        First, it is determined if the versions of the internal dependency "matches". A dependency
        is seen as "matching" when the current dependency version is within the range of the
        specified version according to semantic versioning. When a dependency does not match, it is
        assumed that the respective version of the dependency has been published and thus, no update
        of the package.json object is performed. Afterwards, should the versions match, the
        specified dependency removed from the package.json object.
        """
        # Stop if versions do not match
        if semver.Version(internal_dependency['version']) not in semver.NpmSpec(pkg_json_dep_ref[name]):
            echo(
                f"""
Component {internal_dependency['name']}:
  Dependency {name}@{pkg_json_dep_ref[name]} does not reference the local version '{internal_dependency['version']}'.
  It is assumed that {name}@{pkg_json_dep_ref[name]} has been published to the ShapeDiver GitHub
  registry or NPM registry.
""",
                'wrn')
        else:
            # Remove the property from the JSON object
            del pkg_json_dep_ref[name]

    for component in components:
        pkg_json_file = join_paths(component['location'], "package.json")

        # Open and parse package.json file.
        with open(pkg_json_file, 'r') as reader:
            pkg_json_content: t.Dict[str, t.Any] = json.load(reader)

        # Remove all internal dependencies that have a matching version.
        for name, internal_dependency in component_map.items():
            if "dependencies" in pkg_json_content and name in pkg_json_content['dependencies']:
                update_internal_dependency(pkg_json_content['dependencies'])
            elif "devDependencies" in pkg_json_content and name in pkg_json_content['devDependencies']:
                update_internal_dependency(pkg_json_content['devDependencies'])

        # Write changes to package.json file.
        with open(pkg_json_file, 'w') as writer:
            writer.write(json.dumps(pkg_json_content, indent=2) + "\n")


def commit_changes(repo: git.Repo, components: t.List[LernaComponent]) -> None:
    """
    Commit version changes to Git.

    Add the staging changes of package.json and package-lock.json files from all Lerna components to
    the index and writes them to a new commit.
    """
    index = repo.index

    for component in components:
        index.add(join_paths(component['location'], "package.json"))
        index.add(join_paths(component['location'], "package-lock.json"))

    if len(repo.index.diff("HEAD")) > 0:
        index.commit("Update dependencies", skip_hooks=True)
        echo("\nCreated a new commit.")
    else:
        echo("\nNo updates found.")


def cleanup_on_success(components: t.List[LernaComponent]) -> None:
    """ Restores the removed references of internal dependencies. """
    for component in components:
        pkg_json_file = join_paths(component['location'], "package.json")
        pkg_lock_file = join_paths(component['location'], "package-lock.json")

        # Open and parse package.json file.
        with open(pkg_json_file, 'r') as reader:
            pkg_json_updated_versions: t.Dict[str, t.Any] = json.load(reader)

        # Open and parse package.json.bak file.
        with open(pkg_json_file + ".bak", 'r') as reader:
            pkg_json_original: t.Dict[str, t.Any] = json.load(reader)

        # Replace the version string of all lerna managed dependencies in the package.json with
        # their absolute path.
        if "dependencies" in pkg_json_updated_versions:
            for dependency, version in pkg_json_updated_versions['dependencies'].items():
                pkg_json_original['dependencies'][dependency] = version
        if "devDependencies" in pkg_json_updated_versions:
            for dependency, version in pkg_json_updated_versions['devDependencies'].items():
                pkg_json_original['devDependencies'][dependency] = version

        # Write changes to package.json file.
        with open(pkg_json_file, 'w') as writer:
            writer.write(json.dumps(pkg_json_original, indent=2) + "\n")

        # Remove backup files.
        remove(pkg_json_file + ".bak")
        remove(pkg_lock_file + ".bak")

        # Remove linked .npmrc file.
        unlink_npmrc_file(component)


def cleanup_on_error(components: t.List[LernaComponent]) -> None:
    """ Restores package.json backups and removes linked .npmrc files. """
    for component in components:
        # Restore backup of package.json file.
        pkg_json_file = join_paths(component['location'], "package.json")
        move(pkg_json_file + ".bak", pkg_json_file)

        # Restore backup of package-lock.json file.
        pkg_lock_file = join_paths(component['location'], "package-lock.json")
        move(pkg_lock_file + ".bak", pkg_lock_file)

        # Remove linked .npmrc file.
        unlink_npmrc_file(component)
