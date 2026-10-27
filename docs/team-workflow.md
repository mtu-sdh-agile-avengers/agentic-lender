# Team workflow

This document describes our team’s internal working processes. If you are an external contributor, please familiarize yourself with [CONTRIBUTING.md](../CONTRIBUTING.md).

- [Team workflow](#team-workflow)
  - [How we work](#how-we-work)
  - [Jira issue lifecycle](#jira-issue-lifecycle)
  - [Step-by-step workflow](#step-by-step-workflow)

## How we work

Our team is operating inside of [**Scrum framework**](https://www.scrum.org/learning-series/what-is-scrum/), using [**Jira**](https://www.atlassian.com/software/jira/guides/getting-started/introduction) as an issue tracking system. Our selected branching strategy is (simplified) [**GitFlow**](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow), but [**Trunk Based Development**](https://trunkbaseddevelopment.com/) also could be utilized (it helps reduce merge conflicts, simplify code-reviews).

> [!NOTE]
> Branching strategy was simplified since creation of numerous small branches slowed down development in our case.

Our **Ground Rules** include:

- each push to `main` (trunk) branch goes through PR (never directly)
- devlopment branch exists for each subsytem (`<subsystem>/dev`); long-running branch
- specific issue branch could exists for 1 sub-task OR task (`<type>/<jira-issue-key>-<description>`); short-running branch; delete local and remote after issue is completed
- if CI fails (red), then fix it before merging

> [!WARNING]
> CI is not currently implemented.

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

1. **Pick up assigned Jira sub-task** (or a task, if applicable) for the current Sprint and **move it to In Progress**.

2. **Switch to `main` and pull changes** from the `main` (trunk) branch:

    ```bash
    git switch main
    git pull
    ```

> [!NOTE]
> It helps to stay up-to-date with others, and prevent merge conflicts beforehand (fail fast).

3. Now, there is two possible outcomes (depending which branch strategy you prefer to use).

    **Switch to your dev branch**, `pull` changes from main if required:

    ```bash
    git switch <subsystem>/dev
    ```

    OR
   
   **Create and switch to a separate branch** related to the Jira work-item following [branch naming guidelines](../CONTRIBUTING.md#branch-naming):
   
   ```bash
    git switch -c <type>/<jira-issue-key>-<description>
    ```

4. **Stage and commit changes** following [commit message guidelines](../CONTRIBUTING.md#commit-message-format):

    ```bash
    git add .
    git commit -m "<type>: <description>"
    ```

> [!IMPORTANT] Important
> For **GitFlow**, **always** include Jira issue key (if applicable) inside of the commit message for your dev branch. For **Trunk-Based**, include it inside of the **short-lived** branch name. It helps to understand exactly which commit / branch relates to what.
>

5. **Push the branch** and **open a Pull Request** into `main` branch, then **move assigned Jira sub-task to "In Review"**.

    ```bash
    git push
    ```

    OR

    ```bash
    git push -u origin <branch-name>
    ```

6. Wait until code review will be conducted (by [Teki Shodo](https://github.com/tekisho) or [Pashokkkk](https://github.com/Pashokkkk)).

7. Once approved and CI is green, **Squash and Merge** into `main` branch, then **move assigned Jira sub-task to Done**. Then (if not in your `dev` branch) don't forget to remove remote and local branch:

    ```bash
    git push origin --delete <branch-name>
    git switch main
    git pull
    git branch -D <branch-name>
    ```

    **Otherwise** move the issue back to In Progress and return to step 4.

> [!NOTE]
> Why **squash and merge** but not **merge commit** or **rebase**? A single "squashed" commit is easier to `git revert` than multiple of them.
