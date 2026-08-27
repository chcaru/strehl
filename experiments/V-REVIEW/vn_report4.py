import io
P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-REVIEW-noise-verification.md"
T = """

## 14. Do the four cells hold on the SHIP-V4 pin?

**Verdict: HOLD.** All six per-channel ratios are unchanged and all six remain
clear of parity. The scope line can be struck. The reason is stronger than the
verdict: **the pin question turned out to be empty, and it took a measurement to
find that out.**

The decision rule was written and committed as `e358bd3c` before any SHIP-V4
render existed. Its threshold was the published interval, on the six
per-channel ratios rather than the four rounded cells, because a rounded cell
hides movement.

### What was rendered

Pin verified by hash before use, never by path or size, since four builds on
this machine share size 9,568,768:

    44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490

which equals the SHIP-V4 corpus seal. The strehl A/B half-stack pair for
subject 113 was re-rendered with the switch state copied verbatim from the Rule
47 block of `experiments/V-HEADTOHEAD2/render_linear.ps1` -- `stack --merge
pyramid --pyramid-gate 4.5 --linear-srgb --demosaic`, `STREHL_FULLRES_GATHER=1`,
the pinned per-half warpmap, eleven variables cleared by name, and a check that
no other `STREHL_*` was set in the calling process. Comparator outputs and the
tile census were held fixed. Both renders were sealed at render time.

### The commissioning gate fired

The pre-registration required the SHIP-V4 render to **differ** from the SHIP-V3
arm, because rendering with the wrong binary produces exactly the "no change"
answer a real null produces. MEASURED:

| half | SHIP-V3 pin | SHIP-V4 pin | differ |
|---|---|---|---|
| `113-A-g1` | `F6810573765972E9...` | `F6810573765972E9...` | **no** |
| `113-B-g1` | `41DA8F97C2BD7B0F...` | `41DA8F97C2BD7B0F...` | **no** |

Byte-identical. By the rule I had already committed, that is a red flag to
diagnose rather than a clean null, and it had to be established positively by a
route other than my own run. Two routes were used.

**Route one, is my harness inert?** A responsiveness control: same pin, same
command, one environment variable changed to `STREHL_FULLRES_GATHER=0`.
MEASURED, the output hash becomes `DACB36FB1141AD86...` -- completely different.
The harness genuinely invokes the binary and its output responds to input state.

**Route two, the source.** MEASURED, `git diff 740e7056 9b05d0b7` touches 99
files, of which seven are under `crates/`. Four are `examples/*.rs`, which
compile to separate binaries and cannot reach `strehl.exe`. The diffs to
`strehl-core/src/photometric.rs` and `strehl-core/src/highlight.rs` are **doc
comments and one test rename** with no executable change; `DEFAULT_KNEE` stays
`0.60`. That leaves `crates/strehl-cli/src/image_out.rs`, whose only behavioural
change is one match arm:

| condition | `740e7056` | `9b05d0b7` |
|---|---|---|
| matrix, `--srgb` | sRGB profile | sRGB profile |
| matrix, linear, **no tone** | linear-sRGB profile | linear-sRGB profile |
| matrix, linear, **with tone** | linear-sRGB profile | **none** |

The changed arm requires a linear render that also carries a tone curve. This
measurement path is `--linear-srgb` with no `--exposure` and no
`--auto-exposure`, so it has no tone and takes the unchanged arm. **The two
binaries are required to agree here, and they do.**

### The cells

MEASURED, same gauge, same code, same 2000-resample bootstrap:

| comparator | channel | SHIP-V3 published | SHIP-V4 | SHIP-V4 interval | clear |
|---|---|---:|---:|---|---|
| `enfuse` | luma | 1.618 | 1.618 | 1.511 to 1.709 | yes |
| `enfuse` | B-Y | 1.606 | 1.606 | 1.525 to 1.702 | yes |
| `enfuse` | R-Y | 1.813 | 1.813 | 1.717 to 1.966 | yes |
| `focus-stack` | luma | 1.475 | 1.475 | 1.400 to 1.514 | yes |
| `focus-stack` | B-Y | 1.640 | 1.640 | 1.550 to 1.710 | yes |
| `focus-stack` | R-Y | 1.661 | 1.661 | 1.592 to 1.755 | yes |

Six points inside their published intervals, six intervals clear of parity, six
rounded cells unchanged. **HOLD** on the pre-registered rule.

**These six numbers are not independent evidence and should not be read as
such.** The inputs are byte-identical, so identical statistics follow by
construction. Running the estimator confirms no file was mixed up; it confirms
nothing about the pipeline. The residual deltas, all below 0.0005, are the
rounding of the published three-decimal values and not movement.

### The finding that outranks the verdict

If the two pins agree on this path, do they agree on the delivered images?
MEASURED, hashing every master in both corpora:

**All 26 subjects are byte-identical between SHIP-V3 and SHIP-V4.** Identical
26, differing 0, missing 0, summing to the 26 subjects present. The seals name
different binaries -- `15EA7346...` against `44C2F2CD...` -- over the same
pixels.

So the two shipping corpora are **one set of images rendered by two builds that
agree**, not two generations of output. The distinction is a labelling
distinction on these files. That retires the scope concern completely rather
than narrowly: any measurement on either corpus applies to both, which also
means the print-readiness adjudication done on SHIP-V3 and the aura work done on
SHIP-V4 were always on the same pixels.

This does **not** say the binaries are equivalent in general. They provably
differ on linear-plus-tone renders. It says they agree on every path either
corpus exercises, and that was worth measuring rather than assuming in either
direction.

### Cleanup

The three renders made here are byte-identical duplicates of files already on
disk, or a control whose result is its hash, so the `.tiff` artifacts were
removed after measurement and their `.ok` and `.provenance.txt` records kept.
Nothing is lost: the exact bytes of the measurement arms remain at
`C:\\dev\\strehl-out\\V-H2H2\\lin\\`, and each render reproduces in under 40
seconds from the sealed provenance.
"""
io.open(P, "a", encoding="utf-8", newline="\n").write(T)
print("appended")
