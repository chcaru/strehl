# BUILD-RESAMP — the gather resampler, and what the band metric could not say

Instruments from the run that priced the two candidate causes of
`V-HEADTOHEAD`'s 0.20–0.40 cyc/px deficit. The report is
`docs/research/BUILD-RESAMP.md`; this directory is the machinery, kept so the
numbers can be re-derived rather than believed.

## What is here

| file | what it is |
|---|---|
| `../../crates/strehl-cli/examples/build-resamp-mtf.rs` | the isolated kernel MTF, measured **through `align.rs`'s own `Resampler::sample`** rather than a re-implementation, so it cannot drift from the shipping sampler |
| `band_ratio.py` | band-power ratio between two renders, green channel, with the flat-ROI control and the band-composition decomposition printed on every run |
| `commission.py` | commissions `band_ratio.py`: NULL, a σ=0.5 px Gaussian POTENCY arm scored against the Gaussian's own analytic MTF, and a SIGN arm |
| `spectrum.py` | the same transfer as a 0.01-wide curve instead of five wide bands — this is what made the merge plane's Nyquist visible |
| `render.ps1` | kernel A/B, four subjects × up to four kernels, one pinned binary |
| `render2.ps1` | byte-level commissioning of `--resampler`, plus the `STREHL_ALIGN=zoom` arms |
| `render3.ps1` | the `STREHL_COVER` A/B: the coverage enlargement priced against the identical render |
| `render4.ps1` | the 2×2 headroom grid — kernel and enlargement, separately and together |

## The one thing to know before reusing any of it

**`band_ratio.py` is not a resolution metric and must not be cited as one.** It is
band power. Band power rises under ringing, under aliasing and under noise
exactly as it rises under preserved detail. Measured on this corpus, it awards
`--resampler nearest` — the worst gather in the enum — **+29% at 0.20–0.30 and
+42% at 0.30–0.40** against the shipping Catmull-Rom, a margin larger than the
entire deficit it was built to investigate. Its flat-decile control fails on
every subject.

It is admissible as a *comparison between two kernels whose ringing is
separately bounded*, printed alongside its own controls. It is not admissible as
evidence that one render resolves more than another. For that, use a slanted
edge.

## The trap that would have voided the whole run

`merge_cmd.rs::alignment_for` — if `STREHL_WARPMAP` is set, **the sidecar's own
recorded resampler beats `--resampler`**, and the run says so on stderr. Every
driver here begins by removing that variable. AGENTS.md rule 45 now carries the
warning.

## `STREHL_COVER`

`align_cmd.rs` gained one measurement control: `STREHL_COVER=0` skips
`fit_to_cover` while keeping registration. It is **not a shipping option** — a
render made with it has edge pixels no frame covers, and it says so on stderr.
It exists because the enlargement and the per-frame warp fuse into one matrix
and are paid in one resample, so the only honest way to price the enlargement is
against the identical render with the identical solve from the identical binary.
It is deliberately absent from `SOLVE_ENV`, so both arms share one cached solve.

Commissioned: with `STREHL_ALIGN=0` there is no map to fit, so the switch must be
inert — and the two renders are byte-identical, SHA256 `8AC0AB71…3698`.

## Binaries these numbers came from

| SHA256 | what |
|---|---|
| `0DEBD94E0F26BE5720CE84EA32798ACB558DCFA536F08907A3F27C9331FABD1E` | `strehl.exe` at commit `a7017331`, the kernel A/B |
| `3B3B386DD3F45B7F823D53F1613D280BD8F7A5D494073EF490F4F732290B92E5` | the same plus `STREHL_COVER`, the enlargement A/B |
| `29E6E3F69A0C0E28404F4239FB34F4200174974A7AD8A0FB0B14F8EA6DDB5A20` | `build-resamp-mtf.exe` |

With `STREHL_COVER` unset the first two produce **byte-identical output** on all
four checked pairs, so comparisons spanning them are single-binary in effect.
