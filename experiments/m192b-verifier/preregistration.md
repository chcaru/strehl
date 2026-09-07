# M192b: prospective verification of M192 evidence

Registered 2026-09-07 before implementation. Prior evidence:
`docs/research/M192-terminal-verification.md`, the independent completed-run audit,
M139, M172, M178, M182, and the current execution plan. This implements the
independent review's missing bindings; it does not remeasure M12.

The original verifier, protocol, campaign and verdicts stay unchanged. A separate
entry point retains the original bar calculations and adds semantic checks on the
recorded commands, cleared environment, IDs, input counts, complete log/sidecar
membership, commissioning readings, and actual CPU trace. It reads an artifact
directory without accessing captures or executing its recorded commands.

Falsifiers: a re-sealed wrong gate, worker setting, uncleared environment,
missing/foreign campaign ID, contradictory input manifest, omitted terminal key,
missing/corrupt commissioning log, mismatched binary/sidecar, fabricated
commissioning boolean, truncated/duplicated CPU trace, or trace summary drift
must fail. Negative controls must reach the whole public verification function;
chain and terminal hashes are recomputed so stale-checksum rejection alone does
not count. An inert label and the complete original package must be accepted
with exactly the original one-pass/three-unmeasured outcome. Failed product bars
are valid evidence and must not be mistaken for invalid artifacts.

No claim of authenticity against a party rewriting every record and log is made.
The trusted anchor is the repository's frozen protocol and verifier lineage;
the checked property is consistency of recorded evidence. No output pixels are
retained, so their hashes remain campaign receipts. New checks are prospective;
they cannot improve any recorded memory/timing disposition. A different agent
must challenge the implementation before acceptance. All mutations use copies,
and original artifact bytes are hashed before and after commissioning.
