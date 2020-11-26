#!/bin/bash
SCOPE=$(json -f 'scope.json' scope)
NAME=$SCOPE.$1
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

lerna create $NAME 'libs' --description "" --yes

# add an empty index.ts
mkdir -p $LIB_PATH'/src/'
cd $LIB_PATH'/src/'
touch index.ts
cd ../../..

cd $LIB_PATH
rm -r 'lib'
cd ../..

cd $LIB_PATH'/__tests__/'
rm $NAME'.test.js'
touch $NAME'.test.ts'
cd ../../..

# copy tsconfig
cp './scripts/utils/tsconfig.json' $LIB_PATH
json -q -I -f $LIB_PATH'tsconfig.json' -e 'this.extends="@shapediver/'$SCOPE'.ts-config/tsconfig.json"'

# adjust package.json
json -q -I -f $LIB_PATH'package.json' -e 'this.name="@shapediver/'$NAME'"'
json -q -I -f $LIB_PATH'package.json' -e 'this.description=""'
json -q -I -f $LIB_PATH'package.json' -e 'this.main="dist/index.js"'
json -q -I -f $LIB_PATH'package.json' -e 'this.typings="dist/index.d.ts"'
json -q -I -f $LIB_PATH'package.json' -e 'this.files=["dist"]'
json -q -I -f $LIB_PATH'package.json' -e 'this.scripts.check="tsc --noEmit"'
json -q -I -f $LIB_PATH'package.json' -e 'this.scripts.build="bash ../../scripts/build.sh"'
json -q -I -f $LIB_PATH'package.json' -e 'this.scripts["build-dep"]="bash ../../scripts/build-dep.sh"'
json -q -I -f $LIB_PATH'package.json' -e 'this.scripts.test="bash ../../scripts/test.sh"'
json -q -I -f $LIB_PATH'package.json' -e 'this.jest={}'
json -q -I -f $LIB_PATH'package.json' -e 'this.jest.preset="ts-jest"'
json -q -I -f $LIB_PATH'package.json' -e 'this.jest.testEnvironment="node"'
json -q -I -f $LIB_PATH'package.json' -e 'this.directories={}'
json -q -I -f $LIB_PATH'package.json' -e 'this.directories.test="__tests__"'
json -q -I -f $LIB_PATH'package.json' -e 'this.devDependencies={}'
json -q -I -f $LIB_PATH'package.json' -e 'this.devDependencies["jest"]="^26.6.3"'
json -q -I -f $LIB_PATH'package.json' -e 'this.devDependencies["lerna"]="^3.22.1"'
json -q -I -f $LIB_PATH'package.json' -e 'this.devDependencies["typescript"]="^4.1.2"'

npm run add-devDependency '@shapediver/'$SCOPE'.ts-config' '@shapediver/'$NAME

npm run bootstrap
echo 'lib "'$NAME'" successfully created!'