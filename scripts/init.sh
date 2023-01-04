#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -o nounset

npm run check-npm-version
npm i

scope=$(npx json -f 'scope.json' scope)

if [ "$scope" = 'test' ]; then
  echo 'You have to change the name of the scope first.'
  echo 'https://shapediver.atlassian.net/wiki/spaces/SS/pages/953352193/Naming+of+Github+Packages'
  echo 'New scope name: '
  read -r NEW_SCOPE
  npx json -q -I -f 'scope.json' -e "this.scope=\"${NEW_SCOPE}\""
fi

function ask_yes_or_no() {
  read -rp "$1 ([y]es or [n]o): "
  case $(echo "$REPLY" | tr '[A-Z]' '[a-z]') in
  y | yes) echo "yes" ;;
  *) echo "no" ;;
  esac
}

initialized=$(npx json -f 'scope.json' 'initialized')

if [ "$initialized" != 'true' ]; then
  echo 'The "npm run publish" command is currently set to publish all packages, every time (even if there were no changes).'
  if [[ "yes" == $(ask_yes_or_no "Do you want to independently publish only changed packages instead?") ]]; then
    npx json -q -I -f 'lerna.json' -e 'this.version="independent"'
  fi
fi

npx json -q -I -f 'scope.json' -e 'this.initialized=true'
npm run bootstrap
