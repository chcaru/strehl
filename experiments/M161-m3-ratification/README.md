# M161 M3 ratification and recommissioning

This directory versions the M3 checker rather than rewriting M152's failed
commissioning record.

## What changed

- `[bar]` is ratified at **5% of the independently selected local source step**.
- The owner-facing gate is literal: every frozen scored site must have
  `max(h_e,v_e) <= 0.05`.
- `v_e` is the maximum of the two signed-side means.
- Narrow halo and broad veil use their separately registered source plateaus.
- The external-warp gate has null, degradation, and improvement controls.

`preregistration.json` freezes the decision rules. `m3_checker_v2.py` is the
scorer. `freeze-manifest.json` pins the pre-output files.
`commission_m3_v2.py` writes `out/commission-v2.json`.

## Host lock

M153 owns the timing-sensitive host. Do not run the commissioning script, RAW
decode, rendering, package construction, or scoring until an explicit release
record exists at `packages/HOST-RELEASE.json`. The metadata-only preflight is
safe:

```powershell
python experiments\M161-m3-ratification\preflight.py
```

After release:

```powershell
python experiments\M161-m3-ratification\verify_freeze.py
python experiments\M161-m3-ratification\test_m3_checker_v2.py
python experiments\M161-m3-ratification\commission_m3_v2.py
python experiments\M161-m3-ratification\score_m3_packages.py `
  --candidate experiments\M161-m3-ratification\packages\strehl\manifest.json `
  --comparator fork=experiments\M161-m3-ratification\packages\fork\manifest.json `
  --comparator zerene-pmax=experiments\M161-m3-ratification\packages\zerene-pmax\manifest.json `
  --comparator zerene-dmap=experiments\M161-m3-ratification\packages\zerene-dmap\manifest.json
```

Each profile-package manifest must use schema
`m161-m3-profile-package-v1`, carry the frozen checker and census hashes,
attest the common-input/transfer contract, provide per-capture input-only
geometry evidence, and list one hashed `.npz` payload for every frozen M152
site. The common-input object must include lowercase SHA-256 values for the
input manifest, input-pixel set, run manifest, and final output. The scorer
also hashes the source arrays inside every payload and requires them to be
identical across products. Missing or inadequate evidence is `UNMEASURED`,
never a product failure.
