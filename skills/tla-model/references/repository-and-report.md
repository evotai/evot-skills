# Repository and report conventions

## Repository files

```text
<models-root>/
├── AGENTS.md
└── <model_name>/
    ├── <Module>.tla
    ├── model.json
    └── README.md
```

Create `<models-root>/AGENTS.md` once:

```markdown
# TLA+ models

Use the evot `tla-model` skill to create, change, run and triage these models; read its SKILL.md first.

- One directory per protocol: `<Module>.tla`, `model.json`, and `README.md` with the modeled logic and full bound source commit.
- Run: `python3 <tla-model skill>/scripts/tlc_run.py <models-root>/<model>`. The installed skill is at `~/.evotai/skills/tla-model/`.
- Default is replay of the bound model: do not scan current code diffs, auto-correct the model or change its source binding.
- Only an explicit request to validate the current branch/PR/latest code authorizes source synchronization. Follow the skill's consistency review, update for semantic changes and rerun every case; record review separately from TLC results.
- Never commit generated `.cfg` files, traces, jars or logs. These checks are not part of CI.
```

Keep each model README about 40 lines or fewer; do not duplicate `scope` or `source_map`:

````markdown
# <Module>

<The modeled logic and safety question, in plain terms.>

| | |
|---|---|
| Bound source | <repository> `<full commit>`; clean/dirty, reviewed patch artifact if dirty |
| Consistency review | <date>: unchanged semantics / model updated / unverified; brief reason |
| Generated with | evot `tla-model` skill `<evot-skills commit>`, TLC 1.8.0 |
| Last TLC run | <date>, <model/config revision or hashes>: <passed>/<total> checks; normal cases <distinct states> distinct states |

## Modeled logic
- <step group>: `<path>::<function>`

## Safety properties
- `<Invariant>`: <meaning>

Bounds and abstractions are in `model.json` `scope`, the action-to-code map in `source_map`, and resolved model errors in `audit`.

## Run
```bash
python3 <tla-model skill>/scripts/tlc_run.py <models-root>/<model_name>
```
````

## Report

Replay writes results to external artifacts, not the model README. Create/update repository documentation only for authorized modeling, repair or source synchronization.

Write in the user's language. Keep this order, omit empty sections, and put the verdict first without a preamble or closing recap:

````markdown
**Verdict:** <confirmed bug | model error | property/assumption error | not reproduced | passes within bounds | source correspondence unverified | unresolved>, <key reason and repair status, if any>.

## Scope
- Logic: <source snapshot or design>, <main files::functions>
- Mode: <replay of bound commit / explicit sync to requested target>
- Source consistency: <not rechecked in replay / reviewed target, clean/dirty status and outcome>
- Property: <safety property in user terms>
- Bounds: <actors, operations, retries, time samples>; abstractions: <relevant ones>

## Results
| Check | Result | Distinct states |
|---|---|---|
| Normal configurations (N) | all exhaustive / K failed | <total> |
| Mutation controls (M) | each found its expected violation | |
| Witnesses (W) | all reachable | |

## Counterexample
<case>: <invariant>, <classification>.

| Step | Action | Code | Effect |
|---|---|---|---|

- Protection lost at step <n>: <missing information or check>
- Final state: <what exists> vs <what is still referenced>
- Evidence: <source line, artifact, or native test result and which check fired>

## Not covered
- <behavior outside the bounds or model>

## Rerun
```bash
<command>
```
Artifacts: <path>
````

Use the counterexample section for normal-case failures or a requested trace. For deliberate mutations, name the disabled code check and explicitly say it is not a bug. Include only relevant steps; merge consecutive steps without relevant changes. Never call a bounded pass a proof or a model error an implementation bug.
