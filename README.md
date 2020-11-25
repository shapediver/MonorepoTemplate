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

One great feature of `lerna` is bootstrapping. As we have multiple packages, the either rely on each other or have the same dependencies, installing the dependencies per package doesn't make sense. Also, bootstrapping checks for circular dependencies, which makes our life that much easier.

Therefore there are two scripts (one for normal dependencies, one for devDependencies) that use `lerna` and will make your life easier. I will just explain the script for normal dependencies, but the script for devDependencies works just the same. (just replace `add-dependency` with `add-devDependency` in the examples below)

### Example 1 - adding an external dependency

Let's say we want to add the package `three` to a specific package `a_package`.
Then the only thing we have to do is call `npm run add-dependency three @shapediver/a_package` in the root folder.
This installs the package in the root and links it to `a_package`.

In case you want `three` in all packages and libs you can call `npm run add-dependency three`.

### Example 2 - adding an internal dependency

Now I want to add `a_package` to `another_package` (both are part of this repository).
This works just similarly with `npm run add-dependency @shapediver/a_package @shapediver/another_package`.

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

TODO

## 7. Example

So this is the goal of our example. We want to create to packages, `package_A` and `package_B`, where `package_B` has a dependency on `package_A`. After, we want to publish both packages.

First we create both packages:
```bash
npm run create-package package_A
npm run create-package package_B
```

Then we add some extremely simple logic to the `index.ts` of `package_A`:
```typescript
const package_A = (): string => {
  return 'Hello ShapeDiver!';
};

export default package_A;
```

Then we add a dependency of `package_A` to `package_B` to be able to use `package_A` there:
```bash
npm run add-dependency @shapediver/package_A @shapediver/package_B
```

In the `index.ts` of `package_B` we'll now also add some simple logic that uses `package_A`:
```typescript
import package_A from '@shapediver/package_A';

const package_B = (): string => {
  return 'What does package_A say? ' + package_A();
};

export default package_B;
```

Let's now build `package_B` with a command that builds also it's dependencies `npm run build-dep` (in the packages/package_b folder).

Now we want to publish `package_B`, as this package is dependent on `package_A`, we need to publish that as well.

TODO