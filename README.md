# IS373 Server Studio

**Launch a calculator on the server you already built—with an AI coach—and show
what proves it works.** Your first lesson uses a published image, your existing
Docker/Traefik setup and one public HTTPS hostname. You practice agreeing a small
specification, letting AI build and test, inspecting the result, and keeping
visible evidence in GitHub.

You need your usual server SSH access, Docker and working Traefik/HTTPS. Missing
prerequisites become explicit gaps to troubleshoot with the coach. Start with
your existing server; keep fresh-server installation for a separate task.

## Start here — on your laptop

1. Choose **Use this template → Create a new repository** on
   [373_hosting](https://github.com/kaw393939/373_hosting). Make your own public
   copy named `my-server-studio`. Wait until it displays its README and files.
2. Use your usual class terminal and GitHub SSH setup. Replace `YOUR-USERNAME`,
   then run one command at a time:

   ```sh
   git clone git@github.com:YOUR-USERNAME/my-server-studio.git
   cd my-server-studio
   pwd
   git remote -v
   ```

   If Git says the clone is empty, wait until GitHub shows its README, then
   run `git pull --ff-only origin main` inside the clone. Do not create the
   missing files yourself.

3. Open this cloned folder as a **local project** in ChatGPT desktop/Codex or an
   agent that can read/edit local files and run terminal commands. Browser
   control helps with review. VS Code is optional. Start one chat:

   > Read README.md, AGENTS.md, SPEC.md and LEARNING.md. Guide me through studio/lesson-01.md one small step at a time. Confirm my folder and SSH remote first, help me run setup, then ask for my usual server SSH command. Wait for my predictions and observations; do not invent my answers or change my server before we review the plan.

4. Let the connected agent check Python 3.12+ and run `python3 studio.py setup`
   in this laptop clone. It prepares the Python tools and Chromium and helps
   with actual setup errors. Give the coach one requested nonsecret value at a
   time; you do not need to collect every server detail first.

**First checkpoint:** the agent can read your clone, setup works, and your next
step is clear. Keep the same project and chat. The coach will help inspect your
existing server before proposing a change. Keep passwords, tokens, keys and raw
server dumps private.

## One lesson, one visible result

Follow [Lesson 01](studio/lesson-01.md) as the coach reveals each step:

**Try → Decide → Build → Check → Keep**

Try the [classroom calculator](https://calc.mywebclass.org), agree a small scope,
launch the image, let AI check it, then try YOUR public calculator and explain
one actual result. The current calculator UI says “IS373 Content Management
System” and mentions automatic deployment; this first lesson launches a fixed
image. Your own application and automatic code delivery come later.

The CLI runs from this laptop clone and sends a scoped bundle over SSH/SCP.
Your server does not need a GitHub key or an application source clone. A matching
existing deployment can be adopted only after explicit review; that is recorded
as verification of existing work, rather than a new launch.

The prepared `check` combines Black, Pylint, pytest and real-browser checks.
Full local E2E needs local Docker; without it, the coach uses `check --fast`
locally and the PR's full CI for E2E, keeping unrun checks explicit. No Node
setup is needed for this lesson. `status` names
the next checkpoint; it cannot certify understanding or close a GitHub issue.

| File | What it holds |
|---|---|
| [SPEC.md](SPEC.md) | Agreed scope and links to actual implementation/evidence |
| [AGENTS.md](AGENTS.md) | Short, paced coaching behavior |
| [LEARNING.md](LEARNING.md) | Your explanations, observations and help received |
| [Lesson 01](studio/lesson-01.md) | Current actions and success checkpoints |

The agent drafts a short LEARNING.md summary, not a transcript or grade. It may
be public: review, correct or remove excerpts before commit/push. Your issue and
PR belong to YOUR repository; template copies do not inherit instructor issues.
`python3 studio.py issue --open` opens the prepared form; plain `issue` prints its URL.
Checks, live behavior, learner contributions and GitHub completion are separate
claims. Timestamps record activity, not learning.

**Returning later:** reopen the same clone/chat and ask the coach to read SPEC
and LEARNING and resume the next checkpoint. You normally do not clone again.

## Next · build your application

After keeping the calculator lesson, start the separate
[IS373 App Studio](https://github.com/kaw393939/is373-app-studio).
Its README guides a new template copy and laptop clone: first a branded FastAPI
homepage, then signup/login and member/admin roles. Keep this repository for
your server. The app starts locally; deployment is a later agreed step.

## Hosting textbook — reference when needed

These chapters explain the existing infrastructure. They are not a second
onboarding path. Do not run fresh-server installation over a working host.

| Chapter | Topic |
|---|---|
| [1](book/01-architecture.md) | Request path, DNS, ports, TLS and routing |
| [2](book/02-server-and-dns.md) | Server and DNS preparation |
| [3](book/03-docker.md) | Docker installation and concepts |
| [4](book/04-deploy.md) | Hosting-stack generation and deployment |
| [5](book/05-https-dashboard.md) | HTTPS and the private dashboard |
| [6](book/06-troubleshooting.md) | Diagnosing one layer at a time |
| [7](book/07-operations.md) | Deliberate operations and recovery |
| [8](book/08-assessment.md) | Original hosting exercises and glossary |
| [9](book/09-configuration-files.md) | Configuration-file walkthrough |
| [10](book/10-application-delivery.md) | Older full application-delivery integration |

[Complete hosting examples](examples/full-stack/README.md) and
[host configuration references](examples/host-config/README.md) remain available.
The older Chapter 10 application-checkout/Make/WUD route is reference material;
Lesson 01 uses the server CLI and published image instead.

This repository owns hosting and its studio CLI. The separate
[calculator source](https://github.com/kaw393939/is373_ci_cd) owns application
code, tests and image publication; you can inspect it without making another
student clone. No application source or publishing workflow is copied here.

[VALIDATION.md](VALIDATION.md) states what repository and instructor checks
actually established. Optional worked records cover
[private dashboard access](book/changes/2026-10-26-dashboard.md),
[backup/restore and host maintenance](book/changes/2026-10-26-maintenance.md), and
[application dependency maintenance](book/changes/2026-10-26-certifi.md).
Those historical operations add no required task or permission to repeat them.
