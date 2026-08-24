# M82 — pre-registration amendment: renamed bee capture and bee triple

**Frozen before M82 decodes any frame from `bee-1-cpl`, `bee-2-cpl`, or
`bee-3-cpl` in this amendment.** This document does not alter
`PREREGISTRATION.md`, its original five-stack bar, its wrapped-text sibling
bar, or the result already committed from those tests. It adds a current-path
reproduction and a separately reported bee-triple arm.

## B0. Why this amendment exists, and what was already visible

**MEASURED path audit, metadata only.** On 2026-08-23, the required directories
and filename-sorted ARW counts are:

| logical stack | current directory | exists | ARWs |
| --- | --- | --- | ---: |
| `wrapped-text-1` | `D:\personal\macro\wrapped-text-1` | yes | 130 |
| `wrapped-text-2` | `D:\personal\macro\wrapped-text-2` | yes | 120 |
| `109MSDCF` | `D:\personal\macro\109MSDCF` | yes | 22 |
| `coffee-bean` | `D:\personal\macro\coffee-bean` | yes | 105 |
| `foam` | `D:\personal\macro\foam` | yes | 100 |
| M77 `bee-1` | `D:\personal\macro\bee-1` | **no** | 0 |
| M77 `bee-1` | `D:\personal\macro\bee-1-cpl` | yes | 299 |
| `bee-2` | `D:\personal\macro\bee-2-cpl` | yes | 299 |
| `bee-3` | `D:\personal\macro\bee-3-cpl` | yes | 299 |

**MEASURED correction to the amendment brief.** The bee triple is not
unmeasured in the committed corpus. M70 commit `d882b0c`, made before this
amendment, includes `bee-1`, `bee-2`, and `bee-3` in its fresh through-focus
spectral measurement. `out/s10_architecture.log` reports the exact
equal-average window ladder requested here. M70 also reports all three as 299
frames at marked f/5.6; its source census records ISO 100, 400, and 100
respectively. The pointer that nobody had measured their through-focus
behaviour is therefore false at source.

**MEASURED, pre-existing and not blind.** M70's committed equal-average values,
each referenced to its own ±1 average, are:

| stack | ±1 | ±2 | ±3 | ±5 | ±10 | ±20 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `bee-1` | 1.0000 | 1.1823 | 1.2909 | 1.3720 | 1.5058 | 1.3813 |
| `bee-2` | 1.0000 | 1.1815 | 1.3024 | 1.4442 | 1.6709 | 1.7580 |
| `bee-3` | 1.0000 | 1.2070 | 1.3385 | 1.4355 | 1.5648 | 1.6369 |

**MEASURED path-identity limit.** The 299 filenames stored inside each of
M70's committed `tfs-bee-*.npz` files exactly match the 299 filenames now in
the corresponding `*-cpl` directory, including first `DSC00001.ARW` and last
`DSC00299.ARW`. M70 did not store RAW byte hashes, so filename identity is not
byte identity. A fresh current-path recomputation remains required.

**MEASURED historical-run audit.** M82 did not silently skip M77 `bee-1`
before the rename. Its ladder, confirmation, and sharpness logs ran from
2026-08-24T05:40:07Z through 05:59:12Z, each records 299 frames and exit 0,
and all four aggregate JSON files contain the stack. The result is complete,
not partial. It is nevertheless re-run from `bee-1-cpl` so the current
reproduction path is real rather than documentary.

## B1. Current-path identity and physical-comparability arm

**ARGUED method.** Re-run M70's source method on the three current directories,
without modifying M70's files:

1. use M70's exact 24 fixed green-quincunx patch centres;
2. use 256-sample patches, 128-sample periodic-Hann Welch tiles, 50% overlap,
   and M70's six sensor-frequency bands;
3. subtract the shipped photon-transfer variance at the matching
   squared-window-weighted patch level;
4. classify texture by M70's low-band
   `max signal / median model variance >= 10`;
5. in each textured patch and each of M70's three mid bands, locate the
   `[1,2,1]/4`-smoothed peak and compute the equal-average response in windows
   ±1, ±2, ±3, ±5, ±10, and ±20; and
6. take the median over textured patches, then the mean over the three bands,
   exactly as `s10_architecture.py`.

