import functools
import shlex
import typing as t

from utils import (
    LernaComponent,
    app_on_error,
    cmd_helper,
    copy,
    echo,
    fetch_globally_pinned_dependencies,
    join_paths,
    link_npmrc_file,
    move,
    remove,
    run_process,
    unlink_npmrc_file,
)


def run_upgrade(
    target: t.Literal["latest", "minor", "patch"],
    dep_filter: str,
    dep_exclude: t.Optional[str],
) -> bool:
    # Initialize repo object and search for Lerna components.
    _, root, components = cmd_helper()

    # Fetch globally pinned dependencies. These packages have to be ignored in the upgrade process.
    pinned_deps = fetch_globally_pinned_dependencies(root)
    pinned_deps_string = ",".join([p["name"] for p in pinned_deps])

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
    cmd = f"npx ncu --upgrade --packageManager npm --target {shlex.quote(target)} --filter {shlex.quote(dep_filter)}"
    if reject != ",":
        cmd += f" --reject {shlex.quote(reject)}"

    for component in components:
        echo(f"\nUpgrading dependencies of component {component['name']}:")
        run_process(cmd, cwd=component["location"])

    # Cleanup - We have to remove the created backups of package.json files.
    cleanup_on_success(components)

    # Install upgraded dependencies.
    echo("\nInstalling upgraded dependencies:")
    run_process("pnpm install", root)

    # Log information about next steps.
    echo(
        """
Dependency upgrade successfully applied.

Please complete the following steps next:
  1. Test the application(s) and make sure that the new versions do not cause problems. When you
    encounter issues and cannot fix them, downgrade the version of the problematic dependencies.
    (Do not forget to run `pnpm install` after downgrading versions to apply the changes).
  
  2. Persist your changes by running `npm run apply-upgrade`.
""",
        "wrn",
    )

    return True


def run_apply():
    repo, root, _ = cmd_helper()
    index = repo.index

    # The general idea is, that the user runs the upgrade command before testing the new dependency
    # versions via unit test or whatever. This might result in file changes. Therefore, we have to
    # add all open changes and new files to the index when the user wants to persist the upgrade.
    changed_and_new_files = " ".join(
        item.a_path for item in index.diff(None) + index.diff("HEAD")
    )
    # NOTE repo.index.add and .remove have problems with deleted files -> call git directly!
    run_process(f"git add {changed_and_new_files}", root)

    # Create a new commit.
    if len(repo.index.diff("HEAD")) > 0:
        index.commit("Upgrade dependencies", skip_hooks=True)
        echo("\nCreated a new commit.")
    else:
        echo("\nNo upgrades found.")

    return True


def backup_package_files(components: t.List[LernaComponent]) -> None:
    """Creates backups of all component's package.json files."""
    for component in components:
        # Backup package.json file
        package_json = join_paths(component["location"], "package.json")
        copy(package_json, package_json + ".bak")


def cleanup_on_success(components: t.List[LernaComponent]) -> None:
    """Removes package.json backups and linked .npmrc files."""
    for component in components:
        # Remove backup of package.json file.
        pkg_json_bak_file = join_paths(component["location"], "package.json.bak")
        remove(pkg_json_bak_file)

        # Remove linked .npmrc file.
        unlink_npmrc_file(component)


def cleanup_on_error(components: t.List[LernaComponent]) -> None:
    """Restores package.json backups and removes linked .npmrc files."""
    for component in components:
        # Restore backup of package.json file.
        pkg_json_file = join_paths(component["location"], "package.json")
        move(pkg_json_file + ".bak", pkg_json_file)

        # Remove linked .npmrc file.
        unlink_npmrc_file(component)
