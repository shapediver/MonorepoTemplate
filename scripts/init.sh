#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -o nounset

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Check NPM and setup JavaScript
npm run check-npm-version
pnpm install

# Check and setup Python with virtual environment
source "${__dir}/init-python-environment.sh" # 'exit' in sub-script should also stop this script

scope_file="${__dir}/../scope.json"
scope=$(npx json -f "${scope_file}" scope)

if [ "$scope" = 'test' ]; then
  echo -e '\nYou have to change the name of the scope first.'
  echo 'https://shapediver.atlassian.net/wiki/spaces/SS/pages/953352193/Naming+of+Github+Packages'
  echo 'New scope name: '
  read -r scope_name
  npx json -q -I -f "${scope_file}" -e "this.scope=\"${scope_name}\""
fi

