import io, os
DOC = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-REVIEW-merge-rim.md"
T = """# V-REVIEW-merge-rim: does the merge itself put a rim at subject edges?

**VERDICT: UNMEASURABLE-ON-THIS-CORPUS.**

Four routes were attempted. Three were refused by regime for a stated, measured
reason. The one that seated returned a null that its own control shows it could
not have detected the effect with.

**The exact sentence that is safe to say:**

> We have not measured whether the merge adds a rim of its own. Four routes were
> tried and each was refused for a measured reason; the one statistic that did
> seat scored the shipping kernel at 0.49x the floor set by a kernel that
> physically cannot ring, so it was not capable of isolating the effect. The
> merge's rim content is unmeasured, and no claim about it in either direction
> is currently supported.

This closes nothing. It converts an open question that looked answerable into an
open question with a known cost to answer, listed in section 5.

## 1. Partition

Every attempt is accounted for. `measured` counts a route that produced a number
its own controls license; `refused-by-regime` counts a route whose preconditions
were tested and found absent; `failed` counts a route that errored.

| route | subject | outcome | binding reason |
|---|---|---|---|
| A frame envelope via sidecar warp | coffee-bubbles | refused-by-regime | warp convention not decodable to required precision |
| B frame envelope via native registration | coffee-bubbles | refused-by-regime | frames not co-registered; photometric spaces differ |
| C gather-kernel isolation | coffee-bubbles | measured, NULL | statistic dominated by a sharpness term |
| D full-resolution edge plateau | lead-1-cpl | refused-by-regime | no macro edge has flat plateaus |

**measured 1 / refused-by-regime 3 / failed 0 = 4 routes.** A refusal is not a
clean result and must not be read as one. Route C is counted as measured and its
number is a null, which is not the same as an acquittal.

## 2. Route A -- the warp sidecar

`strehl align` writes a documented sidecar: per-frame complex similarity, the
header states `reference -> frame`, plane coordinates, and the resampler. On
coffee-bubbles it placed 19 of 19 frames, total corner drift **34.318 plane px**,
cycle-consistency floor **0.333 plane px**, and `held-out corner error: NOT
MEASURED (too few edges)`.

I could not reproduce the transform. Five conventions were tested against
adjacent and distant frame pairs at four image corners, which is where a scale
change actually displaces pixels:

| convention | mean residual px | worst px |
|---|---|---|
| none (unwarped) | 16.126 | 28.792 |
| `a*z+b` as given | 19.706 | 31.618 |
| `(z-b)/a` | 58.596 | 230.906 |
| `a*(z-c)+b+c` | **7.634** | 45.195 |
| `(z-c-b)/a+c` | 88.224 | 489.871 |

The best convention halves the unwarped error and is still **23x** the
alignment's own 0.333 px floor. A warp wrong by several pixels puts a false rim
on every edge in the image, which is the one failure this work exists to avoid,
so the route was abandoned rather than tuned.

**A centre crop cannot discriminate any of these**, and my first attempt used
one. Focus breathing is a scale change, so it displaces nothing at its own
centre; the declared 34 px is *corner* drift. Measured at the centre, the
unwarped stack looked registered to 0.464 px and every convention looked
plausible.

## 3. Route B -- native registration, and the denominator that was not in the same space

If the frames were natively co-registered near the scale centre, no warp would be
needed. Three sampled pairs suggested they were, at half-size 512 px. Checking
**all** 19 frames against the reference instead of three gave a worst case of
**3.953 px** at frame 16. The three-pair sample was a lucky draw.

The route fails for a second and independent reason. Median level in the same
region, 16-bit linear:

| quantity | value |
|---|---|
| frame medians, range over 19 frames | 1114 to 1261 |
| spread | 12.53% |
| master median | **1034** |

**The master sits below every single frame it was built from.** An envelope of
per-pixel frame min and max is only a bound if numerator and denominator share a
photometric space, and these do not. Building it anyway would have produced a
confident number with no meaning.

## 4. Route C -- the gather kernel, and the control that refuted my own reading

The registration gathers each frame through an interpolator whose **shipping
default is catmull-rom, a kernel with negative lobes**. `nearest` and `bilinear`
have none. All arms share alignment, photometry, merge and raster, so those terms
cancel and any difference is the kernel.

**The arms had to be commissioned before they could be compared.** Passing
`--resampler` to `align` produced four sidecars but four **byte-identical**
renders, all reporting `resampler: CatmullRom`, because `stack` looks up the
sidecar keyed to its own default. Passing the flag to `stack` gave four distinct
hashes, with the catmull-rom arm reproducing the default render exactly.

Statistic: excess of an arm over the local range of the bilinear arm, radius 2 px.

| arm | negative lobes | max DN | p99.99 DN | vs floor |
|---|---|---|---|---|
| bilinear vs itself | -- | **0.0** | 0.0 | identity control |
| nearest | no | 21006.0 | **3655.0** | 1.00 (the floor) |
| catmull-rom (shipping) | yes | 9262.0 | 1797.0 | **0.49x** |
| lanczos3 | yes | 12360.0 | 2378.0 | 0.65x |

**Both negative-lobe kernels score BELOW the kernel that cannot ring at all.**
The statistic is measuring aliasing and sharpness, not ringing, and it is not
capable of answering the question.

Read without the `nearest` control, the same table says catmull-rom exceeds
bilinear by up to 9262 DN on 10.0% of pixels, and I would have reported a
conviction. Every arm I built first perturbed the numerator; the arm that
refuted the reading perturbed the reference.

## 5. What it would cost to answer

- The sidecar's coordinate convention, from the source rather than by guessing.
  With it, route A becomes a bounded job, since a bilinear gather cannot inject
  overshoot and residual misregistration can be absorbed conservatively by
  dilating the envelope.
- A way to render a single frame in the **same** photometric space as the
  multi-frame master, which route B needs and does not have.
- A ringing statistic that is not confounded by sharpness. The excess-over-local-
  range form works against a *reduction*, where the input is available as the
  bound; between two merges it has no such anchor.

## 6. Errors I made

- I tested the warp convention at the image centre, where a scale change is
  invisible by construction, and briefly believed a wrong convention.
- I sampled three frame pairs and concluded the stack was co-registered; all 19
  showed 3.953 px.
- I ran four resampler arms that were byte-identical and would have reported
  "no kernel difference" had I not hashed them first.
"""
os.makedirs(os.path.dirname(DOC), exist_ok=True)
with io.open(DOC, "w", encoding="utf-8", newline="\n") as f:
    f.write(T)
print("wrote", len(T), "chars")
