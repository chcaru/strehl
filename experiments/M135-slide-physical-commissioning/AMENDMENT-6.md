# M135 slide commissioning amendment 6

Status: **SECOND ADVERSARIAL REVIEW FINDING FIXED BEFORE COMMIT**

The review repair was re-read by a fresh read-only reviewer.  It found that
the six flat roles were present in the required-role list but excluded from
the source-group, parent-stack, and calibration-lineage independence checks.
A ledger could therefore partition one flat directory into pseudo-captures
and still become `IDENTIFIABLE`.

The role gate now requires every required role, including all flat roles, to:

- consume one complete and unique inventoried leaf capture unit;
- carry unique source hashes, capture IDs, parent-stack IDs, flat lineages,
  and dark lineages; and
- match an exact per-role record in the separately hashed
  `m135-matched-flat-evidence-v1` manifest.

New controls plant a shared flat capture unit, a shared flat calibration,
partial group consumption, and a role/manifest identity mismatch.  No
physical threshold or preregistered role is weakened.
