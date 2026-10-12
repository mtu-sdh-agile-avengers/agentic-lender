# Contributing to Agentic Lender

First off, thank you for considering contributing to our project :3! This document describes the guidelines that our team follows (it really helps to manage the work process :O), and we would like you, as a contributor, to adhere to them too:

- [First contribution](#your-first-contribution)
- [What about issues?](#what-about-a-issues)
- [What about pull requests?](#what-about-a-pull-requests)
- [Conventions guidelines](#conventions-guidelines)
  - [Branch naming](#branch-naming)
  - [Commit message](#commit-message-format)

## Your first contribution

As an *external contributor* most likely you will follow the next series of steps:

1. **Fork** this repository

    Click on the **Fork button** in the top-right corner of the repository page. Then click on the **Create fork** button.

2. **Clone** your fork

    Open your forked repository, click on the **Code button**, and
    copy the repository URL using HTTPS or SSH.

    Then open terminal or Git Bash and change the current working directory
    to desired one:

    ```bash
    cd path/to/your/directory
    ```

    Finally, clone forked repository inside of selected directory
    using URL you copied earlier:

    ```bash
    git clone git@github.com:<your-name>/agentic-lender.git
    ```

3. To keep your fork up to date, **add remote** repository

    Click **Sync fork** on your forked GitHub page, then run `git pull origin main` or do it manually:

    ```bash
    git remote add upstream git@github.com:mtu-sdh-agile-avengers/agentic-lender.git
    git pull upstream main
    ```

4. Create and switch to your **branch**:

    ```bash
    git switch -c <type>/description
    ```

5. Make and **commit** your changes:

    ```bash
    git add .
    git commit -m "<type>: <description>"
    ```

6. **Push** your changes into forked repository:

    ```bash
    git push -u origin <branch-name>
    ```

7. **Open a pull request** from your forked branch into main of this repository

> [!NOTE]
> If you are wondering how OUR work process looks like or just a crew member searching for a reference, take a look at [team workflow](/docs/team-workflow.md) document.

## What about a issues?

Before you open an issue, please search the issue tracker, maybe it already exists for your problem. Otherwise, you can create one following [provided template](.github/ISSUE_TEMPLATE.md).

## What about a pull requests?

Simply follow [provided template](.github/PULL_REQUEST_TEMPLATE.md) and don't forget that:

- **Title should follow [commit message format](#commit-message-format) + Jira issue key** (only if you have access to Jira workspace).
- **Description** explains what changed and how to test it, **contains link to the GitHub issue** (if applicable); add screenshots for UI changes.
- **A PR is squashed and merged** when CI passes and at least one responsible team member approves it.

> [!IMPORTANT]
> **If changes are ever pushed directly to `main`** without PR (branch protection should normally prevent this), **always include Jira or GitHub issue key at the end of the commit message**.
>
> Without a PR, the commit message is the only link between the change and its issue.
>
> e.g. `docs: correct typo in README (ALG4-404)` or `docs: correct typo in README (#22)`

## Conventions guidelines

The conventions described below are derived from, and represent a simplified version of, [Conventional Branch 1.1.0](https://conventionalbranch.org/#spec) and [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/). It's strongly recommend that you get familiar with them before continuing, so that you understand the context better.

### Branch naming

```text
<type>/<jira-issue-key>-<description>
```

- **feat/**: For new features (e.g., `feat/ALG4-404-add-login-page`)
- **fix/**: For bug fixes (e.g., `fix/ALG4-404-header-bug`)
- **chore/**: For non-code tasks like dependency, docs updates (e.g., `chore/ALG4-404-update-dependencies`)

> [!NOTE]
> If you an external contributor, then Jira issue key could be omitted.

### Commit message format

```text
<type>: <description>
```

`e.g. feat: add login and register page ui`

- **feat** Commits that add, adjust or remove a feature to/of/from the API or UI
- **fix** Commits that fix an API or UI bug of a preceded feat commit
- **refactor** Commits that rewrite or restructure code without altering API or UI behavior
- **style** Commits that address code style (e.g., white-space, formatting, missing semi-colons) and do not affect application behavior
- **test** Commits that add missing tests or correct existing ones
- **docs** Commits that exclusively affect documentation
- **build** Commits that affect build-related components such as build tools, dependencies, project version, ...
- **ops** Commits that affect operational aspects like infrastructure (IaC), deployment scripts, CI/CD pipelines, backups, monitoring, or recovery procedures, ...
- **chore** Commits that represent tasks like initial commit, modifying .gitignore, ...
