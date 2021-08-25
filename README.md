![logo](https://sduse1-assets.shapediver.com/production/assets/img/apple-icon.png "ShapeDiver")
# Monorepo Template

This Repository is here to be used if you want to have multiple npm packages in one repository. These packages can be reliant on each other or completely separate.

The setup is built on `lerna` which is a package that is build for handling javascript monorepos. I extended some functionality and created some further custom scripts for creating packages and building them. But trust me, there is no magic involved, mostly just creating a nice project setup.

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
Your package name will be `@shapediver/SCOPE.NAME`. Where the scope is defined in the `scope.json` of the root directory. For why we use scopes, look [here](https://shapediver.atlassian.net/wiki/spaces/SS/pages/953352193/Naming+of+Github+Packages).


## 3. Bootstrapping

One great feature of `lerna` is bootstrapping. As we have multiple packages, the either rely on each other or have the same dependencies, installing the dependencies per package doesn't make sense. Also, bootstrapping checks for circular dependencies, which makes our life that much easier.

Therefore there are two scripts (one for normal dependencies, one for devDependencies) that use `lerna` and will make your life easier. I will just explain the script for normal dependencies, but the script for devDependencies works just the same. (just replace `add-dependency` with `add-devDependency` in the examples below)

### Example 1 - adding an external dependency

Let's say we want to add the package `three` to a specific package `a_package`.
Then the only thing we have to do is call `npm run add-dependency three @shapediver/test.a_package` in the root folder.
This installs the package in the root and links it to `a_package`.

In case you want `three` in all packages and libs you can call `npm run add-dependency three`.

### Example 2 - adding an internal dependency

Now I want to add `a_package` to `another_package` (both are part of this repository).
This works just similarly with `npm run add-dependency @shapediver/test.a_package @shapediver/test.another_package`.

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

Publishing can only be done for the whole repository at once, to keep the versioning simple. We publish to github packages, where you can see the all packages of the whole organization here: https://github.com/orgs/shapediver/packages
Naturally, please be smart with the naming of packages.

First, if you haven't already, create an access token on github. An explanation can be seen [here](https://docs.github.com/en/free-pro-team@latest/github/authenticating-to-github/creating-a-personal-access-token). You need permissions for `repo`, `write:packages`, `read:packages` and `delete:packages`.

Then create on the root of this repository a `.npmrc` file, if there isn't one already and add the following.
```bash
//npm.pkg.github.com/:_authToken=TOKEN
registry=https://npm.pkg.github.com/shapediver
@shapediver:registry=https://npm.pkg.github.com/
```

Here just, replace `TOKEN` with you access token that you just created.

Afterwards, just call `npm run publish` and follow the prompts.

## 7. Example

So this is the goal of our example. We want to create to packages, `package_a` and `package_b`, where `package_b` has a dependency on `package_a`. After, we want to publish both packages.

First we create both packages:
```bash
npm run create-package package_a
npm run create-package package_b
```

Then we add some extremely simple logic to the `index.ts` of `package_a`:
```typescript
const package_a = (): string => {
  return 'Hello ShapeDiver!';
};

export default package_a;
```

Then we add a dependency of `package_a` to `package_b` to be able to use `package_a` there:
```bash
npm run add-dependency @shapediver/test.package_a @shapediver/test.package_b
```

In the `index.ts` of `package_b` we'll now also add some simple logic that uses `package_a`:
```typescript
import package_a from '@shapediver/test.package_a';

const package_b = (): string => {
  return 'What does package_a say? ' + package_a();
};

export default package_b;
```

Let's now build `package_b` with a command that builds also it's dependencies `npm run build-dep` (in the packages/test.package_b folder).

Let's create a commit for our changes, we need this as for publishing, a tag is created on that commit.

Now we want to publish the repository, therefore we just call `npm run publish` and follow the prompts there (please see the part about publishing a bit above).


## 7. FAQ

- I add a dependency, but in the typescript file, it still shows me an error. What is up with that?

The VSCode typescript language server has some issues, just restart it or VSCode in general.
