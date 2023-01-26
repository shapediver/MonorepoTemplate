import functools
import os
import shlex
import typing as t

from utils import (
    LernaComponent, app_on_error, cmd_helper, copy, echo, fetch_globally_pinned_dependencies,
    link_npmrc_file, move, reinstall_dependencies, remove, run_process, unlink_npmrc_file)


def run(
        target: t.Literal['major', 'minor', 'patch'],
        dep_filter: str,
        dep_exclude: t.Optional[str],
) -> bool:
    # Initialize repo object and search for Lerna components.
    repo, root, components = cmd_helper(no_git=True)

    # Fetch globally pinned dependencies. These packages have to be ignored in the upgrade process.
    pinned_deps = fetch_globally_pinned_dependencies(root)
    pinned_deps_string = ",".join([p['name'] for p in pinned_deps])

    # Register cleanup handler for error case - We want to undo the upgrade call.
    app_on_error.append(functools.partial(cleanup_on_error, components))

    # Create backup of package.json files and link .npmrc file.
    backup_package_files(components)
    link_npmrc_file(root, components)

    # Exclude packages that are globally pinned, or dependencies that have been explicitly excluded
    # by the user.
    #
    # Note:
    #  ncu is very flexible here, so no problem mixing a comma-separated-list with space-separated
    #  components, a leading comma, or duplicated dependencies.
    reject = pinned_deps_string + "," + (dep_exclude or "")

    # Build command to upgrade dependencies.
    cmd = f"npx ncu --upgrade --target {shlex.quote(target)} --filter {shlex.quote(dep_filter)}"
    if reject != ",":
        cmd += f" --reject {shlex.quote(reject)}"

    for component in components:
        echo(f"\nUpgrading dependencies of component {component['name']}:")

        try:
            run_process(cmd, cwd=component['location'])
        except RuntimeError as e:
            print(e)

    # Cleanup - We have to remove the created backups of package.json files.
    cleanup_on_success(components)

    # Install upgraded dependencies.
    echo("\nInstalling upgraded dependencies:")
    reinstall_dependencies(root)

    return True


def backup_package_files(components: t.List[LernaComponent]) -> None:
    """ Creates backups of all component's package.json files. """
    for component in components:
        # Backup package.json file
        package_json = os.path.join(component['location'], "package.json")
        copy(package_json, package_json + ".bak")


def cleanup_on_success(components: t.List[LernaComponent]) -> None:
    """ Removes package.json backups and linked .npmrc files. """
    for component in components:
        # Remove backup of package.json file.
        pkg_json_bak_file = os.path.join(component['location'], "package.json.bak")
        remove(pkg_json_bak_file)

        # Remove linked .npmrc file.
        unlink_npmrc_file(component)


def cleanup_on_error(components: t.List[LernaComponent]) -> None:
    """ Restores package.json backups and removes linked .npmrc files. """
    for component in components:
        # Restore backup of package.json file.
        pkg_json_file = os.path.join(component['location'], "package.json")
        move(pkg_json_file + ".bak", pkg_json_file)

        # Remove linked .npmrc file.
        unlink_npmrc_file(component)
