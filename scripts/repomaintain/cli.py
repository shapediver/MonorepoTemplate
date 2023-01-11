import traceback
import typing as t

import click

from cmd_update import run as run_update
from utils import app_on_error, app_on_success, echo


def handler(status: t.Literal["ok", "err"]) -> None:
    """ Process all cleanup functions that have been registered for the respective status. """
    fns = app_on_success if status == "ok" else app_on_error
    for fn in fns:
        fn()


def cmd_wrapper(cmd_fn: t.Callable[[t.Any], bool], *args) -> None:
    """ Wrapper around a command function that allows to use `click` functions. """
    try:
        res = cmd_fn(*args)
        handler("ok" if res else "err")
    except KeyboardInterrupt:
        echo("Process got interrupted.", "wrn")
        handler("err")
    except:
        traceback.print_exc()
        handler("err")


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


if __name__ == "__main__":
    main()
