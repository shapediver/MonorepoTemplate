import json
import os
import re
import shlex
import shutil
import sys
import typing as t
from subprocess import DEVNULL, STDOUT, run

import click
import git
from PyInquirer import prompt
from atlassian import Confluence
from bs4 import BeautifulSoup
from requests import HTTPError

ATLASSIAN_URL = "https://shapediver.atlassian.net"
ATLASSIAN_SPACE_KEY = "SS"  # ShapeDiver Scrum
ATLASSIAN_PAGE_TITLE = "Pinned Dependency Versions"
ATLASSIAN_DOC_VERSION = "1"  # Specified in the Confluence page

# Typed structure of the property `repomaintain` in `root/scope.json`.
CliConfig = t.TypedDict('CliConfig', {
    'publish_mode': t.Optional[t.Literal['all', 'independent']],
    'publish_tag_name': t.Optional[str],
})

# Type of single dependency that is globally pinned in Confluence.
GloballyPinnedDependency = t.TypedDict('GloballyPinnedDependency', {
    'name': str,
    'version': str,
    # 'author': str,
    'reason': str,
    'repositories': t.List[str]
})

# Type of single Lerna component
LernaComponent = t.TypedDict('LernaComponent', {
    'name': str,
    'version': str,
    'private': bool,
    'location': str,
})

# Holds functions that should be executed when the application completed successfully.
app_on_success: list[(): None] = []

# Holds functions that should be executed when the application stopped due to an error, or was
# stopped by the user (CTRL+c).
app_on_error: list[(): None] = []


# Helper class to stop the CLI and print the error message without the stack trace.
class PrintMessageError(Exception):
    pass


def load_cli_config(root: str) -> CliConfig:
    """ Reads and parses the CLI configuration properties. """
    cli_config_file = os.path.join(root, "scope.json")

    # Open and parse scope.json file.
    with open(cli_config_file, 'r') as reader:
        cli_config_content: t.Dict[str, t.Any] = json.load(reader)

    mapped: CliConfig = {
        'publish_mode': None,
        'publish_tag_name': None,
    }

    # Extract config and map values
    if 'repomaintain' in cli_config_content:
        config = cli_config_content['repomaintain']
    else:
        return mapped

    if 'publish_mode' in config:
        if config['publish_mode'] == 'all' or config['publish_mode'] == 'independent':
            mapped['publish_mode'] = config['publish_mode']

    if 'publish_tag_name' in config:
        mapped['publish_tag_name'] = config['publish_tag_name']

    return mapped


def update_cli_config(
        root: str,
        *,
        publish_mode: t.Optional[t.Literal['all', 'independent']] = None,
        publish_tag_name: t.Optional[str] = None,
) -> None:
    """ Overrides all CLI config properties that are specified and not `None`. """
    cli_config_file = os.path.join(root, "scope.json")

    # Open and parse scope.json file.
    with open(cli_config_file, 'r') as reader:
        cli_config_content: t.Dict[str, t.Any] = json.load(reader)

    # Extract config and map values
    config: CliConfig
    if 'repomaintain' in cli_config_content:
        config = cli_config_content['repomaintain']
    else:
        config = {
            'publish_mode': None,
            'publish_tag_name': None,
        }

    # Set values
    if publish_mode is not None:
        config['publish_mode'] = publish_mode
    if publish_tag_name is not None:
        config['publish_tag_name'] = publish_tag_name

    # Set or update cli config
    cli_config_content.update({'repomaintain': config})

    # Write changes to scope.json file.
    with open(cli_config_file, 'w') as writer:
        writer.write(json.dumps(cli_config_content, indent=2) + "\n")


def echo(
        out: t.Union[str, list, dict],
        lvl: t.Literal['log', 'wrn', 'err'] = 'log'
) -> None:
    """ Prints the given text or object to the terminal. """
    # Prettify exceptions, list and dict objects.
    if type(out) is str:
        pass
    elif type(out) is list or dict:
        out = json.dumps(out, indent=2)

    # Determine the foreground color according to the log-level.
    if lvl == 'log':
        fg = 'magenta'
    elif lvl == 'wrn':
        fg = 'yellow'
    else:
        fg = 'red'  # lvl == 'err'

    click.secho(out, fg=fg)


def git_repo() -> git.Repo:
    """ Instantiates and returns a Git Repository object. """
    file_path = os.path.realpath(__file__)
    return git.Repo(file_path, search_parent_directories=True)


def ask_user(questions: t.List[t.Dict[str, t.Any]]) -> t.Dict[str, t.Any]:
    """ Wrapper around `PyInquirer.prompt` that catches user interrupts. """
    answers = prompt(questions)
    if len(answers) == 0:
        raise KeyboardInterrupt
    else:
        return answers


