#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -o nounset

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Check NPM and setup JavaScript
npm run check-npm-version
npm i

# Check and setup Python with virtual environment
source "${__dir}/init-python-environment.sh"  # 'exit' in sub-script should also stop this script

scope_file="${__dir}/../scope.json"

scope=$(npx json -f "${scope_file}" scope)

if [ "$scope" = 'test' ]; then
  echo 'You have to change the name of the scope first.'
  echo 'https://shapediver.atlassian.net/wiki/spaces/SS/pages/953352193/Naming+of+Github+Packages'
  echo 'New scope name: '
  read -r NEW_SCOPE
  npx json -q -I -f "${scope_file}" -e "this.scope=\"${NEW_SCOPE}\""
fi

function ask_yes_or_no() {
  read -rp "$1 ([y]es or [n]o): "
  case $(echo "$REPLY" | tr '[A-Z]' '[a-z]') in
  y | yes) echo "yes" ;;
  *) echo "no" ;;
  esac
}

initialized=$(npx json -f "${scope_file}" 'initialized')

if [ "$initialized" != 'true' ]; then
  echo 'The "npm run publish" command is currently set to publish all packages, every time (even if there were no changes).'
  if [[ "yes" == $(ask_yes_or_no "Do you want to independently publish only changed packages instead?") ]]; then
    npx json -q -I -f 'lerna.json' -e 'this.version="independent"'
  fi
fi

npx json -q -I -f "${scope_file}" -e 'this.initialized=true'
npm run bootstrap
