import json
import os
import shutil
import typing as t
from subprocess import DEVNULL, STDOUT, run

import click
import git

# Type of single Lerna component
LernaComponent = t.TypedDict('LernaComponent', {
    "name": str,
    "version": str,
    "private": bool,
    "location": str,
})

# Holds functions that should be executed when the application completed successfully.
app_on_success: list[(): None] = []

# Holds functions that should be executed when the application stopped due to an error, or was
# stopped by the user (CTRL+c).
app_on_error: list[(): None] = []


def echo(
        out: t.Union[str, list, dict],
        lvl: t.Literal["log", "wrn", "err"] = "log"
) -> None:
    """ Prints the given text or object to the terminal. """
    # Prettify exceptions, list and dict objects.
    if type(out) is str:
        pass
    elif type(out) is list or dict:
        out = json.dumps(out, indent=2)

    # Determine the foreground color according to the log-level.
    if lvl == "log":
        fg = "magenta"
    elif lvl == "wrn":
        fg = "yellow"
    else:
        fg = "red"  # lvl == "err"

    click.secho(out, fg=fg)


def git_repo() -> git.Repo:
    """ Instantiates and returns a Git Repository object. """
    file_path = os.path.realpath(__file__)
    return git.Repo(file_path, search_parent_directories=True)


def run_process(
        args: str,
        cwd: str,
        *,
        get_output: bool = True,
        show_output: bool = True,
) -> t.Optional[str]:
    """
    Invokes the given command in a new subprocess.

    :arg args: The command to execute.
    :arg cwd: Absolute path from which the command should be run.
    :arg get_output: When set to `True`, the output is captured and returned. Captured output is not
    shown in the terminal.
    :arg show_output: Shows the command output in the terminal when set to `True`. This parameter is
    ignored when `get_output=True`.
    :raise KeyboardInterrupt: When the process received an interrupt signal.
    :raise RuntimeError: When the subprocess returned a non-zero exit code.
    :return: The decoded captured output when `get_output=True`; otherwise `None`.
    """
    try:
        # We cannot disable the output when we also want to capture it
        stdout = DEVNULL if not show_output and not get_output else None
        stderr = STDOUT if stdout is not None else None

        process = run(args.split(), cwd=cwd, capture_output=get_output, stdout=stdout, stderr=stderr)
    except KeyboardInterrupt:
        # This catches SIG_INT (Ctrl+C)
        raise KeyboardInterrupt(f"Process '{args}' got interrupted.")
    except RuntimeError:
        raise RuntimeError(f"Error when running Process '{args}'.")
    else:
        if process.returncode > 0:
            exp = RuntimeError(f"Process '{args}' returned exit code '{process.returncode}'.")

            # Add details about command error if available
            if process.stderr is not None:
                raise exp from RuntimeError(process.stderr.decode("utf-8"))
            else:
                raise exp from None
        elif get_output:
            return process.stdout.decode("utf-8")
        else:
            return None


def get_lerna_components(root: str) -> t.List[LernaComponent]:
    """
    Returns information about all components that are managed by Lerna.

    :param root: The path of the Git repository's root folder.
    :return: List of all local components in topological order.
    """
    res = run_process("npx lerna list --all --toposort --json", root)
    return json.loads(res)


def copy(src: str, dst: str) -> None:
    """
    Copies the given file or symlink to the specified location; overrides if it already exists.

    :param src: The path of the source file or symlink to copy.
    :param dst: The destination path.
    :raise FileNotFoundError: When the source file was not found.
    """
    if os.path.islink(src):
        # Manual removal of already existing symlink
        if os.path.exists(dst):
            os.remove(dst)

        link = os.readlink(src)
        os.symlink(link, dst)
    else:
        # Always overrides
        shutil.copy(src, dst)
