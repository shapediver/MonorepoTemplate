import functools
import json
import os
import re
import shlex
import typing as t

import git
import semantic_version as semver

from utils import (
    CliConfig, LernaComponent, PrintMessageError, app_on_error, ask_user, cmd_helper, copy,
    echo, link_npmrc_file, load_cli_config, remove, run_process, unlink_npmrc_file,
    update_cli_config)

REGISTRY_GITHUB = "https://npm.pkg.github.com/"
REGISTRY_NPM = "https://registry.npmjs.org/"

# Type of single Lerna component
PublishableComponent = t.TypedDict('PublishableComponent', {
    'component': LernaComponent,
    'new_version': str,
})


def run(dry_run: bool, always_ask: bool) -> bool:
    # Initialize repo object and search for Lerna components.
    repo, root, all_components = cmd_helper()

    # Stop processing when open changes have been detected.
    if not dry_run:
        check_open_changes(repo)

    # Load cli config file.
    config = load_cli_config(root)

    # Ask user which components should get published.
    publishable_components = ask_user_for_components_and_version(
        all_components, root, config, always_ask)

    # Ask user to which registries the selected components should be published to and make sure that
    # the user is already logged in for all selected registries.
    publish_to_github, publish_to_npm = ask_user_for_registry(root)

    # Register cleanup handler for error case. However, we cannot really do much here.
    app_on_error.append(functools.partial(cleanup, all_components))

    # Build argument string for global pre-/post-publish scripts.
    global_args = [dry_run, json.dumps(publishable_components)]
    global_args_str = " ".join([shlex.quote(str(arg)) for arg in global_args])

    # Run GLOBAL pre-publish.
    run_process(f"npm run pre-publish-global {global_args_str}", root)

    # Backup package.json files to undo the version change in dry-run mode.
    if dry_run:
        for component in all_components:
            package_json = os.path.join(component['location'], "package.json")
            copy(package_json, package_json + ".bak")

    # Update component versions.
    update_version(all_components, publishable_components)

    for c in publishable_components:
        echo(f"\nPublishing component {c['component']['name']}:")

        # Build argument string for pre-/post-publish scripts.
        args = [dry_run, c['component']['name'], c['new_version']]
        args_str = " ".join(shlex.quote(str(arg)) for arg in args)

        # Run pre-publish
        run_process(f"npm run pre-publish {args_str}", c['component']['location'])

        # Prepare publish command
        cmd = "npm publish" + (" --dry-run" if dry_run else "") + " --registry "

        # Publish to GitHub.
        if publish_to_github:
            echo("Publishing to GitHub:")

            # Authorization is done via an .npmrc file -> link from root when found.
            link_npmrc_file(root, [c['component']], must_exist=True)

            run_process(cmd + REGISTRY_GITHUB, c['component']['location'])

        # Publish to NPM.
        if publish_to_npm:
            echo("Publishing to NPM:")

            # Authorization is done via NPM CLI login -> remove .npmrc file when found.
            unlink_npmrc_file(c['component'])

            run_process(cmd + REGISTRY_NPM, c['component']['location'])

        # Run post-publish
        run_process(f"npm run post-publish {args_str}", c['component']['location'])

    # Create Git commit and tags
    to_push: t.Union[None, t.List[str]] = None
    if not dry_run:
        to_push = ask_user_and_prepare_commit_and_tags(
            root, repo, config, all_components, publishable_components, always_ask)
    else:
        echo("\nSkipping Git commit and tag(s) creation.")

    # Run GLOBAL post-publish
    run_process(f"npm run post-publish-global {global_args_str}", root)

    # Push changes to Git
    if to_push is not None:
        ask_user_and_push_to_origin(repo, to_push)
    else:
        echo("\nSkipping Git push.")

    # Restore package.json files to undo to version change in dry-run mode.
    if dry_run:
        for component in all_components:
            package_json = os.path.join(component['location'], "package.json")
            copy(package_json + ".bak", package_json)

    # Remove auth files
    cleanup(all_components)

    return True


def check_open_changes(repo: git.Repo) -> None:
    """ Checks if the Git index has any open changes (except for untracked files). """
    if repo.is_dirty():
        raise PrintMessageError(
            """ERROR:
  Your index contains uncommitted changes.
  Please commit or stash them.
""")


