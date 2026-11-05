# Optional induction diagnostics

Read only when a candidate inductive invariant fails or the user requests proof preparation. Ordinary code audits stay on the TLC reachability workflow; do not install Apalache/TLAPS or start a benchmark as a side effect.

## Separate safety from induction

A safety predicate can hold in every reachable state without being inductive over all states satisfying that predicate. Introduce an auxiliary candidate `IndInv` only when needed. It should have enumerable finite domains for every variable (`TypeOK`) plus justified structural facts; keep the user's safety goal unchanged.

Check three different obligations:

| Obligation | Meaning of failure |
|---|---|
| `Init => IndInv` | The candidate rejects a legal initial state. |
| `IndInv /\ Next => IndInv'` | The candidate is not closed under a transition. The starting state may be unreachable from the real `Init`. |
| `IndInv => Safety` | The candidate permits a state violating the safety goal, not necessarily a reachable one. |

A consecution counterexample is **not** automatically a production bug. First check whether its initial state is reachable in the real specification. If it is not, identify a structural fact justified by initialization and transitions, strengthen the auxiliary candidate, and recheck all three obligations. Never fix it by weakening Safety or silently restricting Next.

## Non-invasive finite checks

Keep diagnostic definitions and tool annotations in an external scratch wrapper over the unchanged model. Record the wrapper, constants, tool version and exact command with artifacts. Do not make the real model depend on the wrapper.

For TLC, the conceptual configurations are:

| Check | Initial predicate | Next relation | Invariant |
|---|---|---|---|
| Initiation (also checks reachable preservation) | `Init` | `Next` | `IndInv` |
| Consecution | `IndInv` | `Next` | `IndInv` |
| Safety implication | `IndInv` | `UNCHANGED vars` via a wrapper operator | `Safety` |

Here `vars` is the full tuple of model variables. Disable deadlock checking for these safety diagnostics. Starting TLC from `IndInv` requires every variable to receive an enumerable domain; a predicate that merely compares variables may fail initialization rather than falsify induction. TLC's consecution setup explores from all candidate states, not just a single execution or necessarily only one step.

The shipped `tlc_run.py` fixes `INIT Init` and `NEXT Next`; it does **not** expose arbitrary induction predicates or proof backends. These diagnostics require a separate wrapper/config and explicit TLC invocation, not unsupported runner flags. Reuse the pinned TLC jar and inspect its help for the installed version. Tool-specific failures are not logical counterexamples.

Use tiny finite domains first. Domain caps and constraints may exclude transitions; record them and examine boundary counterexamples before drawing conclusions. Do not substitute randomized initial-state sampling for the required exhaustive normal cases. Finite checks can falsify a candidate, but cannot justify an unbounded theorem or a TLAPS proof step.

## If formal proof is explicitly requested

After the candidate stabilizes, prove initiation, preservation (including stuttering for `[Next]_vars`), and implication with TLAPS under explicit assumptions. A failed backend obligation can reflect missing usable facts or definition expansion, not a false theorem. Report proof-checker results separately from TLC results and source correspondence.

For the narrow case of an instantiated theorem with `ASSUME`, ensure its instantiated assumptions are discharged. If prefixed imported operators differ from local ones internally, consult the official practical hints below about bridge equalities. Do not add this workaround to ordinary TLC models.

## Sources and scope of borrowing

Reviewed TLAPS-Bench at `4da913bb37a02396ec492c2998a8ee977b9c74ef` (MIT). These are independently written adaptations of its diagnostic ideas, not imported benchmark code or a claim that it is the official TLA+ skill distribution:

- [TLAPS-Bench: inductive-invariant validation](https://github.com/specula-org/TLAPS-Bench/blob/4da913bb37a02396ec492c2998a8ee977b9c74ef/skills/tla-inductive-invariant-validation/SKILL.md): separate the three obligations; test candidates before proof; isolate diagnostics in wrappers. Its sandbox paths, benchmark checker and random sampling heuristics are not adopted.
- [TLAPS-Bench: proof hints](https://github.com/specula-org/TLAPS-Bench/blob/4da913bb37a02396ec492c2998a8ee977b9c74ef/skills/tlaps-proof-hints/SKILL.md): narrow symptom-driven lookup rather than mandatory proof machinery.
- [Official TLAPS tutorial](https://proofs.tlapl.us/doc/web/content/Documentation/Tutorial/A_simple_proof.html): explicit facts and definition expansion.
- [Official tlapm documentation change #279](https://github.com/tlaplus/tlapm/pull/279): instantiated assumptions and prefixed-operator bridge equalities.
- [Lamport: Using TLC to Check Inductive Invariance](https://lamport.azurewebsites.net/tla/inductive-invariant.pdf): primary reference linked by the upstream skill.
