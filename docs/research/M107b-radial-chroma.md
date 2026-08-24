# M107b R-series — D2 vs a single-frame control cannot validate a chroma fix

Response to ORCH's edge-chroma measurement. Bars R1–R4 registered at `4be0a6f`
and R5 at the commit below, both **before** the numbers existed.

**Headline: I reproduced your four numbers exactly, then found the render/control
comparison is confounded by sharpness, and in the process withdrew a finding of my
own.**

---

## 1. R4 — the instruments agree

| scene | arm | yours | mine | delta |
|---|---|---|---|---|
| `lavendar` | strehl HEAD | 4.22x | 4.22x | 0.004 |
| `lavendar` | single-frame | 1.36x | 1.36x | 0.004 |
| `marker` | strehl HEAD | 2.65x | 2.65x | 0.003 |
| `marker` | single-frame | 2.23x | 2.23x | 0.003 |

Everything below is measured on the same footing as your D2.

## 2. The confound: the two arms do not select the same pixels

D2 takes the **top 1% of gradient in each image separately**. The render is a
focus stack; the control is one frame of a bracket, so most of its scene is
defocused. Their gradient distributions are nowhere near each other:

| scene | control p99 gradient | render p99 gradient | ratio |
|---|---|---|---|
| `lavendar` | 0.006619 | 0.049835 | **7.53x** |
| `marker` | 0.012307 | 0.058963 | **4.79x** |

So "the top 1% of edges" means something **7.5x stronger** in the render than in
the control. Applying the control's threshold to both, the inner annulus of
`lavendar` contains **934 164** qualifying render pixels against **16 018** in the
control — the render has ~58x more genuine edge content at the same absolute
gradient.

**A single frame of a focus bracket is not a control for chroma. It is mostly
out of focus, and defocus is a lowpass that suppresses edge chroma directly.**
Much of the 1.36x is "this frame has few in-focus edges", not "this scene has
little edge chroma".

## 3. What happens when you compare like with like

Chroma produced by a channel displacement `d` across an edge of gradient `g` goes
as `d*g`, so `chroma/grad` is a displacement estimate and is the contrast-free
quantity. With a **common absolute threshold** and that normalisation:

`lavendar`, excess = render / control, by radius:

| annulus | n_render | n_control | excess |
|---|---|---|---|
| 0.00-0.17r | 934 164 | 16 018 | **0.90** |
| 0.17-0.33r | 3 112 632 | 61 005 | **1.08** |
| 0.33-0.50r | 2 890 181 | 149 817 | **1.05** |
| 0.50-0.67r | 762 670 | 48 613 | 1.56 |

`marker`: **0.64, 0.85, 0.67, 0.87** across its four dense annuli — the render is
*better* than the control per unit edge contrast in every one.

**The 4.22x-against-1.36x gap largely collapses to ~1.0 once contrast is matched.**
It does not vanish entirely, and the outer `lavendar` annuli stay elevated, but
the headline 3.1x is not a 3.1x chroma defect.

Standing caveat, which is yours and I am not weakening it: the control is
LibRaw-developed, so demosaic differences sit inside every comparison here too.
This bounds the effect; it does not isolate a mechanism.

## 4. A finding of mine, made and then withdrawn

R1 found the excess **rising** with radius (`lavendar` 1.35 -> 5.68, outer/inner
4.21). Under the per-image threshold that looked like a radius-dependent term
being added by the pipeline — a geometry result, and a new one.

**It was a selection artefact and I killed it with R5.** As radius grows, fewer
render edges clear a global cut, so the survivors are increasingly the
highest-contrast ones, which carry more chroma. Under the common threshold:

| scene | R5a unnormalised | R5a gradient-normalised |
|---|---|---|
| `lavendar` | 1.193 **FLAT** | 1.200 **FLAT** |
| `marker` | 1.165 **FLAT** | 1.351 UNRESOLVED |

**R1's rising-excess finding is withdrawn.** The withdrawal branch was registered
before the run, not written afterwards.

## 5. R1/R3 — this metric is blind to lateral CA

Lateral CA acts only where there is an edge to displace, so it must make **edges**
rise with radius while **flat** regions stay put. Measured on the control:

| scene | edge trend | flat trend | edge-over-flat |
|---|---|---|---|
| `lavendar` | 0.311 | 0.317 | **0.981** |
| `marker` | 1.469 | 2.118 | 0.693 |

`lavendar`'s edges and flats fall together at within 2% of the same rate. **The
radial structure D2 sees is whole-image colour shading, not CA.** R3 was
registered precisely to be able to kill R1 this way, and it did.

## 6. Consequences for the two-sided validation plan

1. **D2-against-a-single-frame cannot validate M107b's lateral correction.**
   Lateral CA is an optical property present in a single frame **at full
   strength**, so it appears in both arms and largely cancels. A correct lateral
   fix would push the render *below* an uncorrected control and score as
   over-correction.
2. **The plan is gameable in the wrong direction.** "Move `lavendar` toward its
   1.36x control" is achievable by **blurring**, since the control's low ratio is
   substantially defocus. Any fix that lowpasses would score as a win.
3. **`marker` is not a clean "leave it alone" arm — it is an arm with no data.**
   Beyond 0.67r its control contains **zero** qualifying edge pixels, and beyond
   0.83r the render has 1 926. The 1.19x global excess is diluted by an absence of
   coverage where a radial defect would be largest, not by an absence of defect.
4. **What would work instead**: measure the geometry directly rather than through
   a contrast-dependent colour statistic. `e2_lateral` measures per-channel edge
   displacement in plane px on unresampled CFA data, which is contrast-free and
   scene-independent by construction. That is the instrument that scored L3/L4.

## 7. What I could not determine

- Whether any real chroma excess survives full matching. The residual after
  contrast-matching is small, non-zero and confounded by the LibRaw/Malvar
  demosaic difference. **Bounding it needs a same-demosaic control**, e.g. a
  strehl render of a single frame, which I did not build.
- `marker`'s gradient-normalised 1.351 sits in the band I registered as
  unresolved, and I am leaving it there.
- Nothing here measures the axial term. It is radius-independent (M107b A1:
  `R^2 <= 0.037` vs radius on 3/3 stacks), so a radial statistic is the wrong
  instrument for it either way.