def ask_user_for_components_and_version(
        components: t.List[LernaComponent],
        root: str,
        config: CliConfig,
        always_ask: bool,
) -> t.List[PublishableComponent]:
    """
    Determine which components should be published and their respective version.

    Either uses the configured selection or asks the user what to do.
    :param components: All Lerna managed components.
    :param root: The path of the Git repository's root folder.
    :param config: The CLI configuration values.
    :param always_ask: Disables and overrides default selection of answers.
    :raise PrintMessageError: When the user input is not processable.
    :return: A list of all selected components to publish and their respective new version.
    """
    print()  # Add empty line

    def ask_for_new_version(old_version: str, cmp_name: t.Optional[str]) -> str:
        """ Helper function to ask the user which version should be used next. """
        user_msg = f"Select a new version (currently {old_version})"
        if cmp_name is not None:
            user_msg += f" for component {cmp_name}"

        v = semver.Version(old_version)
        a = ask_user([{
            'type': "list",
            'name': "version",
            'message': f"{user_msg}:",
            'choices': [
                str(v.next_patch()),
                str(v.next_minor()),
                str(v.next_major()),
                {
                    'name': "A custom version.",
                    'value': "custom"
                }
            ]
        }])

        if a['version'] == "custom":
            # Ask the user for a concrete custom version and validate the input.
            a = ask_user([{
                'type': "input",
                'name': "version",
                'message': "Custom version:"
            }])

            try:
                # Allow partial versions but make sure that custom version is a valid semver format.
                custom_version = semver.Version.coerce(a['version'])
                echo(f"\nThe custom version you entered got coerced to '{custom_version}'.", 'wrn')
            except ValueError:
                raise PrintMessageError(f"\nERROR:\n  Invalid version string: '{a['version']}'.")

            # Check with the user if we have coerced the custom version.
            if custom_version != a['version']:
                a = ask_user([{
                    'type': "confirm",
                    'name': "proceed",
                    'message': "Proceed?",
                    'default': True,
                }])
                if not a['proceed']:
                    raise PrintMessageError("Process got stopped by the user.")
                a['version'] = custom_version

        return a['version']

    # We never publish components that are marked as "private".
    public_components = [c for c in components if c['private'] is False]

    # Stop when no public components where found.
    if len(public_components) == 0:
        raise PrintMessageError("\nERROR:\n  Found no public components that are managed by Lerna.")

    res: t.List[PublishableComponent] = []

    # Determine the publishing mode to use.
    publishing_mode: t.Literal['all', 'independent']
    if not always_ask and config['publish_mode'] is not None:
        # Use publishing mode from config value.
        publishing_mode = config['publish_mode']
    else:
        # Ask user which publishing mode to use and store the answer in cli config.
        answers = ask_user([{
            'type': "list",
            'name': 'mode',
            'message': "What should get published:",
            'choices': [
                {
                    'name': "All public components.",
                    'value': 'all',
                },
                {
                    'name': "Select individual components.",
                    'value': 'independent',
                },
            ],
        }])
        publishing_mode = answers['mode']
        config['publish_mode'] = publishing_mode
        update_cli_config(root, publish_mode=publishing_mode)

    if publishing_mode == 'all':
        # Sanity check: Stop when public components have not the same versions.
        unique_versions = list({c['version']: c for c in public_components}.keys())
        if len(unique_versions) > 1:
            msg = f"""
ERROR:
  Cannot release all public components since they do not share the same version.
  The following components and their respective versions have been found:"""
            for c in public_components:
                msg += f"\n   * {c['name']}, {c['version']}"
            raise PrintMessageError(msg)

        # Ask for the new version that should be used for all public components.
        version = ask_for_new_version(unique_versions[0], None)

        # Map public components into publishable structure.
        res = [{'component': c, 'new_version': version} for c in public_components]
    elif publishing_mode == 'independent':
        # Ask user which public components should be published.
        answers = ask_user([{
            'type': "checkbox",
            'name': "selection",
            'message': "Select all public components that should be published:",
            'choices': [{'name': c['name']} for c in public_components],
        }])

        # Filter public components by user selection.
        selected_components = list(filter(
            lambda c: c['name'] in answers['selection'],
            public_components))

        # Check for empty selection.
        if len(selected_components) == 0:
            raise PrintMessageError("\nERROR:\n  At least one component must be selected.")

        # Ask user for the new version of each selected component.
        for c in selected_components:
            res.append({
                'component': c,
                'new_version': ask_for_new_version(c['version'], c['name'])
            })
    else:
        # Catch invalid config values.
        raise PrintMessageError(
            f"""ERROR:
  Unknown publishing mode '{publishing_mode}'.
  Remove the property `repomaintain.publish_mode` in the `scope.json` file and try again.
""")

    # Log a message that shows information about all components that will be published.
    msg = "\nYou selected the following components for publishing:\n"
    for c in res:
        msg += f"  * {c['component']['name']}, {c['new_version']}\n"
    echo(msg)

    return res


