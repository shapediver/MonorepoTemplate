#!/bin/bash
NAME=$1
LIB_PATH='./libs/'$NAME'/'
echo 'Trying to create lib "'$NAME'" at "'$LIB_PATH'"...'

if [ $LIB_PATH = './packages//' ]
then
    echo 'Please provide a name for the package.'
    exit 1
fi

if [ -d $LIB_PATH ]
then
    echo 'The path for this package already exists.'
    exit 1
fi

lerna create $NAME 'libs' --private true --description "" --yes

# add an empty index.ts
mkdir -p $LIB_PATH'/src/'
cd $LIB_PATH'/src/'
touch index.ts
cd ../../..

# copy tsconfig
cp './scripts/utils/tsconfig.json' $LIB_PATH

# adjust package.json
json -q -I -f $LIB_PATH'package.json' -e 'this.name="@shapediver/'$NAME'"'
json -q -I -f $LIB_PATH'package.json' -e 'this.description=""'
json -q -I -f $LIB_PATH'package.json' -e 'this.main="dist/index.js"'
json -q -I -f $LIB_PATH'package.json' -e 'this.typings="dist/index.d.ts"'
json -q -I -f $LIB_PATH'package.json' -e 'this.files=["dist"]'
json -q -I -f $LIB_PATH'package.json' -e 'this.scripts.check="tsc --noEmit"'
json -q -I -f $LIB_PATH'package.json' -e 'this.scripts.build="tsc -b"'
json -q -I -f $LIB_PATH'package.json' -e 'this.scripts["build-dep"]="lerna run build --stream --scope=$npm_package_name --include-dependencies"'
json -q -I -f $LIB_PATH'package.json' -e 'this.devDependencies={}'
json -q -I -f $LIB_PATH'package.json' -e 'this.devDependencies["@shapediver/ts-config"]="^1.0.0"'
json -q -I -f $LIB_PATH'package.json' -e 'this.devDependencies["lerna"]="^3.22.1"'
json -q -I -f $LIB_PATH'package.json' -e 'this.devDependencies["typescript"]="^4.1.2"'

npm run bootstrap
echo 'lib "'$NAME'" successfully created!'