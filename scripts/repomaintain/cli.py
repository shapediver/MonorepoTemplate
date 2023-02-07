import sys
import traceback
import typing as t

import click

from cmd_publish import run as run_publish
from cmd_sd_global import run as run_sd_global
from cmd_update import run as run_update
from cmd_upgrade import run_upgrade, run_apply as run_apply_upgrade
from utils import PrintMessageError, app_on_error, app_on_success, echo


def handler(status: t.Literal['ok', 'err']) -> None:
    """ Process all cleanup functions that have been registered for the respective status. """
    if status == 'ok':
        for fn in app_on_success:
            fn()
    else:
        for fn in app_on_error:
            fn()
        sys.exit(1)


def cmd_wrapper(cmd_fn: t.Callable[[t.Any], bool], *args) -> None:
    """ Wrapper around a command function that allows to use `click` functions. """
    try:
        res = cmd_fn(*args)
        handler('ok' if res else 'err')
    except KeyboardInterrupt:
        echo("Process got interrupted.", 'wrn')
        handler('err')
    except PrintMessageError as e:
        echo(str(e), 'err')
        handler('err')
    except:
        traceback.print_exc()
        handler('err')


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option("--no-git", type=bool, help="Don't run any Git commands.", is_flag=True)
def update(no_git: bool) -> None:
    """
    Update and audit dependencies.

    Updates and audits all NPM dependencies of Lerna managed components. The update respects each
    dependency's semantic versioning specified in the component's 'package.json' file. This process
    changes primarily the 'package-lock.json' file.
    """
    cmd_wrapper(run_update, no_git)


@cli.command()
@click.option(
    "-t",
    "--target",
    type=click.Choice(['major', 'minor', 'patch'], case_sensitive=False),
    prompt="Target version",
    help="Determines the version to upgrade to.")
@click.option(
    "-f",
    "--filter",
    "dep_filter",
    type=str,
    help="Include only packages matching the given string, wildcard, /regex/ or comma-delimited "
         "list.",
    default="*")
@click.option(
    "-x",
    "--exclude",
    "dep_exclude",
    type=str,
    help="Exclude packages matching the given string, wildcard, /regex/ or comma-delimited list.",
    default=None)
def upgrade(target: str, dep_filter: str, dep_exclude: str) -> None:
    """
    Upgrades dependencies to the latest versions.

    Upgrades one or more NPM dependencies in all Lerna managed components. The upgrade process keeps
    semantic versioning policies but ignores specified versions.

    Example:
    `upgrade -t major -f X` upgrades dependency X from "^16.0.4" to "^18.2.0" in package.json.

    THIS PROCESS DOES NOT AUDIT THE NEW DEPENDENCIES OR UPDATES THE LOCK FILE!
    Run the `apply-upgrade` command to finalize the changes.
    """
    cmd_wrapper(run_upgrade, target.lower(), dep_filter, dep_exclude)


@cli.command()
def apply_upgrade() -> None:
    """
    Finalizes the `upgrade` command.

    This command should be called when the `upgrade` command was executed and after the user made
    sure that the new dependency versions do not break the application(s).

    Finalizes the version upgrade process by auditing the dependencies, updating the
    package-lock.json file of Lerna managed components and committing all open changes to Git.
    """
    cmd_wrapper(run_update, True)
    cmd_wrapper(run_apply_upgrade)


@cli.command()
@click.option(
    "--dry-run",
    type=bool,
    help="Doesn't publish anything.",
    is_flag=True)
@click.option(
    "--no-git",
    type=bool,
    help="Disable Git commit and tag creation.",
    is_flag=True)
@click.option(
    "--always-ask",
    type=bool,
    help="Always asks the user and sets answers as default values for future invocations.",
    is_flag=True)
@click.option(
    "--skip-existing",
    type=bool,
    help="Doesn't publish components when the target version already exists.",
    is_flag=True)
@click.option(
    "--keep-version",
    type=bool,
    help="Doesn't increment component versions.",
    is_flag=True)
def publish(
        dry_run: bool,
        no_git: bool,
        always_ask: bool,
        skip_existing: bool,
        keep_version: bool,
) -> None:
    """
    Publishes one or more components.

    Interactive command to release one or more Lerna managed components.
    The workflow is as follows:

      1. Ask the user which components to release, which version(s) to use, and to which registries
    the components should be published to.

      2. Call `scripts/pre-publish-global.sh`.

      3. Increment versions in package.json files. This also updates the version of linked internal
    dependencies but keeps semantic versioning policies.

      4. For each component selected for publishing:

        4a. Call `scripts/pre-publish.sh`.

        4b. Publish the component to the selected registries.

        4c. Call `scripts/post-publish.sh`.

      5. Create Git commit and tags (skipped when flag `--dry-run` is set).

      6. Call `scripts/post-publish-global.sh`.

      7. Push current Git branch and the created tags to 'origin' (skipped when flag `--dry-run` is
    set).
    """
    cmd_wrapper(run_publish, dry_run, no_git, always_ask, skip_existing, keep_version)


@cli.command()
@click.argument(
    "command",
    type=click.Choice(['list-pinned', 'update-pinned'], case_sensitive=False))
def sd_global(command: str) -> None:
    """
    Interact with the ShapeDiver global configuration.

    COMMANDS:

      [list-pinned] List all globally pinned TypeScript dependencies.

      [update-pinned] Apply globally pinned TypeScript dependencies to local package.json files and
    update the repository list of the Confluence page with all pinned dependencies that are
    currently used by at least on Lerna managed component.
    """
    cmd_wrapper(run_sd_global, command.lower())


if __name__ == "__main__":
    cli()
