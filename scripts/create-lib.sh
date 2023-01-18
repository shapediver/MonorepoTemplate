#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -o nounset

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Validate arguments
if [ $# -lt 1 ] || [ -z "$1" ] ; then
  echo "Error: Specify the name of the new library." >&2
  exit 1
fi

scope=$(npx json -f 'scope.json' scope)
name=$scope.$1
root_path="${__dir}/../"
lib_path="${root_path}/libs/${name}/"

echo "Trying to create library '${name}' at '${lib_path}'..."

if [ -d "${lib_path}" ]; then
  echo 'The path for this package already exists.'
  exit 1
fi

lerna create "${name}" 'libs' --description "" --yes

# prepare package
mkdir -p "${lib_path}/src/"
touch "${lib_path}/src/index.ts"
rm -r "${lib_path:?}/lib"
echo "" > "${lib_path}/__tests__/${name}.test.js"

# copy tsconfig
cp "${__dir}/utils/tsconfig.json" "${lib_path}"

# adjust package.json
npx json -q -I -f "${lib_path}package.json" -e "this.name=\"@shapediver/${name}\""
npx json -q -I -f "${lib_path}package.json" -e 'this.description=""'
npx json -q -I -f "${lib_path}package.json" -e 'this.main="dist/index.js"'
npx json -q -I -f "${lib_path}package.json" -e 'this.typings="dist/index.d.ts"'
npx json -q -I -f "${lib_path}package.json" -e 'this.files=["dist"]'
npx json -q -I -f "${lib_path}package.json" -e 'this.scripts.check="tsc --noEmit"'
npx json -q -I -f "${lib_path}package.json" -e 'this.scripts.build="bash ../../scripts/build.sh"'
npx json -q -I -f "${lib_path}package.json" -e 'this.scripts["build-dep"]="bash ../../scripts/build-dep.sh"'
npx json -q -I -f "${lib_path}package.json" -e 'this.scripts.test="bash ../../scripts/test.sh"'
npx json -q -I -f "${lib_path}package.json" -e 'this.scripts["pre-publish"]="bash ../../scripts/pre-publish.sh"'
npx json -q -I -f "${lib_path}package.json" -e 'this.scripts["post-publish"]="bash ../../scripts/post-publish.sh"'
npx json -q -I -f "${lib_path}package.json" -e 'this.jest={}'
npx json -q -I -f "${lib_path}package.json" -e 'this.jest.preset="ts-jest"'
npx json -q -I -f "${lib_path}package.json" -e 'this.jest.testEnvironment="node"'
npx json -q -I -f "${lib_path}package.json" -e 'this.directories={}'
npx json -q -I -f "${lib_path}package.json" -e 'this.directories.test="__tests__"'
npx json -q -I -f "${lib_path}package.json" -e 'this.devDependencies={}'
npx json -q -I -f "${lib_path}package.json" -e "this.devDependencies['jest']=\"$(npx json -f "${root_path}/package.json" 'devDependencies.jest')\""
npx json -q -I -f "${lib_path}package.json" -e "this.devDependencies['lerna']=\"$(npx json -f "${root_path}/package.json" 'devDependencies.lerna')\""
npx json -q -I -f "${lib_path}package.json" -e "this.devDependencies['typescript']=\"$(npx json -f "${root_path}/package.json" 'devDependencies.typescript')\""

npm run bootstrap
echo "Library '${name}' successfully created!"
