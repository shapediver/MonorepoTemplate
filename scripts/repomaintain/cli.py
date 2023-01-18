import traceback
import typing as t

import click

from cmd_publish import run as run_publish
from cmd_update import run as run_update
from cmd_upgrade import run as run_upgrade
from utils import PrintMessageError, app_on_error, app_on_success, echo


def handler(status: t.Literal['ok', 'err']) -> None:
    """ Process all cleanup functions that have been registered for the respective status. """
    fns = app_on_success if status == 'ok' else app_on_error
    for fn in fns:
        fn()


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
def main() -> None:
    pass


@main.command()
@click.option("--no-git", type=bool, help="Don't run any Git commands.", is_flag=True)
def update(no_git) -> None:
    """
    Update and audit dependencies.

    Updates and audits all NPM dependencies of Lerna managed components. The update respects each
    dependency's semantic versioning specified in the component's 'package.json' file. This process
    changes primarily the 'package-lock.json' file.
    """
    cmd_wrapper(run_update, no_git)


@main.command()
@click.option(
    "-t",
    "--target",
    type=click.Choice(['major','minor', 'patch'], case_sensitive=False),
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
def upgrade(target, dep_filter, dep_exclude) -> None:
    """
    Upgrades dependencies to the latest versions.

    Upgrades one or more NPM dependencies in all Lerna managed components. The upgrade process keeps
    semantic versioning policies but ignores specified versions.

    Example:
    `upgrade -t major -f X` upgrades dependency X from "^16.0.4" to "^18.2.0" in package.json.

    THIS PROCESS DOES NOT AUDIT THE NEW DEPENDENCIES OR UPDATES THE LOCK FILE!
    Run the `update` command to finalize the changes.
    """
    cmd_wrapper(run_upgrade, target, dep_filter, dep_exclude)


@main.command()
@click.option(
    "--dry-run",
    type=bool,
    help="Doesn't publish or commit anything.",
    is_flag=True)
def publish(dry_run) -> None:
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
    cmd_wrapper(run_publish, dry_run)


if __name__ == "__main__":
    main()
