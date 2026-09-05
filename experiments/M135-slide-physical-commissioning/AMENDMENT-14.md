# M135 slide commissioning amendment 14

Status: **SECOND DETERMINISTIC-SERIALIZATION REPAIR BEFORE COMMIT**

Ten decimal places were still one place too fine for OpenCV's diagnostic edge
support.  Fresh-process runs alternated between:

- `55ad6996bb416296ac53a06a603111f0b57e2d96c6d8e0b0a7c6ca068e0fb03a`;
- `d41eaa250a255fd82b4a17c45bb57ee27b764d959338b05ba5de0bf9f1692872e`.

The two files are preserved as
`commission-run5-nondeterministic-{before,after}.json`.  Only three diagnostic
fields differed, each by `1e-10`; selected corners and all 55 checks were
identical.  Diagnostic serialization is reduced to eight decimal places.
Decision arithmetic remains unrounded.
