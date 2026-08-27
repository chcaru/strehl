# gate2veil.ps1 — RESULT

Binary `C:\dev\strehl-out\BUILD-BLEND\tgt-bandsep\release\examples\blend-render.exe`,
commit `8e531fd4`. `--gate 2 --base-mean --camera-linear`, `STREHL_FIX_CA=off`.
ctrl and the gate-4 arm are ORCH's own `clean6` renders, unmodified, so their
published numbers remain the middle column. All three arms scored in ONE
`veilpair.py` invocation, so the mask and distance transform are built once and
applied unchanged to every arm.

## (a) YES — the veil reduction survives at gate 2, essentially unchanged

Background luminance deficit vs far-field, ctrl / gate4 / gate2:

`flower-bud-alone-cpl`

| dist | ctrl | gate4 | gate2 |
|---|---:|---:|---:|
| 0..2 | -2269.6 | -2000.8 | -1993.1 |
| 8..16 | -1846.8 | -1151.0 | -1149.7 |
| 16..32 | -1866.1 | -981.3 | -977.9 |
| 64..128 | -1533.8 | -1199.4 | -1191.3 |

`dry-erase-marker-head-cpl`

| dist | ctrl | gate4 | gate2 |
|---|---:|---:|---:|
| 32..64 | -6966.5 | -2198.1 | -2453.7 |
| 64..128 | -3520.2 | -999.0 | -1022.1 |
| 128..200 | -2248.4 | -365.8 | -362.6 |

gate2 tracks gate4 to under 1% in every flower-bud bin and to 5-12% on
dry-erase's mid bins. Q2 confirmed, and for the reason registered before the
render: the gate sweep showed everything above 272 DN is gate-independent
across a 16x range, the veil is a low-frequency large-scale quantity, and it
duly lives in that gate-independent population.

**Consequence, which is ORCH's own stated one: the gate no longer has to
defend the veil. It can be chosen on detail/noise grounds alone.**

## A caveat that bounds the flower-bud half of the veil claim

`veilpair.py`'s placebo is commissioned on the REFERENCE arm -- it shows the
ctrl's own profile collapsing -2270 -> -458 when the mask is moved off the
silhouette. That establishes the ctrl's veil is edge-keyed. It does not
establish that the DIFFERENCE BETWEEN ARMS is edge-keyed, and the difference
is the quantity the claim rests on. Taking arm-to-arm differences in both
panels:

| subject / bin | real diff (ctrl-gate2) | placebo diff | placebo as % of real |
|---|---:|---:|---:|
| flower-bud 0..2 | 276.5 | **982.7** | **355%** |
| flower-bud 16..32 | 888.2 | **586.2** | **66%** |
| dry-erase 32..64 | 4768.4 | -487.5 | -10% |
| dry-erase 128..200 | 1885.8 | — | small |

On `dry-erase` the placebo difference is small and of OPPOSITE sign, so that
veil win is edge-keyed and solid. On `flower-bud` the two arms differ by MORE
at 640 px off the silhouette than they do on it at the closest bin. That is
the signature of a global low-frequency luminance difference between the
backends, not a silhouette-keyed veil reduction, and it means flower-bud's
0.53 ratio is substantially confounded.

This is the same class of error ORCH has been policing all night -- a control
that validates the reference's own property rather than the contrast being
claimed. Reported as a suggested fix to `veilpair.py` rather than worked
around: print the arm-to-arm difference in both panels and require the placebo
difference to be small before printing a veil verdict.

The strong claim therefore rests on `dry-erase`, where it is clean.

## The fallback fraction is strongly subject-dependent

`averaged` L0..L6 at gate 2:

| subject | L0 | L1 | L2 | L3 |
|---|---:|---:|---:|---:|
| tweezers (ORCH) | 29.0% | 0.1% | 0.0% | 0.0% |
| flower-bud | **49.1%** | 0.0% | 0.0% | 0.0% |
| dry-erase | **10.7%** | 2.3% | 1.9% | 1.5% |

The 47.9% everyone has been reasoning from is a tweezers-at-gate-4 number. At
one gate the fraction spans 10.7% to 49.1% across subjects, so notch severity
should vary with it and a single subject cannot calibrate the estimator.
Note also that at gate 2 flower-bud confines the fallback entirely to level 0
-- L1 and coarser are 0.0%.
