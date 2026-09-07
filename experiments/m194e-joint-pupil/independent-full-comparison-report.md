# Genuine M194e full-array float commissioning

2026-09-07. **MEASURED / VERIFIED: PASS_FLOAT_MODEL** for the complete frozen
five-frame, three-arm geometric model population. This is the first actual
complete fifteen-array comparison in this lane. All earlier incomplete full
campaigns remain failed and retained; none of their arrays was substituted.

The producer completed `float-run-4` under root release `b59d6ce5`, after the
committed amendment4 release/review and independent component refresh. I waited
for the terminal complete record and externally supplied result/bundle hashes
before launching the reader. No progress record or successful partial arm was
used to grant authority.

## Bound inputs and result

| Artifact | SHA-256 |
| --- | --- |
| float-run-4/result.json | 6436a4ec32255ff383c4ec674b5a80f8d854acd7973638af53738550ddd70d40 |
| float-run-4/float-bundle.json | 200da9731cc90b508b544658c4fb084f0b52d11cace116d525248a9a3812e8e1 |
| independent-full-comparison-1/result.json | 00a6a877005bfc15c33d583f70e4ef6d4f4fb334667ebc00ae61f84e0e20f42f |
| independent-full-comparison-1/float-commission.json | 4bd57b896be0b68c42fb1384a468a4f29cc54139a18a046a678dd97bad408217 |
| independent-full-comparison-1-invocation.json | 67d91f25903cb7fc03db3ba6a488b71024ab1864cb291b6aaef75204850bf530 |

The independent result contains all15 full arrays, all10 author refinement
comparisons and all5 independent-reference refinement comparisons. Each array
is the complete48x64 float64 payload:3072 pixels and775 independently fixed
edge-band pixels. Every external file/hash/type/shape/finite check passes.
Source/design bindings agree before/after the producer run and remain unchanged
through comparison. The independently chosen reference source and its primary/
refined arrays remain the original frozen bytes.

| Decisive check | Largest observed discrepancy, electrons | Unchanged limit |
| --- | ---: | ---: |
| Full-image maximum, any arm/frame | .00012419945960573386 | .004 |
| Edge-band maximum, any arm/frame | .00012419945960573386 | .004 |
| Full-image RMS, any arm/frame | .0000022448767439374392 | .0008 |
| Edge-band RMS, any arm/frame | .000004469431187679662 | .0008 |
| Author angular refinement maximum | .000000004321918822824955 | .001 |
| Author cell refinement maximum | .00012358053027128335 | .001 |
| Independent complete-reference refinement maximum | .0000005183519533602521 | .0005 |

The largest full/edge discrepancy occurs in primary frame2. No pixel, edge
subset, arm or refinement row was discarded, and no normalization, alignment,
gain fit or tolerance change was applied. The reference's underlying analytic
cell/Cartesian pupil method is independent of the author's polar radial/cell
quadrature; its previously commissioned controls and factor16 full-reference
refinement remain separately bound.

## Actual invocation and source boundary

The frozen full reader remains SHA
`e9745149a30f2754240c2970ce5d1855849679636488efecd125202831432f42`.
The separate launcher SHA is
`aebd798c2992f8e6c393bd73ae2a39100f81c4d0586593723165c90293f1aa33`.
It wrote the invocation receipt before starting the child, with exact executable,
parent `sys.orig_argv`, child argument vector, working directory, source/input
digests, explicitly fresh cache location and two-thread numerical environment.
It then preserved stdout/stderr, child exit0/result digest, elapsed wall time,
and successful after-run source/input rechecks. It did not modify the reader
or itself decide scientific acceptance.

The exact parent command was:

```powershell
python -X utf8 -X pycache_prefix=experiments/m194e-joint-pupil/work/cache-independent-comparison-launch-1 experiments/m194e-joint-pupil/independent-comparison-launch.py --bundle experiments/m194e-joint-pupil/float-run-4/float-bundle.json --bundle-sha256 200da9731cc90b508b544658c4fb084f0b52d11cace116d525248a9a3812e8e1 --author-run experiments/m194e-joint-pupil/float-run-4/result.json --author-run-sha256 6436a4ec32255ff383c4ec674b5a80f8d854acd7973638af53738550ddd70d40 --schema-sha256 1efac4ff18b704047d3386e58379e6dd5c53fc7cd28854da044d20b35c179d13 --reader-controls experiments/m194e-joint-pupil/independent-reader-controls-6/result.json --reader-controls-sha256 05042a5b6ab3cd96e447d9e2811999251fea909adc3c1e8694747c47e3f69b82 --output experiments/m194e-joint-pupil/independent-full-comparison-1 --cache-prefix experiments/m194e-joint-pupil/work/cache-independent-full-comparison-1
```

`python` resolved to
`C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe`,
Python3.12.10 MSC1943 AMD64. The child used that exact interpreter with
`-X utf8`, `-X pycache_prefix=` pointing to the absolute fresh
`work/cache-independent-full-comparison-1` directory, and the bound reader's
absolute path. The complete unabridged child argument vector is in the
invocation receipt; it does not rely on the older reader's `sys.argv` field
to reconstruct interpreter flags. NumPy2.4.4 and two numerical-library threads
are recorded. This short reader's runtime is not a producer or product
performance claim.

After reading the full result, the current bound schema's actual
`validate_commission(bundle_path, commission_path, trusted_hash)` accepted the
genuine emitted float gate using its external SHA above. The exact fresh-cache
validation invocation and schema/gate bindings are retained beside the result
in `independent-full-comparison-1-structural-gate.json`. This structural check
is supplemental to the independent numerical comparison, not its replacement.

A subsequent read-only console summary of producer arm metadata initially
indexed its arm dictionary as a list and raised KeyError(0). It occurred after
the successful child and structural gate validation, changed no artifact and
was not a scientific reader failure. No producer arm statistic was inferred
from that failed summary request.

## Authority and limits

The genuine `float-commission.json` is now available for the separately gated
CFA emission/conversion stage, with its external digest supplied to root and
the independent conversion verifier. It is float/model authority only: no CFA
conversion or production bridge pass is asserted here.

This commission covers the exact finite geometric two-plane, opaque half-plane,
uniform-disc pupil and sensor-cell model and its declared numerical fixture.
It does not validate diffraction, aberrations, measured sensor/noise calibration,
general natural scenes, real captures, the production merge, performance or
SOTA quality. The ideal pinhole latent and attainable finite-aperture captures
retain their distinct meanings. Earlier M25 physical/occlusion bars are not
redefined or silently passed by this new numerical model.
