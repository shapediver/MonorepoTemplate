#!/bin/bash
NAME=$1
PACKAGE_PATH='./packages/'$NAME'/'
echo 'Trying to create package "'$NAME'" at "'$PACKAGE_PATH'"...'

if [ $PACKAGE_PATH = './packages//' ]
then
    echo 'Please provide a name for the package.'
    exit 1
fi

if [ -d $PACKAGE_PATH ]
then
    echo 'The path for this package already exists.'
    exit 1
fi

lerna create $NAME 'packages' --private true --description "" --yes

# add an empty index.ts
mkdir -p $PACKAGE_PATH'/src/'
cd $PACKAGE_PATH'/src/'
touch index.ts
cd ../../..

# copy tsconfig and index.html
cp './scripts/utils/tsconfig.json' $PACKAGE_PATH
cp './scripts/utils/index.html' $PACKAGE_PATH

# adjust package.json
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.name="@shapediver/'$NAME'"'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.description=""'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.main="dist/index.js"'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.typings="dist/index.d.ts"'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.files=["dist"]'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.scripts.check="tsc --noEmit"'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.scripts.build="tsc -b"'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.scripts["build-dep"]="lerna run build --stream --scope=$npm_package_name --include-dependencies"'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.scripts["build-dev"]="rm -rf ./dist-dev && mkdir dist-dev && cp index.html dist-dev/index.html && webpack serve --config ../../webpack.dev.js --output-filename bundle.js --output-path dist-dev --content-base ./dist-dev"'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.scripts["build-prod"]="rm -rf ./dist-prod && mkdir dist-prod && cp index.html dist-prod/index.html && webpack --config ../../webpack.prod.js --output-filename bundle.js --output-path dist-prod"'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.devDependencies={}'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.devDependencies["@shapediver/ts-config"]="^1.0.0"'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.devDependencies["lerna"]="^3.22.1"'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.devDependencies["typescript"]="^4.1.2"'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.devDependencies["webpack"]="^5.6.0"'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.devDependencies["webpack-cli"]="^4.2.0"'
json -q -I -f $PACKAGE_PATH'package.json' -e 'this.devDependencies["webpack-dev-server"]="^3.11.0"'

npm run bootstrap
echo 'package "'$NAME'" successfully created!'