import functools
import json
import re
import typing as t

import git
import semantic_version as semver
from utils import (
    CliConfig,
    LernaComponent,
    PrintMessageError,
    app_on_error,
    ask_user,
    cmd_helper,
    copy,
    echo,
    join_paths,
    load_cli_config,
    move,
    remove,
    run_process,
)


def run(no_git: bool) -> bool:
    # Initialize repo object and search for Lerna components.
    repo, root, components = cmd_helper()

    # Stop processing when open changes in package.json files have been detected.
    if not no_git:
        check_open_changes(repo)

    # Load CLI config file.
    config = load_cli_config(root)

    # Register cleanup handler for error case. We want to undo the update call as much as possible
    # (node_modules changes persist however).
    app_on_error.append(functools.partial(cleanup_on_error, root, components))

    # Create backups of package.json and the pnpm-lock.yaml files.
    backup_package_files(root, components)

    # Prepare Lerna components for dependency updates and auditing. Remove Lerna managed components
    # from package.json files to ignore them during updating and auditing.
    prepare_components(components, config)

    # Update all dependencies according to sem-ver constraints and installs missing packages.
    # The new versions are updated in package.json and pnpm-lock.json.
    echo("\nUpdating dependencies of all components:")
    run_process("pnpm update -r", root)

    # Print information output about newer dependency versions outside of semv-ver range.
    echo("\nSearching for newer packages outside of specified sem-ver range:")
    try:
        run_process("pnpm outdated -r", root)
    except RuntimeError:
        # pnpm-outdated returns non-zero status code when packages where found.
        pass

    problems_found = False
    for component in components:
        echo(f"\nAuditing dependencies of component {component['name']}:")
        try:
            # Searches for vulnerabilities in dependencies.
            run_process(
                "pnpm audit --prod --audit-level high --ignore-registry-errors",
                component["location"],
            )
        except RuntimeError:
            problems_found = True

    # Warn user if vulnerabilities where found that require manual intervention.
    if problems_found:
        echo(
            """
WARNING:
  pNPM audit found one or more dependencies with vulnerabilities of level 'high' or 'critical'.
  The logging output above should provide more information.
""",
            "wrn",
        )
        answers = ask_user(
            [
                {
                    "type": "confirm",
                    "name": "proceed",
                    "message": "Proceed?",
                    "default": True,
                }
            ]
        )
        if not answers["proceed"]:
            echo("Process got stopped by the user.", "wrn")
            return False

    # Cleanup - We have to add previously removed internal dependencies again.
    cleanup_on_success(root, components, config)

    # We have to update the pnpm-lock.yaml file since the pnpm-update command removed all internal
    # dependencies.
    echo("\nInstalling updated dependencies:")
    run_process("pnpm install", root)

    # Commit changes
    if not no_git:
        commit_changes(repo, root, components)

    return True


def check_open_changes(repo: git.Repo) -> None:
    """Checks if there are any open changes in package.json files."""
    # Regex to extract the prefix of a semver (e.g. '~', '<=')
    regex = re.compile(r".*package\.json$")

    changed_and_new_files = repo.index.diff(None) + repo.index.diff("HEAD")
    for item in changed_and_new_files:
        if regex.match(item.a_path):
            raise PrintMessageError(
                """ERROR:
  Your index contains uncommitted changes in package.json files.
  Please commit or stash them.
"""
            )


def backup_package_files(root: str, components: t.List[LernaComponent]) -> None:
    """Creates backups of all component's package.json files and the lock file."""
    pnpm_lock_file = join_paths(root, "pnpm-lock.yaml")
    copy(pnpm_lock_file, pnpm_lock_file + ".bak", must_exist=True)

    for component in components:
        pkg_json_file = join_paths(component["location"], "package.json")
        copy(pkg_json_file, pkg_json_file + ".bak", must_exist=True)


