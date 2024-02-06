#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -o nounset

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Validate arguments
if [ $# -lt 1 ] || [ -z "$1" ] ; then
  echo "Error: Specify the name of the new package." >&2
  exit 1
fi

scope=$(npx json -f 'scope.json' scope)
name=$scope.$1
root_path="${__dir}/../"
pkg_path="${root_path}/packages/${name}/"

echo "Trying to create package '${name}' at '${pkg_path}'..."

if [ -d "${pkg_path}" ]; then
  echo 'The path for this package already exists.'
  exit 1
fi

lerna create "${name}" 'packages' --description "" --yes

# prepare package
mkdir -p "${pkg_path}/src/"
touch "${pkg_path}/src/index.ts"
rm -r "${pkg_path:?}/lib"
echo "" > "${pkg_path}/__tests__/${name}.test.js"

# copy tsconfig and index.html
cp "${__dir}/utils/tsconfig.json" "${pkg_path}"
cp "${__dir}/utils/index.html" "${pkg_path}"

# Adopt source-root in tsconfig
npx json -q -I -f "${pkg_path}tsconfig.json" -e "this.compilerOptions.sourceRoot=\"packages/${name}/src/\""

# adjust package.json
npx json -q -I -f "${pkg_path}package.json" -e "this.name=\"@shapediver/${name}\""
npx json -q -I -f "${pkg_path}package.json" -e 'this.description=""'
npx json -q -I -f "${pkg_path}package.json" -e 'this.main="dist/index.js"'
npx json -q -I -f "${pkg_path}package.json" -e 'this.typings="dist/index.d.ts"'
npx json -q -I -f "${pkg_path}package.json" -e 'this.files=["dist"]'
npx json -q -I -f "${pkg_path}package.json" -e 'this.scripts.check="tsc --noEmit"'
npx json -q -I -f "${pkg_path}package.json" -e 'this.scripts.build="bash ../../scripts/build.sh"'
npx json -q -I -f "${pkg_path}package.json" -e 'this.scripts["build-dep"]="bash ../../scripts/build-dep.sh"'
npx json -q -I -f "${pkg_path}package.json" -e 'this.scripts["build-dev"]="bash ../../scripts/build-dev.sh"'
npx json -q -I -f "${pkg_path}package.json" -e 'this.scripts["build-prod"]="bash ../../scripts/build-prod.sh"'
npx json -q -I -f "${pkg_path}package.json" -e 'this.scripts.test="bash ../../scripts/test.sh"'
npx json -q -I -f "${pkg_path}package.json" -e 'this.scripts["pre-publish"]="bash ../../scripts/pre-publish.sh"'
npx json -q -I -f "${pkg_path}package.json" -e 'this.scripts["post-publish"]="bash ../../scripts/post-publish.sh"'
npx json -q -I -f "${pkg_path}package.json" -e 'this.jest={}'
npx json -q -I -f "${pkg_path}package.json" -e 'this.jest.preset="ts-jest"'
npx json -q -I -f "${pkg_path}package.json" -e 'this.jest.testEnvironment="node"'
npx json -q -I -f "${pkg_path}package.json" -e 'this.devDependencies={}'
npx json -q -I -f "${pkg_path}package.json" -e 'this.directories={}'
npx json -q -I -f "${pkg_path}package.json" -e 'this.directories.test="__tests__"'
npx json -q -I -f "${pkg_path}package.json" -e "this.devDependencies['jest']=\"$(npx json -f "${root_path}/package.json" 'devDependencies.jest')\""
npx json -q -I -f "${pkg_path}package.json" -e "this.devDependencies['lerna']=\"$(npx json -f "${root_path}/package.json" 'devDependencies.lerna')\""
npx json -q -I -f "${pkg_path}package.json" -e "this.devDependencies['typescript']=\"$(npx json -f "${root_path}/package.json" 'devDependencies.typescript')\""
npx json -q -I -f "${pkg_path}package.json" -e "this.devDependencies['webpack']=\"$(npx json -f "${root_path}/package.json" 'devDependencies.webpack')\""
npx json -q -I -f "${pkg_path}package.json" -e "this.devDependencies['webpack-cli']=\"$(npx json -f "${root_path}/package.json" 'devDependencies.webpack-cli')\""
npx json -q -I -f "${pkg_path}package.json" -e "this.devDependencies['webpack-dev-server']=\"$(npx json -f "${root_path}/package.json" 'devDependencies.webpack-dev-server')\""

cd "${root_path}"
pnpm install
echo "Package '${name}' successfully created!"
