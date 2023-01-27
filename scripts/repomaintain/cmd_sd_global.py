import json
import os
import re
import typing as t

import git

from utils import (
    PrintMessageError, cmd_helper, echo, fetch_globally_pinned_dependencies, git_repo,
    update_globally_pinned_dependencies)


def run(cmd: t.Literal['list-pinned', 'update-pinned']) -> bool:
    # Run sub-command specified by user.
    if cmd == 'list-pinned':
        return cmd_list_pinned()
    elif cmd == 'update-pinned':
        return cmd_update_pinned()
    else:
        echo(f"\nERROR:\n  Invalid command argument '{cmd}'.", 'err')
        return False


def cmd_list_pinned() -> bool:
    """ List all globally pinned TypeScript dependencies. """
    # The absolute path of the Git repository's root folder.
    root = git_repo().git.rev_parse("--show-toplevel")

    # Try to connect to Confluence and load all pinned dependencies.
    pinned_deps = fetch_globally_pinned_dependencies(root)

    # Log the pinned dependencies.
    if len(pinned_deps) > 0:
        msg = "The following packages have been pinned globally:"
        for dep in pinned_deps:
            msg += f"""
  * {dep['name']}@{dep['version']}:
    {dep['reason']}
"""
    else:
        msg = "There are currently no globally pinned packages :)"

    echo(msg)
    return True


def cmd_update_pinned() -> bool:
    """
    Manage globally pinned dependencies.

    Apply globally pinned TypeScript dependencies to local package.json files and update the
    repository list of the Confluence page with all pinned dependencies that are currently used by
    at least on Lerna managed component.
    """
    # Initialize repo object and search for Lerna components.
    repo, root, components = cmd_helper()

    # Stop processing when open changes in package.json files have been detected.
    check_open_changes(repo)

    # Try to connect to Confluence and load all pinned dependencies.
    pinned_deps = fetch_globally_pinned_dependencies(root)

    # Stop when no dependencies have been pinned.
    if len(pinned_deps) == 0:
        echo("There are currently no globally pinned packages :)")
        return True

    # Stores the name of all globally pinned dependencies that are currently in use.
    pinned_deps_in_use: t.Set[str] = {*()}

    def update_pinned_dep(pkg_json_dep_ref: t.Dict[str, t.Any]) -> None:
        """ Set the local version of the dependency to the global one. """
        pkg_json_dep_ref[name] = version
        pinned_deps_in_use.add(name)

    # Check all components for globally pinned packages.
    for component in components:
        pkg_json_file = os.path.join(component['location'], "package.json")

        # Open and parse package.json file.
        with open(pkg_json_file, 'r') as reader:
            pkg_json_content: t.Dict[str, t.Any] = json.load(reader)

        for dep in pinned_deps:
            name, version = dep['name'], dep['version']
            if "dependencies" in pkg_json_content and name in pkg_json_content['dependencies']:
                update_pinned_dep(pkg_json_content['dependencies'])
            elif "devDependencies" in pkg_json_content and name in pkg_json_content['devDependencies']:
                update_pinned_dep(pkg_json_content['devDependencies'])

        # Write changes to package.json file.
        with open(pkg_json_file, 'w') as writer:
            writer.write(json.dumps(pkg_json_content, indent=2) + "\n")

    # Log which dependencies have been changed.
    msg = "\nThe versions of the following globally pinned packages have been enforced:"
    for dep in filter(lambda p: p['name'] in pinned_deps_in_use, pinned_deps):
        msg += f"\n  * {dep['name']}@{dep['version']}"
    echo(msg, 'wrn')

    # Try to connect to Confluence and load all pinned dependencies.
    update_globally_pinned_dependencies(repo, root, pinned_deps_in_use)

    # Commit package.json files when changes have been enforced.
    if repo.is_dirty():
        index = repo.index
        for component in components:
            index.add(os.path.join(component['location'], "package.json"))

        # Create a new commit.
        if len(repo.index.diff("HEAD")) > 0:
            index.commit("Update globally pinned dependencies")
            echo("\nCreated a new commit.")

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
