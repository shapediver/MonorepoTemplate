import functools
import os
import shlex
import typing as t

from utils import (
    LernaComponent, app_on_error, cmd_helper, copy, echo, link_npmrc_file, move,
    reinstall_dependencies, remove, run_process)


def run(
        target: t.Literal['major', 'minor', 'patch'],
        dep_filter: str,
        dep_exclude: t.Optional[str],
) -> bool:
    # Initialize repo object and search for Lerna components.
    repo, root, components = cmd_helper(no_git=True)

    # Register cleanup handler for error case - We want to undo the upgrade call.
    app_on_error.append(functools.partial(cleanup_on_error, components))

    # Create backup of package.json files and link .npmrc file.
    backup_package_files(components)
    link_npmrc_file(root, components)

    # Build command to upgrade dependencies.
    cmd = f"npx ncu --upgrade --target {shlex.quote(target)} --filter {shlex.quote(dep_filter)}"
    if dep_exclude is not None:
        cmd += f" --reject {shlex.quote(dep_exclude)}"

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
        remove(pkg_json_bak_file + ".bak")

        # Remove linked .npmrc file.
        npmrc_file = os.path.join(component['location'], ".npmrc")
        remove(npmrc_file)


def cleanup_on_error(components: t.List[LernaComponent]) -> None:
    """ Restores package.json backups and removes linked .npmrc files. """
    for component in components:
        # Restore backup of package.json file.
        pkg_json_file = os.path.join(component['location'], "package.json")
        move(pkg_json_file + ".bak", pkg_json_file)

        # Remove linked .npmrc file.
        npmrc_file = os.path.join(component['location'], ".npmrc")
        remove(npmrc_file)
