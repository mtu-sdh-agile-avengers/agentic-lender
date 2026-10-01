# Team workflow

This document describes our team’s internal working processes. If you are an external contributor, please familiarize yourself with [CONTRIBUTING.md](../CONTRIBUTING.md).

- [How we work](#how-we-work)
- [Jira issue lifecycle](#jira-issue-lifecycle)
- [Step-by-step workflow](#step-by-step-workflow)

## How we work

Our team is operating inside of [**Scrum framework**](https://www.scrum.org/learning-series/what-is-scrum/), using [**Jira**](https://www.atlassian.com/software/jira/guides/getting-started/introduction) as an issue tracking system. Our selected branching strategy is [**Trunk Based Development**](https://trunkbaseddevelopment.com/), since it helps reduce merge conflicts, simplify code-reviews and speed-up development process for such a small team as we are.

Our **Ground Rules** include:

- each push to `main` (trunk) branch goes through PR (never directly)
- 1 sub-task OR task = 1 branch = 1 PR
- issue branch should be short-lived (delete local and remote after issue is completed); the only long-running branch is `main` (trunk)
- if CI fails (red), then fix it before merging

## Jira issue lifecycle

![Jira workflow diagram](/docs/imgs/jira_workflow.png)

| Issue status | Meaning                                                                                        |
|--------------|------------------------------------------------------------------------------------------------|
| To Do        | Included in sprint backlog, but not started yet                                                |
| In Progress  | Someone is working on it and has created related branch                                        |
| In Review    | A pull request is open and waiting for the code review; if declined, could move to In Progress |
| Done         | PR merged after code review; if bug is found, then new Issue of type Bug is created            |

> [!NOTE]
> You can ignore `step-back` transitions, they exist only for testing and management purposes.

## Step-by-step workflow

Typically, the following sequence of steps describes the workflow of one of our team members:

1. **Pick up assigned Jira sub-task** (or a task, if applicable) for the current Sprint and **move it to In Progress**

2. **Switch to `main` and pull changes** from the `main` (trunk) branch:

    ```bash
    git switch main
    git pull
    ```

> [!NOTE]
> It helps to stay up-to-date with others, and prevent merge conflicts beforehand (fail fast).

3. **Create and switch to a separate branch** related to the Jira work-item following [branch naming guidelines](../CONTRIBUTING.md#branch-naming):

    ```bash
    git switch -c <type>/<jira-issue-key>-<description>
    ```

> [!IMPORTANT]
> **Always** include Jira issue key inside of the branch name, so if Jira is integrated with GitHub it could link it to the branch created (it also helps to understand exactly which branch relates to what).

4. **Stage and commit changes** following [commit message guidelines](../CONTRIBUTING.md#commit-message-format):

    ```bash
    git add .
    git commit -m "<type>: <description>"
    ```

5. **Push the branch** and **open a Pull Request** into `main` (trunk) branch, then **move assigned Jira sub-task to In Review**

    ```bash
    git push -u origin <branch-name>
    ```

6. Wait until code review will be conducted (by [Teki Shodo](https://github.com/tekisho) or [Pashokkkk](https://github.com/Pashokkkk))

7. Once approved and CI is green, **Squash and Merge** into `main` (trunk) branch, then **move assigned Jira sub-task to Done**. Then don't forget to remove remote and local branch:

    ```bash
    git push origin --delete <branch-name>
    git switch main
    git pull
    git branch -D <branch-name>
    ```

    **Otherwise** move the issue back to In Progress and return to step 4.

> [!NOTE]
> Why **squash and merge** but not **merge commit** or **rebase**? A single "squashed" commit is easier to `git revert` than multiple of them.