def prepare_components(components: t.List[LernaComponent], config: CliConfig) -> None:
    """
    Remove linked internal dependencies from package.json files.

    Modifies the package.json file of all Lerna components. When a component depends on another
    internally managed component (dependency or dev-dependency), the dependency reference is
    removed. pNPM replaces the version of internal dependencies by a `workspace` identifier, which
    we do not want to use. Therefore we do not include them in the NPM update process.

    An exception to this is when an old version of an internal dependency is referenced.
    """
    echo("\nPreparing components ...")

    component_map: t.Dict[str, LernaComponent] = {
        cmp["name"]: cmp for cmp in components
    }

    def update_internal_dependency(pkg_json_dep_ref: t.Dict[str, t.Any]) -> None:
        """
        Helper function to process a linked internal dependency.

        First, it is determined if the versions of the internal dependency "matches". A dependency
        is seen as "matching" when the current dependency version is within the range of the
        specified version according to semantic versioning. When a dependency does not match, it is
        assumed that the respective version of the dependency has been published and thus, no
        update of the package.json object is performed. Afterwards, should the versions match, the
        specified dependency is removed from the package.json object.
        """
        # Stop if versions do not match
        if semver.Version(internal_dependency["version"]) not in semver.NpmSpec(
            pkg_json_dep_ref[name]
        ):
            echo(
                f"""
Component {internal_dependency['name']}:
  Dependency {name}@{pkg_json_dep_ref[name]} does not reference the local version '{internal_dependency['version']}'.
  It is assumed that {name}@{pkg_json_dep_ref[name]} has been published to the ShapeDiver GitHub
  registry or NPM registry.
""",
                "wrn",
            )
        else:
            # Remove the property from the JSON object
            del pkg_json_dep_ref[name]

    for component in components:
        pkg_json_file = join_paths(component["location"], "package.json")

        # Open and parse package.json file.
        with open(pkg_json_file, "r") as reader:
            pkg_json_content: t.Dict[str, t.Any] = json.load(reader)

        # Remove all internal dependencies that have a matching version.
        for name, internal_dependency in component_map.items():
            if (
                "dependencies" in pkg_json_content
                and name in pkg_json_content["dependencies"]
            ):
                update_internal_dependency(pkg_json_content["dependencies"])
            elif (
                "devDependencies" in pkg_json_content
                and name in pkg_json_content["devDependencies"]
            ):
                update_internal_dependency(pkg_json_content["devDependencies"])

        # Write changes to package.json file.
        with open(pkg_json_file, "w") as writer:
            writer.write(json.dumps(pkg_json_content, indent=config["indent"]) + "\n")


def commit_changes(
    repo: git.Repo, root: str, components: t.List[LernaComponent]
) -> None:
    """
    Commit version changes to Git.

    Add the staging changes of package.json and pnpm-lock.yaml files the index and writes them to
    a new commit.
    """
    index = repo.index

    index.add(join_paths(root, "pnpm-lock.yaml"))

    for component in components:
        index.add(join_paths(component["location"], "package.json"))

    if len(repo.index.diff("HEAD")) > 0:
        index.commit("Update dependencies", skip_hooks=True)
        echo("\nCreated a new commit.")
    else:
        echo("\nNo updates found.")


def cleanup_on_success(
    root: str, components: t.List[LernaComponent], config: CliConfig
) -> None:
    """Restores the removed references of internal dependencies."""
    for component in components:
        pkg_json_file = join_paths(component["location"], "package.json")

        # Open and parse package.json file.
        with open(pkg_json_file, "r") as reader:
            pkg_json_updated: t.Dict[str, t.Any] = json.load(reader)

        # Open and parse package.json.bak file.
        with open(pkg_json_file + ".bak", "r") as reader:
            pkg_json_original: t.Dict[str, t.Any] = json.load(reader)

        # Apply the updated versions to the original package.json file.
        if "dependencies" in pkg_json_updated:
            for dependency, version in pkg_json_updated["dependencies"].items():
                pkg_json_original["dependencies"][dependency] = version
        if "devDependencies" in pkg_json_updated:
            for dependency, version in pkg_json_updated["devDependencies"].items():
                pkg_json_original["devDependencies"][dependency] = version

        # Write changes to package.json file.
        with open(pkg_json_file, "w") as writer:
            writer.write(json.dumps(pkg_json_original, indent=config["indent"]) + "\n")

        # Remove backup files.
        remove(pkg_json_file + ".bak")
        remove(join_paths(root, "pnpm-lock.yaml") + ".bak")


def cleanup_on_error(root: str, components: t.List[LernaComponent]) -> None:
    """Restores package.json backups and removes linked .npmrc files."""
    pnpm_lock_file = join_paths(root, "pnpm-lock.yaml")
    move(pnpm_lock_file + ".bak", pnpm_lock_file)

    for component in components:
        pkg_json_file = join_paths(component["location"], "package.json")
        move(pkg_json_file + ".bak", pkg_json_file)
