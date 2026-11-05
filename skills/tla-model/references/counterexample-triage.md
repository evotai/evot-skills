# Counterexample triage

Use the model's bound source revision, not incidental working-tree HEAD. In replay mode, preserve the failing model and report findings; ask before repairs or source synchronization. The repair steps below require an authorized modeling/audit/repair task.

1. **Keep the artifacts.** Rerun into a new `--output` directory, never over an old one.
2. **Summarize the trace.**

   ```bash
   python3 scripts/tlc_trace.py <artifacts>/<case>/tlc.log
   ```

   It prints the violated invariant, the initial state, and each later step with its action and only the fields that changed. Use `--vars a,b` to focus on some variables and `--final` to add the full final state.
3. **Map every step** to its `source_map` entry and the exact condition in code. Find the first step where protecting information is lost, e.g. a reference that is never recorded or a check that runs on a stale view. That step is usually earlier than the final delete.
4. **Classify** the failure:
   - **Model error**: the model allows something the code forbids, such as a missing check, the wrong data shape, or wrong atomicity. Cite the code line, and ideally a real artifact. Fix the model to match the code without weakening the invariant. Add an invariant or witness for the corrected fact, record it under `audit`, and rerun everything.
   - **Property/assumption error**: the target or its premises misstate the intended contract, even if the modeled behavior is legal. Check requirements, protocol definitions and the bound implementation; for example, distinguish an entry's creation term from its commit term, and snapshot isolation from serializability. Preserve the original property, assumptions and trace. Explain the mismatch and obtain explicit confirmation before changing the target or assumptions; never weaken them just to pass. Record any authorized correction and rerun every case against it, keeping old and new results separate.
   - **Abstraction outside scope**: the trace depends on an abstraction listed in `scope`. Refine the model, or narrow the claim.
   - **Candidate bug**: every step maps to reachable code and the violated property matches the intended contract. Confirm natively before calling it a bug.
5. **Confirm natively.**
   - Use a binary or tests from the same commit.
   - Isolate storage, metadata and ports, and do not touch shared services. Ask before using shared machines, licenses or credentials, and never print or copy secrets.
   - Replay the trace order with separate sessions or nodes.
   - Assert the data outcome, and also which check fired (error code and message). A failure caused by an unrelated error, such as a missing file, does not exercise the defense being tested.
   - Stop only the processes you started. Keep the scripts and evidence.
6. **Report** using the template in [repository and report conventions](repository-and-report.md#report).
