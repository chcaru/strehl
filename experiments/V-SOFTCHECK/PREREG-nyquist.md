# V-SOFTCHECK pre-registration: is the deficit a tuning deficit or a Nyquist deficit?

Written and committed BEFORE the measurement it describes. Timestamp is the
commit, not this line.

## The two worlds

`docs/research/BUILD-SHARP.md:4665-4669` asserts the merge runs on four CFA
planes at half the output dimensions, hence is band-limited to 0.25 cycles per
OUTPUT pixel. My headline band is 0.20-0.25 cyc/output-px, i.e. the top 20% of
that range, ending exactly at the asserted wall.

* **H_WALL.** Above 0.25 cyc/opx the merge has no information; below it the
  merge is unimpaired. The deficit is then roughly flat below 0.25 and
  collapses across it. No kernel, gate or weight can recover anything.
* **H_GATHER.** The loss is the gather's resampling attenuation, which is
  smooth, begins well below 0.25, and is bounded by the kernel's MTF. It is
  recoverable in proportion to how much better a kernel can be.

These predict DIFFERENT SHAPES and I commit to the shape before I look.

## The discriminator, fixed in advance

Let D(f) be the charged deficit in a narrow band centred at f, on the shipping
grid (7032x4688, 1 output px = 1 photosite). Measure D on 0.02-wide bands from
0.10 to 0.40 cyc/opx.

Define D_drop = D(0.11) - D(0.39), the total decline, and W = D(0.23) - D(0.27),
the decline across the 0.04-wide window straddling the asserted wall.

* **CLIFF (H_WALL) if W / D_drop > 0.40.** The window is 4/28 = 14.3% of the
  swept range, so uniform decline contributes 14.3%. A wall must dominate.
* **SMOOTH (H_GATHER) if W / D_drop < 0.20.**
* Between 0.20 and 0.40 is declared AMBIGUOUS and I will say so rather than
  round toward whichever hypothesis is tidier.

## The independent quantitative prediction

The shipping code contains `strehl-core/src/restore.rs::gather_mtf`, the
phase-averaged MTF of one gather, in cycles per PLANE sample. Its own tests pin
Catmull-Rom at 0.25 -> 0.94024, 0.35 -> 0.82113, 0.40 -> 0.74255,
0.50 -> 0.62500, and `lanczos3_is_not_meaningfully_sharper` asserts
Lanczos-3 / Catmull-Rom < 1.15 everywhere up to plane Nyquist.

One plane sample is two output pixels, so f_plane = 2 * f_out. My statistic is
band POWER, so the predicted deficit for a site elected from a gathered frame is

    D_pred(f_out) = gather_mtf(CatmullRom, 2 * f_out) ** 2

I will RE-IMPLEMENT `gather_mtf` in Python from the kernel definitions only,
and validate it against those four pinned values before using it. Reading a
kernel definition is reading a definition; I am not importing a result.

* **H_GATHER is corroborated** if the measured D(f) tracks the SHAPE of
  D_pred(f) across 0.10-0.25, i.e. if D(f)/D(0.11) and D_pred(f)/D_pred(0.11)
  agree in trend and the measured curve lies at or above D_pred (at or above
  because the shipping `restore` Wiener filter exists to undo part of it, and
  because sites elected from the reference frame are gathered by identity).
* **H_GATHER is refuted** if the measured deficit is flat where D_pred falls.

## What would make me report CANNOT DECIDE

If my single-frame reference is itself gathered rather than identity-warped,
the numerator and denominator share the attenuation and the ratio cannot see
it. I established earlier that `STREHL_ONLY_FRAME=k` truncates the path list
before alignment so the frame aligns to itself, but I will re-verify it here
rather than inherit it, because this measurement's whole meaning depends on it.

## Ceiling on any fix, stated in advance

If H_GATHER holds, the best available kernel change buys at most 1.15x in
amplitude and therefore at most 1.32x in power, by the shipping code's own
assertion. I commit in advance to reporting that ceiling whichever way the
shape comes out, because "tunable" and "worth tuning" are different claims.
