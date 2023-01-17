import json
import os
import shlex
import shutil
import sys
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


# Helper class to stop the CLI and print the error message without the stack trace.
class PrintMessageError(Exception):
    pass


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
    Invokes the given command in a new subprocess through a shell.

    WARNING:
    Make sure to use `shlex.quote` for all user input that is part of the command to properly escape
    whitespace and shell metacharacters!
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
        out = DEVNULL if not show_output and not get_output else None
        err = STDOUT if out is not None else None

        # Activate shell mode on Windows systems, but disable it on Unix systems.
        if sys.platform == "win32" or sys.platform == "cygwin":
            shell = True
        else:
            shell = False

        # We have to use `shell=True` for Windows support. However, this opens security risks. Thus,
        # we use `shlex` to create a shell-escaped version of args that can be used safely.
        cmd = shlex.split(args)

        process = run(cmd, cwd=cwd, capture_output=get_output, stdout=out, stderr=err, shell=shell)
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


def reinstall_dependencies(root: str) -> None:
    """ Re-installs dependencies in all Lerna components including root. """
    run_process("npm i", root, get_output=False)
    run_process("npx lerna clean --yes", root, get_output=False)
    run_process("npx lerna bootstrap", root, get_output=False)


def cmd_helper(no_git: bool) -> t.Tuple[git.Repo, str, t.List[LernaComponent]]:
    """
    Helper function to initialize a CLI command.

    :param no_git: When `True` checks the dirty-state of the Git repository.
    :raise PrintMessageError: When `no_git=True` and repository has open changes.
    :return: [0] Git repository object. [1] Absolute path to the repository's root. [2] A list of
    all Lerna managed components.
    """
    repo = git_repo()

    # The absolute path of the Git repository's root folder.
    root = git_repo().git.rev_parse("--show-toplevel")

    # Stop processing when open changes have been detected.
    if not no_git and repo.is_dirty():
        raise PrintMessageError(
            """ERROR:
  Your index contains uncommitted changes.
  Please commit or stash them.
""")

    # Get list of all components that are managed by Lerna
    components = get_lerna_components(root)
    echo(f"Found {len(components)} components managed by Lerna.")

    # Add the repo's root to the component list.
    components.append({
        "name": "root",
        "version": "",
        "private": True,
        "location": root,
    })

    return repo, root, components
