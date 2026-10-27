# Lesson 01 · Launch the calculator

**Goal:** work with an AI agent to put a tested image behind your existing HTTPS
proxy, then explain what proves it works. You are practicing a small, visible
AI collaboration cycle: **Try → Decide → Build → Check → Keep**.

Read the current step when the coach reaches it. The [README](../README.md)
gets you into the project; you do not need to prepare every value or copy all
commands before starting.

## 1 · Try and locate the work

In your LAPTOP clone, let the agent confirm your folder/SSH remote and run
`python3 studio.py setup`. It prepares the Python tools and Chromium. Keep this
chat connected while troubleshooting. No application clone or Node setup is
needed for this lesson.

Try the [classroom calculator](https://calc.mywebclass.org) and describe one
result you see. Its current page calls itself “IS373 Content Management System”
and mentions automatic deployment. Here you are launching a fixed published
calculator image; automatic delivery of your own code comes in a later lesson.

**Checkpoint:** you can find this project in the agent and distinguish the
classroom example from the calculator you will launch.

## 2 · Decide and inspect

Agree `STUDIO-001`: add one published calculator image on your existing server,
preserving its proxy and websites. The agent asks for your usual SSH command
first, then helps find the hostname and existing proxy network one value at a
time. Configuration is saved locally and ignored by Git.

The coach uses `configure`, `plan` and read-only `doctor`. You do not need to
guess the network name. A missing Docker/Traefik/HTTPS baseline is a gap to fix
with help, not a reason to run fresh-server installation over your working host.
Keep credentials, private keys and raw server dumps out of the conversation.

Before the plan is explained, make a short prediction: how will a request for
your new hostname reach the calculator? A guess or hint is fine.

Create the prepared lesson issue in YOUR GitHub copy, review its short scope and
create a feature branch. The agent can use GitHub in its browser/connector;
`python3 studio.py issue --open` opens the form; plain `issue` prints its URL.
After posting, record its actual
URL with `python3 studio.py issue --url ACTUAL_URL`. Template copies do not
inherit the instructor's issues. No new GitHub CLI is required.

**Checkpoint:** the intended server/hostname/image are clear, the prerequisite
checks pass or show an explicit gap, and your issue records the agreed scope.

## 3 · Build: review, then launch

Review the plan with the coach: target server, hostname, existing network and
pinned image. Then let it run `launch` from your LAPTOP clone. The CLI sends the
small runtime bundle over SSH/SCP; you do not SSH-clone a second project on the
server. The existing proxy supplies HTTPS.

If a matching deployment already exists, the coach must explain and agree its
adoption explicitly. “Verified existing deployment” is different from “newly
launched.” An occupied hostname is not permission to replace its current route.

**Checkpoint:** one scoped calculator deployment is running or explicitly
adopted; unrelated services remain in place. The SPEC identifies which happened.

## 4 · Check: AI first, then you

The agent runs `verify` for the actual runtime, trusted public HTTPS and valid/
invalid API cases. It runs `check` for prepared Black, Pylint, pytest and a local
real-browser journey, reviews the result, and fixes actual failures. These tools
help make checks repeatable; passing is not proof of every possible behavior.

Full local browser E2E needs local Docker. Without it, the agent reports that
limit and runs `python3 studio.py check --fast` for local formatting, analysis
and non-E2E tests. Later, push the reviewed branch and open the PR to run full CI;
wait for its actual E2E result and link the run before claiming a full check.
You can continue remote deployment checks meanwhile. Server Docker alone does
not make your laptop's E2E run. No local Docker installation is required for
this alternative; an unrun or skipped check stays unrun or skipped.

Discuss one actual result: what input was tried, what was expected, and what the
result establishes. Positive/negative are cases; unit/integration/E2E are levels.
For example, valid arithmetic and rejected invalid input are different cases;
neither alone establishes the entire public browser journey.

Now open YOUR calculator URL. Try `6 × 7` and describe what you actually see in
the browser and API results. The coach's browser check supplements yours.

**Checkpoint:** actual checks and your observation are recorded separately, with
their limits. A published image or green CI alone does not prove deployment.

## 5 · Keep a result you can explain

Tell the coach whether to keep or revise the result and why. Use `status` to see
the next checkpoint; it is a reminder, not an automatic grade. `report` exports
sanitized actual evidence to `studio/evidence.json`. Review it before sharing.

Keep the agreement and evidence links in SPEC.md and your short contributions
in LEARNING.md. Review/correct/remove the AI-drafted excerpts before they are
committed or pushed. They are a summary, not a transcript or proof of authorship.

Review the diff, commit and push the branch over SSH, and open a PR linked to the
lesson issue when you are ready. If the agent cannot use a logged-in GitHub
browser/connector, you create it on your copy's GitHub page: **Pull requests →
New pull request**, base `main`, compare your feature branch. Give the coach
the created PR URL; no extra CLI or shared login is needed.
Record its actual latest CI result and
save its link with `python3 studio.py issue --pr ACTUAL_PR_URL`. Merge and
close the issue only when the recorded scope is satisfied, preserving any
missing learner explanation as a gap rather than inventing it.

After merging and closing the issue, return to your LAPTOP clone and run one
command at a time:

```sh
git switch main
git pull --ff-only origin main
python3 studio.py status
```

Merging starts checks on `main` too. If status says CI is pending, wait for
that run and rerun `python3 studio.py status`; do not launch again.

Discuss any remaining checkpoint or unavailable GitHub check with the coach.
Do not turn a missing result into a completion claim.

**Done has three parts:** technical checks and live release evidence; your actual
explanation/observation; and verified GitHub PR/issue state. Timestamps establish
recorded activity, not time spent or learning. No extra application feature,
server upgrade or rollback exercise is required here.
