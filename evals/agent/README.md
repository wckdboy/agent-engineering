# Agent evaluation harness

This harness runs a task set in isolated Git worktrees and scores each result with the task's
verification command. It makes no assumption about the model, provider or agent CLI.

```sh
# Validate the harness itself with the deterministic stub:
./evals/agent/run.py --json

# Run a real agent. The command executes inside the task worktree.
./evals/agent/run.py --agent-cmd 'opencode run "$ENG_PROMPT"'

# Prove that a no-op agent scores zero:
./evals/agent/run.py --agent-cmd 'true'
```

The command receives `ENG_TASK`, `ENG_PROMPT` and `ENG_REPO` in its environment, and may use
`{worktree}`/`{task}` placeholders. It runs with the same filesystem permissions as the harness, so
use a sandbox for untrusted agents.

Reported metrics: pass rate on this task set, wall-clock duration, files/lines changed, agent exit
code and verification exit code. Cost is `null` because the harness cannot observe provider billing;
add it from the agent's own report if needed.

A task is valid only if its verification command **fails before** the agent runs. The harness records
`baseline_failed`; a task that already passes is marked invalid.

The task set is intentionally small (two tasks) and is a harness smoke test, not a statistically
meaningful model benchmark. Add tasks from real historical bugs, with a verification command that
fails on the parent revision.
