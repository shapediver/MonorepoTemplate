import functools
import os
import shlex
import typing as t

from utils import (
    LernaComponent, app_on_error, cmd_helper, copy, echo, link_npmrc_file, reinstall_dependencies,
    run_process)


def run(
        target: t.Literal["major", "minor", "patch"],
        dep_filter: str,
        dep_exclude: t.Optional[str],
) -> bool:
    # Initialize repo object and search for Lerna components.
    repo, root, components = cmd_helper(True)

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
            run_process(cmd, cwd=component["location"], get_output=False)
        except RuntimeError as e:
            print(e)

    # Cleanup - We have to remove the created backups of package.json files.
    cleanup_on_success(components)

    # Install upgraded dependencies.
    echo("\nInstalling upgraded dependencies:")
    reinstall_dependencies(root)

    return True


def backup_package_files(components: t.List[LernaComponent]) -> None:
    """
    Creates backups of all component's package.json files.

    :raise PrintMessageError: When a Lerna component does not have a package.json file.
    """
    for component in components:
        # Backup package.json file
        package_json = os.path.join(component["location"], "package.json")
        copy(package_json, package_json + ".bak")


def cleanup_on_success(components: t.List[LernaComponent]) -> None:
    """ Removes package.json backups and linked .npmrc files. """
    for component in components:
        # Remove backup of package.json file
        pkg_json_file = os.path.join(component["location"], "package.json")
        os.remove(pkg_json_file + ".bak")

        # Remove linked .npmrc file
        os.remove(os.path.join(component["location"], ".npmrc"))


def cleanup_on_error(components: t.List[LernaComponent]) -> None:
    """ Restores package.json backups and removes linked .npmrc files. """
    for component in components:
        # Restore backup of package.json file
        pkg_json_file = os.path.join(component["location"], "package.json")
        if os.path.exists(pkg_json_file + ".bak"):
            copy(pkg_json_file + ".bak", pkg_json_file)
            os.remove(pkg_json_file + ".bak")

        # Remove linked .npmrc file
        npmrc = os.path.join(component["location"], ".npmrc")
        if os.path.exists(npmrc):
            os.remove(npmrc)
