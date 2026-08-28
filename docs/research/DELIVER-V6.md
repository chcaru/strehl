# DELIVER-V6: the corpus re-rendered on the re-fit CA coefficient

**Verdict: the fix is real, it is visible, and nothing regressed.** On the 14
subjects where the measurement can actually see chromatic fringing, edge colour
error fell on **14 of 14** — median **-17.0 %**, best **-35.3 %**, worst
**-0.4 %**. I looked at all 26 subjects myself and the magenta the owner
objected to is gone from the subjects it was diagnosed on.

**The masters are also print files, verified in their own bytes.** All 26 carry
the 2716-byte sRGB ICC profile in tag 34675, `300/1` X and Y resolution, and
`ResolutionUnit = inch`. The reader was commissioned against a file known to
lack them before any master was trusted. **A correction to the brief that sent
me looking:** the profile-less gallery BUILD-OUTPUT found is `SHIP-V2`, not
ORCH-FAITHFUL — ORCH-FAITHFUL was built after both ICC commits and already had
the profile, so commissioning against it, as instructed, would have failed (§11).

**Two things happened in my delivery folder that I did not do**, both since
explained: ORCH purged the superseded ORCH-FAITHFUL tree at 02:53 after banking
its hashes eleven seconds earlier, and ORCH rendered seven further subjects into
my masters folder with my pinned binary. Neither is data loss; both change how
the folder should be read (§13).

**Three things in this report are more important than that headline**, because
each one contradicts something the lane was briefed to expect:

1. **The build-drift confound does not exist on this path.** I rendered a
   second arm from the same pinned commit with only `eps_r` reverted, and it
   reproduces the shipped ORCH-FAITHFUL masters **pixel-for-pixel on all 5
   subjects tested**. The six `crates/` commits between the old masters' build
   and my
   pin, and that build's `-dirty` state, changed the output by **zero pixels**.
   The old-vs-new comparison is therefore a clean coefficient-only A/B, not a
   confounded one.
2. **`highly-angled-ruler-mm-cpl` receives no CA correction at all** — under
   either coefficient — and is pixel-identical between arms. It is a tilted
   subject, its alignment is refused, and an unregistered merge does not
   resample, so the correction (which rides the alignment gather) never runs.
   It could not have got worse. It also cannot get better, and it still visibly
   carries lateral CA at 1:1.
3. **The coefficient moves green**, which it should not be able to do directly.
   `eps(Green)` is `None` by construction, yet green moves on 29.4 M pixels
   between the two one-build arms. The mechanism is frame selection, not
   resampling.

**Binary under test:** `strehl 0.0.0 (6af834dac08d)`, sha256
`2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7`,
9 859 584 bytes. **Control binary:** same commit, `eps_r` reverted to
`-704.5e-6`, sha256
`9DC2F85A99E033E3AE4217EF4FD7923A4836A727AEA562D9B993F3FE0D2F00F1`. Both
re-hashed after the last render and unchanged.