def ask_user_for_registry(root: str) -> t.Tuple[bool, bool]:
    """
    Asks the user which target registries should be used for publishing.

    :raise PrintMessageError: When the user did not select any registry.
    :return: [0] Git registry. [1] NPM registry.
    """
    answers = ask_user([
        {
            'type': "confirm",
            'name': "github",
            'message': "Publish to Github registry?",
            'default': True,
        },
        {
            'type': "confirm",
            'name': "npm",
            'message': "Publish to NPM registry?",
            'default': True,
        }
    ])

    # At least one registry must be targeted.
    if not answers['github'] and not answers['npm']:
        raise PrintMessageError("\nERROR:\n  No registry selected.")

    # Make sure that the user is logged in.
    if answers['npm']:
        try:
            run_process(f"npm whoami --registry {REGISTRY_NPM}", root, show_output=False)
        except RuntimeError:
            raise PrintMessageError(f"""
ERROR:
  You are not logged in to your NPM account.
  Run 'npm login --registry {REGISTRY_NPM}' and use your ShapeDiver account!
""")

    return answers['github'], answers['npm']


def ask_user_and_prepare_commit_and_tags(
        root: str,
        repo: git.Repo,
        config: CliConfig,
        all_components: t.List[LernaComponent],
        published_components: t.List[PublishableComponent],
        always_ask: bool,
) -> t.List[str]:
    """ Prepares the Git commit and tag(s). """
    # Add all package.json changes to the Git index.
    index = repo.index
    for component in all_components:
        index.add(os.path.join(component['location'], "package.json"))

    # The CLI config might have been changed, so we add it too.
    index.add(os.path.join(root, "scope.json"))

    # Create a new commit.
    index.commit("Publish")
    echo("\nCreated a new commit.")

    # Add the current branch (contains the publish-commits).
    to_push = [repo.active_branch.path]

    # We want to enforce the following standard:
    #   * One Git tag for repositories that publish all components with the same version. The name
    #     of the shared tag is customizable by the user (<custom name>@<version>).
    #   * Otherwise, each component gets its own Git tag (<pkg_name>@<version>).
    if config['publish_mode'] == 'all':
        # Note: Sanity check for #components, publish_mode and single version already done.
        version = published_components[0]['new_version']

        if (not always_ask and config['publish_tag_name'] is not None and
                len(config['publish_tag_name']) > 0):
            tag = repo.create_tag(f"{config['publish_tag_name']}@{version}")
            to_push.append(tag.path)
        else:
            # Ask the user for a custom tag name and store the answer in cli config.
            echo(f"A single Git tag will be created for all components ('<name>@{version}').")

            tag_name = ""
            while len(tag_name) == 0:
                answers = ask_user([{
                    'type': "input",
                    'name': "tag_name",
                    'message': "Tag name (non-empty string):"
                }])
                tag_name = str(answers['tag_name']).strip().replace(' ', '_')

            tag = repo.create_tag(f"{tag_name}@{version}")
            to_push.append(tag.path)

            config['publish_tag_name'] = tag_name
            update_cli_config(root, publish_tag_name=tag_name)
    else:
        # Create one git tag for each published component.
        for c in published_components:
            name, version = c['component']['name'], c['new_version']
            tag = repo.create_tag(f"{name}@{version}")
            to_push.append(tag.path)

    return to_push


def ask_user_and_push_to_origin(repo: git.Repo, to_push: t.List[str]) -> None:
    """ Pushes the given references to Git remote 'origin' if the users confirm. """
    # Log all references that are going to be pushed.
    msg = "\nThe following Git references are ready to be pushed:\n"
    for ref in to_push:
        msg += f"\n  * {ref}"
    echo(msg)

    # Ask user if changes should be pushed
    print()
    answers = ask_user([{
        'type': "confirm",
        'name': "proceed",
        'message': "Push to Git 'origin'?",
        'default': True,
    }])
    if not answers['proceed']:
        echo("Cancelled by User - no references got pushed to Git.")
        return

    # Push to origin
    repo.remote().push(to_push).raise_if_error()


