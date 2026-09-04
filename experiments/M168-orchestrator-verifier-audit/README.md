# M168 orchestrator-verifier audit reproductions

These scripts never mutate the repository under audit. They materialize a Git archive in a temporary directory and apply every mutation there.

The default target is commit `f267bbccfd450982720f747c64e383376df2c4f9`, the 52-claim / 10-control revision described in the assignment. `semantic_attacks.py HEAD`, `restore_crash.py HEAD`, and `claim_inventory.py HEAD` audit the current checked-out revision instead.

```powershell
python -B experiments\M168-orchestrator-verifier-audit\semantic_attacks.py
python -B experiments\M168-orchestrator-verifier-audit\semantic_attacks.py HEAD
python -B experiments\M168-orchestrator-verifier-audit\claim_inventory.py HEAD
python -B experiments\M168-orchestrator-verifier-audit\restore_crash.py HEAD
python -B experiments\M168-orchestrator-verifier-audit\probe_attacks.py
python -B experiments\M168-orchestrator-verifier-audit\date_audit.py

# Pin the revised apparatus requested in the follow-up audit.
python -B experiments\M168-orchestrator-verifier-audit\semantic_attacks.py 7c65f8a4444d2c2fb239e589f56466da9e7aa7e2
python -B experiments\M168-orchestrator-verifier-audit\claim_inventory.py 7c65f8a4444d2c2fb239e589f56466da9e7aa7e2
python -B experiments\M168-orchestrator-verifier-audit\restore_crash.py 7c65f8a4444d2c2fb239e589f56466da9e7aa7e2
```

`experiments/M134-kernel-frontier/M137-clamped-detail.md` was an untracked live dependency at audit time. If it is present at the audited SHA-256 (`8EA64C98795E51BC007E04775866C2145D1E2D6CFBA9F4F13B8413A3721FD1EF`), the scripts copy it. A clean checkout instead receives a one-token scratch fixture sufficient for that unrelated presence claim; the report identifies the missing committed dependency as a defect.

```powershell
# Defaults to the requested 61-claim revision, 7c65f8a4.
python -B experiments\M168-orchestrator-verifier-audit\boundary_attacks.py
# A commit argument attacks the same matcher in a later revision.
python -B experiments\M168-orchestrator-verifier-audit\boundary_attacks.py HEAD
```
