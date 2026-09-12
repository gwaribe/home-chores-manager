# Home Chores Manager

A lightweight Django app that distributes household chores fairly across
roommates using a weighted point rotation, tracks weekly assignments, and
penalizes overdue tasks.

## Why this project?
The goal is to learn and practice how I can enhance my productivity using coding agents. How do i make the agent become a PM, engineer and tester and execute without baby sitting them.

![Docs for an agentic development](/_docs/agentic.png)

## what did i learn?
How to:
- use a chat assistant like Gemini to brainstorm and discuss the specifications.
- use Gemini to create actionalble tasks from the specifications.
### Creating roles for each agent
- assigned deepseek-v4-flash the [product manager role](/_docs/team/pm.md) to groom the tasks making them independent for development.
- assigned deepseek-v4-flash the [software engineer role](/_docs/team/software-engineer.md) to implement the tasks one at a time.
- assigned glm-5.3 [The QA role](/_docs/team/qa-engineer.md) - did the work of testing ensuring all criterias were met. If a test fail the engineer fixes it.
I put the workflow outlining each agents role in a [workflow](/_docs/process.md) file then placed it in an [Agents](/AGENTS.md) file so that each agent knows where to start.

## What were the results?
The project was done in 3hrs. I would have taken 3 days if I were to write code myself.
I hardly reviewed the code, each agent did its role well. The engineer seemed to excell in backend but the UI was unattractive. Next time i should split the role into frontend and backend and use an agent better in UI rather than deepseek-v4-flash.

## What were the challenges?
- I didn't want to keep approving what commands the agent can ran. I setup an AWS EC2 ubuntu server and setup the workspace and the agents there. I cared less on what commands were run.
- Everytime a task is implemented, the QA has to test the work and this involved switching between agents manually. To solve this an agent orchestrator is needed to automatically manage the workflow. However if i did this, the work would be done in a single session, it would create a lot of context and increasing the token usage.

---
Lessons were learnt from\
[DataTalksClub AI dev tools zoomcamp](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp)