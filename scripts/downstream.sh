#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -o nounset

url_monorepo="git@github.com:shapediver/MonorepoTemplate.git"
remote_name="monorepo"
remote_branch="master"

# Stop when repo is dirty
if [ -n "$(git diff --shortstat)" ]; then
  echo "ERROR: Detected uncommitted changes in this repository." >&2
  exit 1
fi

# Add the Monorepo Template remote
if ! git remote add "${remote_name}" "${url_monorepo}" 2>/dev/null; then
  echo "ERROR: Git remote of name '${remote_name}' already exists!"
  exit 1
fi

cleanup() {
  # Remove remote - this also removes the fetched branch
  git remote remove "${remote_name}"
}
trap 'cleanup' ERR EXIT

# Just to make sure, prevent pushing to the new remote
git remote set-url --push "${remote_name}" no_push

# Fetch the newest changes
git fetch "${remote_name}" "${remote_branch}"

# Merge the changes - this will most likely lead to conflicts!
# Since a non-zero exit code is returned when conflicts appear, we prevent the script from stopping.
git merge --log --allow-unrelated-histories --squash "${remote_name}/${remote_branch}" || :

# If there are merge conflicts, wait for the user to resolve them
if [ -n "$(git ls-files --unmerged)" ]; then
  echo -e "\nMERGE CONFLICTS DETECTED!"
  echo "Please resolve all conflicts manually before continuing the script."
  read -p "Press [Enter] key to resume ..."

  # Prevent the user from continuing without resolving all conflicts
  while [ -n "$(git ls-files --unmerged)" ]; do
    echo -e "\nStill found some open conflicts - resolve them before continuing the script."
    read -p "Press [Enter] key to resume ..."
  done
fi

# Add all tracked files
git add --update

# If there are any untracked files, ask the user what to do with them
if [ -n "$(git ls-files --other --directory --exclude-standard)" ]; then
  echo -e "\nDETECTED UNTRACKED FILES!"
  echo -e "The following untracked files have been found:\n"
  git ls-files --other --directory --exclude-standard
  echo -e "\nIf you want to add one or more of these files to the merge, add them via 'git add <file_path>'."
  echo "Otherwise, these files will stay untracked."
  read -p "Press [Enter] key to resume ..."
fi

# Finalize the merge
git commit -m "Downstream changes from MonorepoTemplate" --no-verify