def update_version(
        all_components: t.List[LernaComponent],
        publishable_components: t.List[PublishableComponent],
) -> None:
    """
    Updates versions in the package.json file of the given components.

    Updates the version of the given components themselves, as well as the linked versions of all
    internal dependencies that have changes in the publish process.
    """
    echo("\nIncrement versions of components.")

    publishable_component_map: t.Dict[str, str] = {
        c['component']['name']: c['new_version'] for c in publishable_components
    }

    # Regex to extract the prefix of a semver (e.g. '~', '<=')
    regex = re.compile(r'^[^ \d]*')

    # List of all forced updates of internal dependency. When a new version of a component is about
    # to be released, this versions is updated in all other components which link this component
    # internally. This is done regardless of the semantic versioning policy.
    #
    # E.g. component A@2.0.0 is about to be published and component B links it internally via
    # `~1.5.3`. Here, the dependency in component B is updated to `~2.0.0`.
    #
    # This makes the publish process much more convenient, but we have ask the user afterwards.
    forced_updates: t.Dict[str, t.Dict[str, str]] = {c['name']: {} for c in all_components}

    def update_internal_dependency(pkg_json_dep_ref: t.Dict[str, t.Any]) -> None:
        """
        Helper function to update the version of a linked internal dependency.

        First, it is determined if the versions of the internal dependency "matches". A dependency
        is seen as "matching" when the current dependency version is within the range of the
        specified version according to semantic versioning. When the dependency does not match, the
        information is added to `forced_updates`. Afterwards, the new version is set in the
        package.json object.
        """
        # Extract semver-prefix
        semver_specifier: str = re.findall(regex, pkg_json_dep_ref[name])[0]

        current_version = pkg_json_dep_ref[name]
        new_version = semver_specifier + version

        # Extend forced_updates list when versions do not match
        if semver.Version(version) not in semver.NpmSpec(current_version):
            forced_updates[component['name']].update({name: f"{current_version} -> {new_version}"})

        # Update the dependency version in the JSON object
        pkg_json_dep_ref[name] = new_version

    for component in all_components:
        pkg_json_file = os.path.join(component['location'], "package.json")

        # Open and parse package.json file.
        with open(pkg_json_file, 'r') as reader:
            pkg_json_content: t.Dict[str, t.Any] = json.load(reader)

        # Update the version of the component itself.
        if component['name'] in publishable_component_map:
            pkg_json_content['version'] = publishable_component_map[component['name']]

        # Remove all internal dependencies that have a matching version.
        for name, version in publishable_component_map.items():
            if "dependencies" in pkg_json_content and name in pkg_json_content['dependencies']:
                update_internal_dependency(pkg_json_content['dependencies'])
            elif "devDependencies" in pkg_json_content and name in pkg_json_content['devDependencies']:
                update_internal_dependency(pkg_json_content['devDependencies'])

        # Write changes to package.json file.
        with open(pkg_json_file, 'w') as writer:
            writer.write(json.dumps(pkg_json_content, indent=2) + "\n")

    # Log additional output if forced updates have been applied.
    forced_updates_applied = False
    for name, updates in forced_updates.items():
        if len(updates) > 0:
            msg = f"\n{name}:"
            for dep_name, dep_versions in updates.items():
                msg += f"\n  * {dep_name}: {dep_versions}"
            echo(msg, 'wrn')
            forced_updates_applied = True

    # Ask user when forced updates have been applied.
    if forced_updates_applied:
        print()
        answers = ask_user([{
            'type': "confirm",
            'name': "proceed",
            'message': "Internal dependencies have been updated regardless existing semantic "
                       "versioning - see logs above for more information.\nProceed?",
            'default': True,
        }])
        if not answers['proceed']:
            raise PrintMessageError("Process got stopped by the user.")


def cleanup(components: t.List[LernaComponent]) -> None:
    """ Removes backup and linked .npmrc files in all components. """
    for c in components:
        # Remove backup of package.json file (might be created for dry-run).
        pkg_json_bak_file = os.path.join(c['location'], "package.json.bak")
        remove(pkg_json_bak_file)

        # Remove linked .npmrc file (might be created for GitHub push).
        unlink_npmrc_file(c)