**Invocation:** `strehl.exe stack <dir> -o <out>.tiff --srgb`. Nothing else.
All `STREHL_*` cleared except `STREHL_CACHE_DIR`. **Outputs:**
`C:\dev\strehl-out\DELIVER-V6\masters\` (26 masters, 4.79 GB, `MANIFEST.txt`),
`D:\strehl-out\DELIVER-V6\corpus\` (9 sheets),
`D:\strehl-out\DELIVER-V6\corpus-registered\` (tile-for-tile before/after),
`D:\strehl-out\DELIVER-V6\ca-ab\` (52 A/B pairs).
**Scripts:** `experiments/DELIVER-V6/`.

## 1. Provenance, and why a clean worktree was not paranoia

The shared tree had 60 dirty files when I started. I did not build it. I made a
worktree at `6af834dac08d6605aee7ea3ad75809fdf6313770`, built with a private
target dir, copied the exe out, hashed it, and rendered every master from that
one file.

**This was load-bearing, MEASURED after the fact.** `git rev-parse HEAD` read
`6af834da` when I pinned. It read `165074a1` mid-run and
`dc6419ae00758ac23542a487afc91327950781bb` when I finished. At the first move,
`git diff --stat 6af834da..HEAD -- crates/` was **empty**. By the end it was
not:

```
crates/strehl-cli/src/merge_cmd.rs     |  51 ++
crates/strehl-cli/tests/byte-freeze.rs |  32 ++
crates/strehl-core/src/pyramid.rs      | 537 +++++++++++++++++++++++++++++--
3 files changed, 602 insertions(+), 18 deletions(-)
```

That is BUILD-SOFTGATE landing 537 lines in `pyramid.rs` while I rendered. Had
I built the working tree, the masters would contain some arbitrary intermediate
state of that work and **no one would have been able to tell from the files**.

**Consequence the owner must know:** these masters are commit `6af834da`, not
current `HEAD`. The 602 lines that landed since are in the render path. This
delivery is "the CA fix as of `6af834da`", and if `pyramid.rs` changes output,
a re-render is needed to represent today's tip. I did not test that.

## 2. The confound I was briefed on is not there (MEASURED)

The brief said absolutes are not stable across builds, citing corpus fact 1886:
a coefficient-independent arm re-rendered with 33 003 417 px different, max
23210 DN, purely because the tree moved. The old masters were built from
`8a480af9c6ba-dirty`, six `crates/` commits behind my pin, so old-vs-new looked
confounded: it would answer "what shipped before vs now", not "what did the
coefficient do".

So I built a second binary from **the same pinned commit** with a **one-line**
change (`eps_r: -508.4e-6` -> `-704.5e-6`; `git diff --stat` =
`1 file changed, 1 insertion(+), 1 deletion(-)`) and rendered five subjects.

```
dry-erase-marker-head-cpl            PIXEL-IDENTICAL to shipped master
tweezers-cpl                         PIXEL-IDENTICAL to shipped master
lavendar-cpl                         PIXEL-IDENTICAL to shipped master
highly-angled-ruler-mm-cpl           PIXEL-IDENTICAL to shipped master
113MSDCF                             PIXEL-IDENTICAL to shipped master
```

Five for five, `np.array_equal` on the full 4688x7040x3 arrays. **The six
intervening commits and the dirty tree changed nothing.** Therefore
old-vs-new *is* the coefficient, and every number in section 4 is a
coefficient-only measurement.

**Read that as pixels, not as whole files, and here is the arithmetic to prove
it.** ORCH-FAITHFUL has since been purged (§13), but its per-file SHA256 and
size were banked first, in
`experiments/ORCH-drift-check/purged/ORCH-FAITHFUL-index.txt`. Anyone comparing
those banked hashes against my CA-old arm will find they **differ on all five**,
and I would rather state why than have it look like an overclaim. The file sizes
differ by **exactly -6 bytes on every subject** (e.g. `dry-erase-marker-head-cpl`
198 026 320 -> 198 026 314), which is the length of the `305 Software` string:
`strehl 0.0.0 (8a480af9c6ba-dirty)` is six characters longer than
`strehl 0.0.0 (6af834dac08d)`. The identity claim is about **image content**,
which is what `np.array_equal` tested and what the A/B depends on; the container
metadata necessarily records a different build and cannot match.

I am not able to reconcile this with fact 1886 and I did not try — that is
another lane's measurement on another arm. I note only that 1886's "33 003 417
px" is 99.9997 % of this geometry's 33 003 520 pixels, i.e. essentially every
pixel, which is not what a build-drift-free path looks like. **The path I
rendered is reproducible.** That is worth more than the A/B it enabled.

Corroborating: the warpmap sidecars the two arms solved independently are
**byte-identical** on all three subjects both arms cached
(`113MSDCF`, `dry-erase-marker-head-cpl`, `lavendar-cpl`). The solve does not
see `eps_r`, which matches the code — `OpticalProfile::compose` is called only
at `align_cmd.rs:1929` and `:2095`, both in the warp gather.

## 3. The control subject gets no correction at all (MEASURED + code)

`highly-angled-ruler-mm-cpl` was flagged as the subject the fix could plausibly
make worse: BUILD-CROP 14.6 records it as the only one of 14 still showing the
lens's natural opposite-sign pattern rather than over-correction.

It did not get worse. **It did not change at all: 0 pixels differ**, max delta
0 DN, old vs new.

The reason is not that the coefficient is harmless there. It is that the
correction never executes:

- `TILTED_SUBJECTS` (`align_cmd.rs:42`) contains exactly this subject.
- The render's own banner says so: `alignment : REFUSED -- ... a global
  similarity cannot describe it (M86). Merging unregistered.`
- `merge_cmd.rs:3733`: "an unregistered merge does not resample at all."
- The CA correction is folded into the alignment transform so the gather does
  one interpolation (`optics.rs:283-295`). No gather, no correction.

It also solved no warpmap in either arm, and rendered 299 frames in 63 s
against ~270 s for comparable subjects — both consistent with the warp being
skipped entirely.

**Looked at, at 1:1** (360 px, unresampled, r = 0.60, `ca-ab/ruler-uncorrected-1to1.png`):
the dark ruler lines carry a warm tan edge on one side and a cool grey-blue on
the other. That is the textbook opposite-sign lateral CA pair, still fully
present in the shipping default. Its edge statistic is `mean m = -116 DN`
(negative = green/cyan side), unchanged old to new.

**This is a product gap, not a defect in the fix**, and I am reporting it
rather than acting on it: a subject in the shipping corpus silently receives no
chromatic-aberration correction because its alignment is refused. Anything that
makes CA correction independent of the alignment gather would reach it.

## 4. What the numbers say (MEASURED)

Instrument `experiments/DELIVER-V6/magsummary.py`. Magenta axis
`m = ((R-G) + (B-G))/2`, positive magenta, negative green. Taken on the top 2 %
of luma gradient, with the edge set **chosen on the old master and reused on
the new one** so both arms are scored on identical pixels, and restricted to
`r > 0.5` because lateral CA is zero on the axis by construction.

This is **not** the acceptance metric. `experiments/V-REVIEW/PREREG-v6ca.md`
pre-registered the scoring of this render before it existed and that lane owns
the verdict. I deliberately did not reimplement their statistic; a second
metric computed by the lane that produced the render is how a comparison gets
talked into the answer its author wanted.

**The statistic has a real limit and it decides how to read the table.** On a
green leaf, edge pixels are dominated by the leaf's own colour, not by
fringing. Where `|mean m| / mean|m|` approaches 1, essentially all the signal
is subject hue and the number says nothing about CA. Splitting on that ratio:

**Fringe-dominated — the statistic can see CA (n=14):**

| subject | bias | mean\|m\| old | new | change |
|---|---|---|---|---|
| 113MSDCF | 0.18 | 1838 | 1189 | **-35.3 %** |
| 112MSDCF | 0.09 | 1913 | 1309 | **-31.6 %** |
| flat-on-ruler-cpl | 0.26 | 1878 | 1300 | **-30.8 %** |
| dry-erase-marker-head-cpl | 0.16 | 1634 | 1169 | **-28.4 %** |
| tweezers-cpl | 0.23 | 1595 | 1178 | **-26.1 %** |
| bee-3-cpl | 0.33 | 1856 | 1452 | -21.7 % |
| bee-1-cpl | 0.09 | 1926 | 1550 | -19.5 % |
| coffee-bean | 0.08 | 1302 | 1081 | -17.0 % |
| bee-2-cpl | 0.50 | 1896 | 1585 | -16.4 % |
| lavendar-cpl | 0.28 | 1621 | 1386 | -14.5 % |
| couch-fibers-cpl | 0.42 | 1397 | 1331 | -4.7 % |
| foam | 0.09 | 3121 | 3024 | -3.1 % |
| coffee-bubbles | 0.18 | 2448 | 2398 | -2.0 % |
| 119MSDCF | 0.34 | 3667 | 3654 | -0.4 % |

**14 of 14 improved. Median -17.0 %. No subject regressed.**

**Subject-hue-dominated — it mostly measures the subject's own colour (n=11):**
`wrapped-text-1` -20.2 %, `pencil-steep-angle-cpl` -12.5 %, `wrapped-text-2`
-9.9 %, `flower-bud-alone-cpl` -4.8 %, `pencil-flatter-angle-cpl` -3.6 %,
`flower-bud-with-background-fern-cpl` -2.3 %, `flower-inner-edge-cpl` -1.4 %,
`flowers-cpl` -0.2 %, `leaf-2-cpl` **+0.5 %**, `lead-1-cpl` **+0.7 %**,
`109MSDCF` **+0.9 %**.

The three positives are the whole of the bad news and they are **under 1 %** on
subjects whose bias ratios are 1.00, 1.00 and 0.82 — green leaves and blue ink
on white. That is the subject's colour, not a fringe. I checked `109MSDCF` and
`lead-1-cpl` by eye and see no new colour artifact. **I am not claiming these
are improvements; I am claiming the metric cannot resolve them.**

**Magnitude and bias move in opposite directions and both are reported.** On
`dry-erase-marker-head-cpl`, mean `|m|` falls 22.7 / 29.4 / 25.8 % across three
sites while the *signed* mean rises +133 / +110 / +45 DN. The old image carried
large fringes of both signs that partly cancelled in the signed mean; the fix
shrinks the spread and leaves a slightly more positive centre. Reporting only
`mean |m|` would have made this look cleaner than it is.

## 5. What I saw, subject by subject

Sheets are 1592x1108 and any viewer resamples them, so under AGENTS rule 48 no
defect claim below rests on a sheet. Every colour verdict was taken on a
standalone 360 px or 520 px tile at 1:1. Gross composition notes are from the
sheets and are labelled as impressions.

**The magenta is gone where it was diagnosed.** On
`dry-erase-marker-head-cpl` — BUILD-CROP's "most visible" subject — the ink
blobs in the old master have an unmistakable purple-violet cast along their
edges. In the new master they read as neutral-to-slightly-olive dark. Same on
`flat-on-ruler-cpl`: the bright diagonal scratch is pink in the old master and
white-grey in the new one. These two are the clearest before/afters in the set
and are the ones to look at first
(`ca-ab/dry-erase-marker-head-cpl-site0.jpg`, `ca-ab/flat-on-ruler-cpl-site0.jpg`).

**A green tint appears in the darkest cores** of the dry-erase ink where the
magenta used to be. It is much weaker than the magenta it replaced — consistent
with `|m|` falling 25 % — and I would not call it a defect, but it is a
direction change, not merely a reduction, and the owner should look at it.

**Per subject** (new masters):

- **109MSDCF, 119MSDCF** — blue ink and a red object on white paper. Vivid,
  clean, crisp ink edges. Unchanged to my eye.
- **112MSDCF, 113MSDCF** — white feathery frost-like fibre on grey. Fine
  detail; some noise in the dark background. Largest measured improvements,
  though the subject is near-monochrome so there is little for the eye to see.
- **bee-1-cpl** — the **compound eye tile is the best image in the corpus**:
  sharp, regular ommatidia, clean specular. Two dark specks on it, consistent
  with the known dust motes.
- **bee-2-cpl, bee-3-cpl** — leg and body hair, iridescent green/purple sheen
  on chitin (real, not fringing). A magenta speck on bee-3, consistent with dust.
- **coffee-bean** — warm browns, bean edge against white, fibrous interior. Clean.
- **coffee-bubbles** — bright green/yellow rims on the bubbles. **I checked
  this against the old master specifically because it looked like a
  regression: it is present in both arms, essentially unchanged (-2.0 %).**
  Thin-film interference on the bubble film, not CA.
- **couch-fibers-cpl** — white synthetic fibre and black hairs; neutral, clean.
- **flower-bud-alone-cpl, flower-bud-with-background-fern-cpl,
  flower-inner-edge-cpl** — natural greens and a vivid yellow-green petal with
  translucent hairs; good. `flower-inner-edge-cpl [texture]` is a plain white
  field carrying **the known dust mote**, plainly visible.
- **flowers-cpl** — **visibly soft, large defocused areas.** This is the known
  capture gap, not a merge defect. No code change fixes it; it needs a
  re-shoot.
- **foam** — dark cells with strong rainbow interference on the rims. Real
  colour; barely moved (-3.1 %), as it should not.
- **highly-angled-ruler-mm-cpl** — see section 3. Still visibly fringed, heavy
  depth softening, bit-identical to the old master.
- **lavendar-cpl** — purple bud and white hairs; natural purple, improved 14.5 %.
- **lead-1-cpl, leaf-2-cpl** — green leaf veins. **These two appear to be the
  same leaf captured twice**: same vein junction, same brown speck, sites
  landing eight pixels apart (`y=2284 x=2340` vs `y=2292 x=2356`). Flagging it
  because they are not independent subjects and any corpus-level average
  double-counts them. I did not investigate further.
- **pencil-flatter-angle-cpl** — graphite; the boundary tile is **notably
  soft**, the known depth softening at boundaries.
- **pencil-steep-angle-cpl** — graphite, sharper, neutral.
- **tweezers-cpl** — metal edge, very sharp, neutral. Improved 26.1 %.
- **wrapped-text-1, wrapped-text-2** — toner on paper fibre. **Letter edges are
  neutral grey with no colour cast**, which is the cleanest evidence in the set
  that the correction is not over-shooting: black-on-white text at high
  magnification is where over-correction would be most obvious.

**No new defect found.** I looked specifically for one, and the two candidates
I found (green rims on `coffee-bubbles`, green cores on dry-erase) resolved as
pre-existing and as a much-reduced residual respectively.

## 6. Green moves, and the mechanism is selection (MEASURED)

Between the two one-build arms on `dry-erase-marker-head-cpl` — same commit,
one line different — green moves on **29 386 393 pixels**, mean `|d|` 14.66 DN,
against red's 128.17 DN on 31 049 280 px.

`eps(Green)` returns `None` (`optics.rs:277`) and `compose` returns its input
bit-for-bit when there is no coefficient, so green's gather transform is
**identical** between the arms. Green cannot move by resampling. It moves
because the CA correction changes the per-pixel sharpness the merge elects on,
so a different frame wins at some pixels, and the winning frame's green comes
with it.

BUILD-CROP 16.3 records this as unexplained ("Green moves between CA arms and I
did not finish explaining it"). **ARGUED, not proven:** I have shown green's
transform is unchanged and that the only remaining coupling is selection, but I
did not instrument the election to count flipped pixels. That is the experiment
that would close it, and it is cheap: log the elected frame index per pixel in
both arms and diff.

## 7. Sheets, and how to look at them

Three artifacts, in the order worth opening:

1. `D:\strehl-out\DELIVER-V6\ca-ab\` — **52 before/after pairs**, old master
   left, new master right, same coordinates, 360 px each, one shared display
   transform. Joined `<subject>-siteN.jpg` for the monitor; standalone
   `arms/<subject>-siteN-{OLD,NEW}.png` because the joined pair is 728 px wide
   and a verdict on it would breach rule 48.
2. `D:\strehl-out\DELIVER-V6\corpus-registered\` — the corpus sheets cut at
   **ORCH-EYE's exact coordinates**, so `sheet-NN.jpg` here is tile-for-tile
   registered against `D:\strehl-out\ORCH-EYE\corpus\sheet-NN.jpg`. Flip
   between them.
3. `D:\strehl-out\DELIVER-V6\corpus\` — 9 sheets in ORCH-EYE style, sites
   chosen by the committed picker on the new masters. This is "does the corpus
   look print-worthy", not an A/B.

**Sampling, stated explicitly as required.** Every crop is **one image pixel
per output pixel**, cut with array slicing, no zoom and no resampling at any
stage. The only transform is display: `scale = 1 / percentile(luma, 99.9)` then
`clip(v*scale, 0, 1) ** (1/2.2)`, one transform per subject, **the same
transform on both arms** so a real level difference shows instead of being
normalised away. Masters are linear 16-bit; read with `tifffile`, never PIL.

**The sheet pipeline was commissioned against the reference before use**, and
the check could have failed: driving the committed `orch_corpuseye.py` picker
over the old masters reproduces `ORCH-EYE/corpus/sheet-00.jpg` **byte-identically**
— sha256 `91DD77204EA25343517DC7F510BFA5154A96C6A46CB783A2413CF2AC4C9B6768`,
519 959 bytes, both files. So my sheets come from the same instrument, my
display transform is exactly ORCH-EYE's, and the old masters on disk are
unchanged since ORCH-EYE read them.

## 8. What I did not verify

- **That these masters represent current `HEAD`.** They do not. They are
  `6af834da`; 602 lines have since landed in `pyramid.rs`, `merge_cmd.rs` and a
  byte-freeze test. I did not render `dc6419ae` and cannot say whether it
  differs.
- **Bit-identity of the CA-old arm beyond 5 subjects.** I tested 5 of 26. The
  claim "the six commits are render-neutral" is strongly supported but not
  exhaustive.
- **The election-flip mechanism in section 6.** Argued from the code and from
  green's unchanged transform; not instrumented.
- **`109MSDCF`, `lead-1-cpl`, `leaf-2-cpl` at +0.5 to +0.9 %.** I looked and
  saw nothing, but my statistic cannot resolve a fringe against those subjects'
  own colour, so I cannot assert they did not regress slightly. V-REVIEW's
  signed radial displacement metric can settle it.
- **Print output.** Everything here is screen at 1:1. Nothing was printed.
- **The 7 newer captures** now under `D:\personal\macro` (chia-seeds-cpl,
  dime-flat-narrow-slices-cpl, duck-tape-side-layers-cpl, maldon-sea-salt-cpl,
  medication-pill-cpl, pottery-art-glazed-cpl, unpopped-popcorn-kernels-cpl)
  are **not** rendered. The corpus is 33 subjects now; the masters are the 26
  that ORCH-FAITHFUL shipped, so the comparison stays like-for-like.

## 9. One deviation from the original invocation, declared

The original driver `experiments/ORCH-drift-check/render_head26.ps1` runs
`& $exe stack <dir> -o <target> --srgb` and iterates whatever subject
directories exist. I matched the command exactly and deviated in two ways, both
deliberate:

1. **Subject list pinned to the 26 ORCH-FAITHFUL basenames** rather than
   globbing the capture library, which now holds 33. Globbing would have
   rendered 7 subjects with no counterpart and made the delivery
   non-comparable.
2. **`STREHL_CACHE_DIR` set to a private directory.** The shared warpmap cache
   at `%LOCALAPPDATA%\strehl\warpmaps` held **347 entries** written by other
   lanes' binaries, and the cache key is (canonical capture path, solve config,
   `SOLVE_GENERATION`) — it **does not include the binary**. Another lane's
   warpmap could have been served to my render silently. All other `STREHL_*`
   were explicitly cleared.

**I did not set `STREHL_WARPMAP`, and AGENTS rule 45 should be revised.** The
rule tells you to set it so `stack` does not write sidecars into the read-only
capture library. M97 already fixed that at source: `sidecar_path`
(`align_cmd.rs:1304`) hashes the canonical path and config into `cache_root()`,
outside the capture directory, and I confirmed zero `warpmap.txt` files exist
anywhere under `D:\personal\macro`. Worse, following the rule would have
**changed the render**: `merge_cmd::alignment_for` checks `is_tilted_subject`
only on the `load_or_solve` path, so with `STREHL_WARPMAP` set it loads and
applies a sidecar unconditionally — silently registering
`highly-angled-ruler-mm-cpl`, which the shipping default refuses. The rule as
written would have corrupted the one subject it matters most on.

## 10. Known defects confirmed present, not re-diagnosed

- **Two dust motes on every master.** Seen; clearest on
  `flower-inner-edge-cpl [texture]` (a dark blob on plain white) and on the
  bee-1 compound eye. Correction is built but off by default; another lane owns
  turning it on.
- **`flowers-cpl` is a capture gap.** Confirmed visually — large soft regions.
  No code change fixes it.
- **Depth softening at some boundaries.** Confirmed on
  `pencil-flatter-angle-cpl [boundary]` and across
  `highly-angled-ruler-mm-cpl`, which is merged unregistered.
- `coffee-bean-20-gate2-sidecar` byte-freeze is already RED and is not mine. I
  did not touch `crates/strehl-cli/tests/byte-freezes.tsv`.

## 11. The masters are print files, verified in their own bytes (MEASURED)

The gallery BUILD-OUTPUT audited — `SHIP-V2` — was not a print file: no ICC
profile, no physical resolution, `ResolutionUnit = none`. BUILD-OUTPUT
established that the **code** at HEAD is already correct and the gallery was
simply stale, predating `96b7e119` and `c14284a8`. I confirmed those two commits
are ancestors of my pin (`96b7e119` 2026-08-26 11:27, `c14284a8` 2026-08-26
16:32, pin `6af834da` 2026-08-28 00:51), but an ancestry argument is not
evidence about bytes, so I read the bytes.

**Reader, and why it is not `tifffile`.** I reused BUILD-OUTPUT's
`experiments/BUILD-OUTPUT/tiff_tags.py` rather than writing my own, driven by
`experiments/DELIVER-V6/tagcheck.py`. It parses the raw IFD. This matters:
`tifffile` normalises a *missing* resolution to `(1, 1)`, which is
indistinguishable from a real `1/1`, so the highest-level reader available
cannot see this defect at all.

**Commissioned before it was trusted — and the target in the brief would have
been the wrong file.** The brief asked me to point the reader at an
ORCH-FAITHFUL master and confirm it reports the defect. Those files have since
been purged (§13), so I used `C:\dev\strehl-out\marker.tif`, rendered
2026-08-23 and so predating the ICC fix by three days. It reads:

```
ICC 34675      : ABSENT
XResolution    : 1/1
ResolutionUnit : 1 (none)
```

— the identical defect signature BUILD-OUTPUT quoted from `SHIP-V2`. The reader
can see the defect, so a clean read from it means something. `tagcheck.py`
re-runs this commissioning on every invocation and refuses to check any master
if it fails.

**The substitution was not merely convenient, it was necessary**, and this is
worth banking. ORCH-FAITHFUL was built from `8a480af9c6ba` (2026-08-27 15:11),
and both `96b7e119` and `c14284a8` are **ancestors of that build** — so those
masters already carried the profile and the 300 DPI. Commissioning against one
would have reported *clean*, i.e. the commissioning would have **failed**, and a
lane following the instruction literally would have concluded its reader was
broken. The banked sizes corroborate independently: each old master is **6 bytes
larger** than mine, not ~2716 bytes smaller, and 6 bytes is exactly the extra
length of its `Software` string. **The print defect BUILD-OUTPUT found is real,
but it belongs to `SHIP-V2`, an older gallery — not to ORCH-FAITHFUL.** The
re-render was still the right call; it just was not fixing what the addendum
assumed it was fixing on this particular predecessor.

**Result: 26 of 26 clean.**

| tag | required | found |
| --- | --- | --- |
| 34675 ICCProfile | present, 2716 B | present, 2716 B, TIFF type `UNDEFINED` (7), on all 26 |
| 282 XResolution | `300/1` | `300/1` on all 26 |
| 283 YResolution | `300/1` | `300/1` on all 26 |
| 296 ResolutionUnit | `2` (inch) | `2` (inch) on all 26 |
| 305 Software | — | `strehl 0.0.0 (6af834dac08d)` on all 26 |

The embedded profile is **byte-identical across all 26** (one distinct SHA256),
is a v2.1.0 `mntr`/`RGB`/`XYZ` profile described as `strehl sRGB (IEC
61966-2-1)`, its internal size field agrees with the actual tag length, and its
`rTRC`/`gTRC`/`bTRC` are a 1024-point curve with `f(0.5) = 0.21450` — the sRGB
transfer curve, not a gamma-2.2 stand-in. Tag 34675 carries TIFF type
`UNDEFINED` as the ICC technote specifies, which is worth recording because a
`[u8]` field would naturally encode as `BYTE` and no high-level reader reports
field type. `270 ImageDescription` additionally states the colour space in
words.

Every one of these values is recorded **per subject** in
`C:\dev\strehl-out\DELIVER-V6\masters\MANIFEST.txt`, beside that subject's
output SHA256 and byte count. Nothing regressed between BUILD-OUTPUT's
verification and my render.

## 12. Clipping and crush, as numbers with their subject (MEASURED)

Reported as numbers, not as a verdict, per the instruction not to treat
`orch_printready.py`'s clip gate as one. Measured with BUILD-OUTPUT's
`clip_census.py`, which separates the two mechanisms a flattened three-channel
statistic conflates. **My masters reproduce BUILD-OUTPUT's diagnosis of the gate
exactly:**

- **`dry-erase-marker-head-cpl` — the subject the gate failed — has
  `clipALL3 = 0.0000 %`.** It is still the corpus's cleanest master by that
  measure. The gate is not measuring blown highlights.
- **`flowers-cpl` reads `clipALL3` 0.0087 % but `clipONE` 0.3993 %**, of which
  blue alone is 0.410 % and `B == 65535` exactly is 0.3859 %. That is the
  `gamut_map` signature — an out-of-gamut triple blended to the boundary — not
  a blown highlight. It will keep tripping `CLIP_MAX`; bounding it needs a
  per-channel tone stage. Known non-finding, not re-diagnosed.
- Larger genuine neutral clipping than `flowers-cpl` occurs on **13 of my 26**
  subjects, led by `113MSDCF` 0.0692 %, `flat-on-ruler-cpl` 0.0684 % and
  `112MSDCF` 0.0676 %.

Crush behaves exactly as the brief said it would: **`crushALL3` is 0.0000 % on
24 of my 26**, the exceptions being `foam` 0.0011 % and `coffee-bubbles`
0.0002 %. What the flattened statistic calls crush is single-channel floor
pinning — `109MSDCF` has `R == 0` on 7.54 % of pixels, `119MSDCF` 9.77 %,
`flower-inner-edge-cpl` has `B == 0` on 10.63 % — with the other two channels
nowhere near zero. These are saturated colours resting on the gamut floor, not
black. **Crush must stay ungated.**

## 13. Two things happened to the delivery folder that I did not do (explained)

**The ORCH-FAITHFUL masters have been purged — deliberately, and safely.**
`C:\dev\strehl-out\ORCH-FAITHFUL\faithful\` now contains only `render.log` and
an empty `preview\`. All 26 old master TIFFs are gone; the directory's
LastWriteTime is `2026-08-28 02:53:36`. My renders finished at 02:15 and my
cleanup named only `DELIVER-V6\tgt`, `DELIVER-V6\tgt-caold`, `DELIVER-V6\scratch`,
`D:\strehl-out\DELIVER-V6\corpus-preview` and `DELIVER-V6\masters-caold\*.tiff`.

I first recorded this as data loss. **It is not**, and the correction matters:
commit `0fd8ec7e` ("ORCH: bank-then-purge tool plus indexes for three superseded
scratch trees") landed at **02:53:25**, eleven seconds before the directory was
emptied, and banked
`experiments/ORCH-drift-check/purged/ORCH-FAITHFUL-index.txt` — 5.00 GB of
artifacts reduced to their SHA256, size and inlined text bodies, explicitly so
that "any published claim about them stays checkable". ORCH-FAITHFUL was
superseded by these masters (`dc6419ae`, "orch: faithful gallery for the V6
masters"), which is why it was chosen for purge. This is a standing practice
tonight, not an accident — V-LINEAR, V-ORACLE, V-GATHER, BUILD-CROP, V-REVIEW,
V-DILUTE and BUILD-OUTPUT all banked before purging.

**The practical effect on this report is that §2 stays checkable without the
files**, via the banked hashes and sizes — see the -6-byte reconciliation in §2,
which I would not have been able to state at all if the index had not been
banked. The old arm is additionally *reproducible*: the control binary is still
pinned at `C:\dev\strehl-out\DELIVER-V6\bin\strehl-caold.exe` (sha256
`9DC2F85A99E033E3AE4217EF4FD7923A4836A727AEA562D9B993F3FE0D2F00F1`), the sources
are read-only, and `experiments/DELIVER-V6/render-caold.ps1` regenerates any
subject deterministically. One judgement of mine was still wrong: during cleanup
I deleted my own CA-old arm TIFFs *because* ORCH-FAITHFUL was preserved and
protected. That reasoning was sound at 02:15 and obsolete by 02:53. Banking the
hashes, as I did, is what made it recoverable.

**Seven files I did not render are sitting in my delivery folder — they are
ORCH's.** Between 02:36 and 02:47, after my run ended, seven TIFFs appeared in
`C:\dev\strehl-out\DELIVER-V6\masters\`: `chia-seeds-cpl`,
`dime-flat-narrow-slices-cpl`, `duck-tape-side-layers-cpl`,
`maldon-sea-salt-cpl`, `medication-pill-cpl`, `pottery-art-glazed-cpl`,
`unpopped-popcorn-kernels-cpl`. These are exactly the seven newer captures I
deliberately excluded to keep the subject list matched to ORCH-FAITHFUL. They
report `Software 'strehl 0.0.0 (6af834dac08d)'` — my pinned commit — and they
pass the same tag check. The provenance is not a guess: my private
`scratch\warpmaps\` directory, which I had deleted during cleanup, has been
**recreated** and contains warpmap sidecars for exactly those seven subjects,
timestamped 02:35–02:46 against the seven TIFF writes at 02:36–02:47. Another
lane ran my pinned binary with my `STREHL_CACHE_DIR`, almost certainly by
reusing `experiments/DELIVER-V6/render.ps1` with a different subject list, and
commit `1fe5cb14` ("ORCH: 1:1 eye survey of all seven new subjects, including
the one that is not clean") identifies it as ORCH extending the survey to the
seven captures I excluded. That is a reasonable thing to have done with a pinned
binary. **They are still not mine**: they are in no manifest record and I cannot
attest to their invocation. I have left them in place — and left the 0.2 MB of
regenerated warpmaps in place — and listed the seven as foreign in a
`MANIFEST.txt` trailer. **Anyone counting files in that folder will find 33 and
should treat only the 26 with manifest records as DELIVER-V6 output.**

I re-hashed all 26 of my masters after discovering the folder had been written
to. **All 26 match the SHA256 recorded at render time** — my delivered bytes
have not moved.