def run_process(
        args: str,
        cwd: str,
        *,
        get_output: bool = False,
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
        if sys.platform == 'win32' or sys.platform == 'cygwin':
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
                raise exp from RuntimeError(process.stderr.decode('utf-8'))
            else:
                raise exp from None
        elif get_output:
            return process.stdout.decode('utf-8')
        else:
            return None


def get_lerna_components(root: str) -> t.List[LernaComponent]:
    """
    Returns information about all components that are managed by Lerna.

    :param root: The path of the Git repository's root folder.
    :return: List of all local components in topological order.
    """
    res = run_process("npx lerna list --all --toposort --json", root, get_output=True)
    return json.loads(res)


def copy(src: str, dst: str, *, must_exist: bool = False) -> None:
    """
    Copies the given file or symlink to the specified location; overrides if it already exists.

    :param src: The path of the source file or symlink to copy.
    :param dst: The destination path.
    :param must_exist: Stops when set to `true` and the source file was not found.
    :raise FileNotFoundError: When the source file was not found and `must_exist=True`.
    """
    # Stop when file was not found
    if not must_exist and not os.path.exists(src):
        print(f"COPY NOPE: {must_exist}, {os.path.exists(src)}")
        return

    if os.path.islink(src):
        # Manual removal of already existing symlink
        if os.path.exists(dst):
            os.remove(dst)

        link = os.readlink(src)
        os.symlink(link, dst)
    else:
        # Always overrides
        shutil.copy(src, dst)


def move(src: str, dst: str, *, must_exist: bool = False) -> None:
    """
    Moves the given file or symlink from the specified location; overrides if it already exists.

    :param src: The path of the source file or symlink to move.
    :param dst: The destination path.
    :param must_exist: Stops when set to `true` and the source file was not found.
    :raise FileNotFoundError: When the source file was not found and `must_exist=True`.
    """
    copy(src, dst, must_exist=must_exist)
    remove(src, must_exist=must_exist)


def remove(src: str, *, must_exist: bool = False) -> None:
    """
    Removes the given file or symlink.

    :param src: The path of the file or symlink to remove.
    :param must_exist: Stops when set to `true` and the file was not found.
    :raise FileNotFoundError: When the file was not found and `must_exist=True`.
    """
    # Stop when file was not found
    if not must_exist and not os.path.exists(src):
        return

    os.remove(src)


def link_npmrc_file(
        root: str,
        components: t.List[LernaComponent],
        *,
        must_exist: bool = False,
) -> None:
    """
    Tries to copy the .npmrc file of the repository's root to each component.

    :param root: The path of the Git repository's root folder.
    :param components: The Lerna components that should get a copy of the .npmrc file.
    :param must_exist: Stops when set to `true` and the file was not found.
    :raise FileNotFoundError: When the file was not found and `must_exist=True`.
    """
    npmrc = os.path.join(root, ".npmrc")
    if os.path.exists(npmrc):
        for component in [c for c in components if c['name'] != "root"]:
            copy(npmrc, os.path.join(component['location'], ".npmrc"))
    elif must_exist:
        raise PrintMessageError(f"\nERROR:\n  Could not link {npmrc}: File does not exist.")
    else:
        echo(f"Could not read {npmrc}: File does not exist.", 'wrn')


def unlink_npmrc_file(component: LernaComponent) -> None:
    """ Removes a linked .npmrc file if found. """
    if component['name'] != "root":
        # Remove linked .npmrc file.
        npmrc_file = os.path.join(component['location'], ".npmrc")
        remove(npmrc_file)


def reinstall_dependencies(root: str) -> None:
    """ Re-installs dependencies in all Lerna components including root. """
    run_process("npm i", root)
    run_process("npx lerna clean --yes", root)
    run_process("npx lerna bootstrap", root)


def get_confluence_page(root: str) -> t.Tuple[Confluence, str, BeautifulSoup]:
    """
    Try to connect to Confluence, fetch the page and return the parsed HTML content.

    :param root: The path of the Git repository's root folder.
    :return: [0] The connection to Confluence. [1] The ID of the Confluence page. [2] The HTML
    wrapper around the content of the Confluence page.
    :raise PrintMessageError: When the page cannot get fetched or parsed, or when the ShapeDiver
    version of the page does not match.
    """
    # Check existence of configuration file.
    atlassianrc = os.path.join(root, ".atlassianrc")
    if not os.path.exists(atlassianrc):
        raise PrintMessageError(f"\nERROR:\n  Could not read {atlassianrc}: File does not exist.")

    # Open and parse configuration file.
    with open(atlassianrc, 'r') as reader:
        config: t.TypedDict[str, str] = json.load(reader)

    # Instantiate client, no authentication performed yet.
    confluence = Confluence(
        url=ATLASSIAN_URL,
        username=config['username'],
        password=config['api_token'],
        cloud=True)

    # Check if user is authenticated and try to fetch the Confluence page.
    try:
        page_id = confluence.get_page_id(space=ATLASSIAN_SPACE_KEY, title=ATLASSIAN_PAGE_TITLE)
    except HTTPError as e:
        raise PrintMessageError(
            f"""ERROR:
  Could not establish connection to Confluence service.
  {str(e)}
""")

    # Make sure that the Confluence page exists.
    if page_id is None:
        raise PrintMessageError(
            f"""ERROR:
  Could not find Confluence page '{ATLASSIAN_PAGE_TITLE}' in space '{ATLASSIAN_SPACE_KEY}'.
  Please check if these settings have been updated in the Git repository 'MonorepoTemplate' and
  downstream the changes if necessary.
""")

    # Load the content data of the page (is in HTML format)
    page_json = confluence.get_page_by_id(page_id, expand='body.storage')
    soup = BeautifulSoup(page_json['body']['storage']['value'], 'html.parser')

    # Check the ShapeDiver version of the Confluence page. This prevents old versions of this CLI
    # tool to mess with the page.
    # sd_version = soup.find(attrs={"data-panel-type": "info"})
    sd_version_element = soup.find(text=re.compile(r'^Processor Version:\s*\d+\s*$'))
    sd_version = sd_version_element.split(": ")[1].strip()
    if sd_version != ATLASSIAN_DOC_VERSION:
        raise PrintMessageError("""
        ERROR:
  You are currently using an old version of the CLI tool. Please downstream the changes made in the
  Git repository 'MonorepoTemplate' before running this command again.
""")

    return confluence, page_id, soup


def fetch_globally_pinned_dependencies(root: str) -> t.List[GloballyPinnedDependency]:
    """ Fetches all globally pinned typeScript packages and returns their information. """
    # Connect, fetch and parse Confluence page.
    _, _, page = get_confluence_page(root)

    # Globally pinned versions are specified in an HTML table element. The first row represents the
    # header row and can be skipped. The other rows contain each a single pinned dependency.
    rows = page.find('table').find_all('tr')
    globally_pinned_dependencies: t.List[GloballyPinnedDependency] = []
    try:
        for tr in rows[1:]:
            td = tr.find_all('td')
            globally_pinned_dependencies.append({
                'name': td[0].string,
                'version': td[1].string,
                # 'author': td[2].find('ri:user')['ri:account-id'],
                'reason': td[3].string,
                'repositories': [i.strip() for i in (td[4].string or "").split(',') if not i.isspace() and i != ""]
            })
    except Exception:
        raise PrintMessageError(
            f"""ERROR:
  Could not extract information from the Confluence page '{ATLASSIAN_PAGE_TITLE}'.
  Please check if the formatting of the Confluence page is off, or if there are updates available in
  the Git repository 'MonorepoTemplate'.
""")

    return globally_pinned_dependencies


def update_globally_pinned_dependencies(
        repo: git.Repo,
        root: str,
        pinned_deps_in_use: t.Set[str],
) -> None:
    """
    Updates the repositories list of globally pinned dependencies.

    :param repo: The Git repository object.
    :param root: The path of the Git repository's root folder.
    :param pinned_deps_in_use: A list of names from all globally pinned packages that is used by at
    least one Lerna managed component in this repository.
    :return:
    """
    # Connect, fetch and parse Confluence page.
    confluence, page_id, page = get_confluence_page(root)

    # Get the remote name of this Git repository.
    repo_name = repo.remotes.origin.url.split('.git')[0].split('/')[-1]

    # Globally pinned versions are specified in an HTML table element. The first row represents the
    # header row and can be skipped. The other rows contain each a single pinned dependency.
    rows = page.find('table').find_all('tr')
    changes_applied = False
    try:
        for tr in rows[1:]:
            # Extract package name and currently registered repositories.
            td = tr.find_all('td')
            name = td[0].string
            repositories = [i.strip() for i in (td[4].string or "").split(',') if not i.isspace() and i != ""]

            # Add this repository name if used and not listed, and remove it if listed but not used.
            if name in pinned_deps_in_use and repo_name not in repositories:
                repositories.append(repo_name)
                changes_applied = True
            elif name not in pinned_deps_in_use and repo_name in repositories:
                repositories.remove(repo_name)
                changes_applied = True

            td[4].string = ", ".join(repositories)
    except Exception:
        raise PrintMessageError(
            f"""ERROR:
  Could not extend information in the Confluence page '{ATLASSIAN_PAGE_TITLE}'.
  Please check if the formatting of the Confluence page is off, or if there are updates available in
  the Git repository 'MonorepoTemplate'.
""")

    # Upload updated content of the Confluence page when something has changed. This way, we prevent
    # the creation of unnecessary page versions in Confluence.
    if changes_applied:
        confluence.update_page(page_id, ATLASSIAN_PAGE_TITLE, str(page))

    echo("\nThe repository list of the Confluence page has been updated successfully.")


def cmd_helper() -> t.Tuple[git.Repo, str, t.List[LernaComponent]]:
    """
    Helper function to initialize a CLI command.

    :return: [0] Git repository object. [1] Absolute path to the repository's root. [2] A list of
    all Lerna managed components.
    """
    repo = git_repo()

    # The absolute path of the Git repository's root folder.
    root = repo.git.rev_parse("--show-toplevel")

    # Get list of all components that are managed by Lerna
    components = get_lerna_components(root)
    echo(f"Found {len(components)} components managed by Lerna.")

    # Add the repo's root to the component list if requested.
    components.append({
        'name': "root",
        'version': "",
        'private': True,
        'location': root,
    })

    return repo, root, components
