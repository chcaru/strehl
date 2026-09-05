# M135 slide commissioning amendment 15

Status: **FULL TERMINAL RECOMPUTATION BEFORE COMMIT**

The signoff review found the remaining self-consistent-artifact hole: terminal
summary reran Stage A and C but trusted Stage B's internally agreeing rawpy and
rawler checksum fields.

`summarize` now reruns all data-bearing stages from the bound inputs:

1. Stage A through the frozen ExifTool binary;
2. Stage B through rawpy and the frozen stdout-only rawler executable on every
   frame;
3. Stage C from the reproduced decode;
4. Stage D from the same-byte hashed ledger and matched-flat manifest; and
5. Stage E from the reproduced inventory/decode and Stage D ledger.

Each complete measurement projection must match its supplied artifact before
any terminal state is reported.  New decode- and flat-recompute mutations must
go red.  This is intentionally expensive: a claim-bearing terminal summary is
not a metadata-only convenience.