**ARGUED identity control.** For each stack and rung, the current-path result
must reproduce M70's committed value within 0.1% relative. Failure makes that
renamed directory's identity with M70's measured capture **NOT ESTABLISHED**.
This is a consistency check against pre-existing evidence, not independent
evidence for the method.

**ARGUED P34-equivalence rule.** To receive the same physical-control status as
the wrapped-text pair, all three bees must:

1. have at least 16 M70-qualified textured patches;
2. select the same maximum rung over ±1, ±2, ±3, ±5, and ±10; and
3. have `max(response)/min(response) <= 1.05` at every one of those rungs.

The 1.05 line is the rounded form of M70 P34's measured 4.7% wrapped-text
agreement. The ±20 rung is reported but does not decide this gate because
M70's own uncertainty analysis marks it unstable. Because M70's values above
were visible before this amendment, this is an interpretation rule frozen
before the current-path rerun, not a blinded discovery claim.

**ARGUED consequence.** If the physical rule fails, the triple's gate and
price results remain mandatory and descriptive, but neither agreement nor
disagreement may pass or refute the portable-price hypothesis. If it passes,
the bee triple becomes a second conditional sibling control.

## B2. Outcome-normalised bee-triple arm

**ARGUED stack identities.** Use logical IDs `bee-1`, `bee-2`, and `bee-3`
with physical directories `bee-1-cpl`, `bee-2-cpl`, and `bee-3-cpl`. Frame
counts are 299. ISO values are 100, 400, and 100, taken from M70's all-frame
EXIF census and required to reproduce in the fresh CLI headers.

**ARGUED ROIs.** Transfer M82's frozen `bee-1` sensor coordinates unchanged to
all three captures:

| role | 256² M77/M80 ROI | 512² M57 ROI |
| --- | --- | --- |
| flat | `2720,1568,256,256` | `2592,1440,512,512` |
| detail | `1952,672,256,256` | `1824,544,512,512` |

This is a coordinate transfer, not a post-view semantic match. There is no
replacement if a transferred cell is untextured, contaminated, pinned, or
otherwise unreadable.

**ARGUED solve and confirmation.** Use the original 15-rung gate ladder,
requests 0.90, 0.70, and 0.50, log-gate/log-gain interpolation, no
extrapolation, and ±0.005 confirmation rule. The original two-update limit
applies independently to every new target.

**ARGUED price and controls.** Use the original M57 `dsig` contrast, 0.343 px
null bound, 3.09 jackknife correction, corrected-z threshold 2, pin veto,
Python-versus-Rust 1% raw-RMS check, all-frame M77 flat precondition, M80
abstention, curve control, and singleton reporting without alteration.

**ARGUED bee-triple bar B.** At primary request 0.70, if and only if B1's
physical rule passes, all three prices must be readable and positive and
`max(C)/min(C) <= 1.50`. An excess or readable sign reversal refutes
portability on this conditional control. Any unreadable price returns
`NOT ESTABLISHED`.

**ARGUED independence of the original decision.** The original five-M77-stack
bar F and wrapped-text bar S stand exactly as committed. Bee bar B cannot
rescue either. A failure of B cannot overrule them unless B1 first establishes
physical comparability.

## B3. Provenance, mutation and reporting

**ARGUED binary.** Reuse M82's frozen release binary only if its SHA-256 remains
`2f1ea8904240acca98937f4755354302b53a061c8791d677b721137e45c58a74`
and `crates/strehl-core/src`, `crates/strehl-cli/src`, and `Cargo.lock` remain
unchanged from binary commit
`79468b971bbf3e7657c86def2ea1b0ddbef78c99`. Otherwise rebuild privately and
record new provenance.

**ARGUED mutation control.** Any change to the shared Python admission helper
requires the original byte-level reversed-comparison control to be re-run,
with planted read-back, nonzero self-test exit, and exact restoration.

**ARGUED reporting.** Report separately:

1. the old-path audit and current-path `bee-1-cpl` reproduction;
2. the source correction that M70 had already measured the bee triple;
3. the fresh physical-comparability result and whether B1 permits inference;
4. the three raw solved gates and confirmed gains at every request;
5. every primary and curve price, including abstentions;
6. all flat-control, pin, M80, local-admission, and singleton diagnostics; and
7. the original M82 verdict unchanged beside the conditional bee result.
