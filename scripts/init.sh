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

npm run bootstrap