npm run check-npm-version
npm i

SCOPE=$(json -f 'scope.json' scope)
NAME=$SCOPE.$1

if [ $SCOPE = 'test' ]
then
    echo 'You have to change the name of the scope first.'
    echo 'https://shapediver.atlassian.net/wiki/spaces/SS/pages/953352193/Naming+of+Github+Packages'
    echo 'New scope name: '
    read NEW_SCOPE
    json -q -I -f 'scope.json' -e 'this.scope="'$NEW_SCOPE'"'
fi

function ask_yes_or_no() {
    read -p "$1 ([y]es or [n]o): "
    case $(echo $REPLY | tr '[A-Z]' '[a-z]') in
        y|yes) echo "yes" ;;
        *)     echo "no" ;;
    esac
}

INITIALIZED=$(json -f 'scope.json' initialized)

if [ $INITIALIZED != 'true' ]
then
    echo 'The "npm run publish" command is currently set to publish all packages, every time (even if there were no changes).'
    if [[ "yes" == $(ask_yes_or_no "Do you want to independently publish only changed packages instead?") ]]
    then
        json -q -I -f 'lerna.json' -e 'this.version="independent"'
    fi
fi

json -q -I -f 'scope.json' -e 'this.initialized=true'
npm run bootstrap