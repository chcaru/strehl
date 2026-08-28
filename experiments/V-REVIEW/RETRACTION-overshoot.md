# Retraction: the +8.2707% overshoot was measured on a 70%-saturated render

MEASURED by `audit_clipcheck.py` against a binary built from the shared tree at
HEAD `3a312ba6` (only `bca05c93` landed during the 4m11s build and it touches
none of `image_out.rs`, `merge_cmd.rs`, `stack.rs`, `pyramid.rs`, so the binary
is materially `3a312ba6` on the exposure path). Subject `109MSDCF`, `--limit 4`,
`--srgb --merge pyramid`.

| arm | flags | % clipped | median | % above 90% of ceiling |
| --- | --- | --- | --- | --- |
| noauto | (none) | 0.0007 | 61122 | 53.60 |
| e0 | `--exposure 0` | 0.0007 | 61122 | 53.60 |
| **e1** | `--exposure 1` | **70.1609** | **65535** | **73.62** |
| em1 | `--exposure -1` | 0.0001 | 45341 | 0.00 |
| auto | `--auto-exposure` | 0.0007 | 61122 | 53.60 |

## 1. I am in ORCH's arm 3, and I can prove it

No V-REVIEW render ever passed `--auto-exposure`. `audit_pairs.py:9`,
`audit_head_exposure.py`, `audit_linear_gain.py`, `audit_overshoot.py` and
`audit_anchors.py` all render `--limit 4 --srgb --merge pyramid`;
`audit_potency.py` uses `COMMON=["--limit","4","--srgb"]`. `AUDIT-potency.md`
contains **zero** occurrences of `auto-exposure` against a control of 10 for
`exposure`, so that absence is measured rather than mis-grepped. The
`--auto-exposure` potency row in `AUDIT-user-surface.md` was taken on the
**pin**, which has no regression.

## 2. Arm 3 did not save the overshoot number, and I am withdrawing it

**The bright endpoint of that measurement, `--exposure 1`, is 70.16% clipped
with its median pinned at 65535.** My mask excluded exactly-clipped samples
(`audit_pairs.py:36`), but 73.62% of the frame sits above 90% of the ceiling,
so the survivors are the compressed shoulder, not linear signal. ORCH's
metrological point applies to my own number: a saturated region has no
structure, and I measured a slope across one.

**WITHDRAWN:** `+8.2707%` as a delivered-gain error. It is an artefact of
regressing onto a saturated endpoint.

**SURVIVES**, because both endpoints are unsaturated (0.0001% and 0.0007%):

- `-2 -> -1` and `-1 -> 0` deliver the commanded 2.0 **exact to seven
  decimals**. The exposure fix works; that verdict is unchanged.
- `+1.37%`, the residual restricted to samples below half ceiling, is the
  defensible highlight figure.

**SHARPENED, and this closes my open gap.** I reported that the error attached
to the brighter render rather than the commanded ratio -- identical +8.2707%
across commanded 2x, 4x and 8x -- and recorded the responsible stage as not
isolated. **There is no stage.** All three pairs shared one 70%-saturated
endpoint, which is why one number appeared three times. My instrument was
reading saturation.

## 3. Independent verification of ORCH's fix, which the author may not certify

`5f367a94` ("stop `--auto-exposure` double-normalising the srgb render") is in
my build. ORCH reported the regression at 92.03% clipped / median 65535 and was
still commissioning the fix. **MEASURED: `--auto-exposure` is now byte-for-byte
in the same place as no flag at all** -- 0.0007% clipped, median 61122, 53.60%
above 90% ceiling, identical on all three statistics. The regression does not
reproduce at `3a312ba6`. The new banner states
`--auto-exposure is SUPERSEDED and applies NOTHING`, which is the tone-rule
cancellation V-REVIEW originally measured, now said out loud by the tool.

## 4. A product observation this turned up

At `--exposure 0` the median already sits at **61122 of 65535 (93.3% of full
scale)** and 53.60% of pixels are above 90% of the ceiling, because the tone
stage anchors p99.9 to 0.90. **Any positive `--exposure` therefore saturates**:
`+1` clips 70.16% of the frame. The tool prints no warning. This is the tone
anchor's doing, not the gain's, and it is a usability defect rather than a false
statement -- but a user who passes `--exposure 1` gets a white sheet and is told
nothing. *Severity MEDIUM.* Not mine to fix; `merge_cmd.rs` is owned.
