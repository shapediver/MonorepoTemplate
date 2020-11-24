![logo](https://d2tlksottdg9m1.cloudfront.net/production/assets/images/shapediver_logo_gradient.png "ShapeDiver")
# Monorepo Template

This Repository is here to be used if you want to have multiple npm packages in one repository. These packages can be reliant on each other or completely separate.

The setup is built on `lerna` which is a package that is build for handling javascript monorepos. I extended some functionality and made create some further custom scripts for creating packages and building them. But trust me, there is no magic involved, mostly just creating a nice project setup.

You can either add packages and libraries in the `packages` folder or in the `libs` folder, respectively. Please see below regarding custom scripts on how to do that.

## 1. Setup
### Node / NPM
You need to install a specific version of node (14.5.0) and npm (6.14.5). You can do this in any way you want to, but in the following steps we will explain how to do this with nvm.

First of all, download nvm ([windows](https://github.com/coreybutler/nvm-windows)/[unix](https://github.com/nvm-sh/nvm)/[mac](https://github.com/nvm-sh/nvm)).
Once installed, just use the commands

`nvm install 14.5.0`

and

`nvm use 14.5.0`

This will install node (14.5.0) and the corresponding npm version (6.14.5).

### GIT
Make sure to have GIT installed on your system.
Set the `script-shell` of npm to bash via

`npm config set script-shell "PATH\TO\Git\bin\bash.exe"`

### Installing

Just call `npm run init`

## 2. Creating Packages and Libraries

In the root of the project, either call `npm run create-lib NAME` or `npm run create-package NAME`, depending on if you want to create a library or a package. Inside this call a `lerna` command is executed first and then some smaller file changes are done after.
Your package name will be `@shapediver/NAME`.


## 3. Bootstrapping

One great feature of `lerna` is bootstrapping. As we have multiple packages, the either rely on each other or have the same dependencies, installing the dependencies per package doesn't make sense.

### External Dependencies

For external dependencies, install them in the root of the project, then copy the name and version number to the package where you need it and call `npm run bootstrap` in the root of the project. `lerna` will link the dependencies accordingly.

Example:
- I want to have the dependency `three` in my package `a_package_that_has_three`.
- I install `three` in the root via `npm i three`.
- I know manually add the installed `three` version (`"three": "^A.B.C"`) of the global `package.json` to the `package.json` of the package `a_package_that_has_three`
- I call `npm run bootstrap`

If the package is already installed on the root, only the two last steps are needed.

### Internal Dependencies

For internal dependencies it is even easier. In this case just add the name and version number of the package you want to add to the `package.json` and run `npm run bootstrap` in the root of the project again.

Example:
- I want to have the dependency `a_package` in my package `another_package`.
- I manually add the package (`"a_package": "^A.B.C"`) to the `package.json` of the package `another_package`
- I call `npm run bootstrap`

## 4. Building

There are various build tasks for different scenarios in each package.

| Usage | Description |
| ------------- | ------------- |
| `npm run build` | Builds just the current package. (folder: `dist`) |
| `npm run build-dep` | Builds this package and all internal dependencies that it has before that. (folder: `dist`) |
| `npm run build-dev` | Builds this package and all internal dependencies with webpack and starts a http-server in watch mode. (folder: `dist-dev`, only for actual packages) |
| `npm run build-prod` | Builds this package and all internal dependencies with webpack and puts them into a single file.  (folder: `dist-prod`, only for actual packages) |

## 5. Testing

Call `npm run test` to test all packages or `npm run test` in a package to just test that single package.
Testing is configured via jest and should be fairly easy to use.

## 6. Publishing

To publish a package, please refer to [this](https://github.com/lerna/lerna/tree/main/commands/publish) page as this might be different for different packages. Should also probably be discussed.