import io, json, datetime, numpy as np
rows = [r for r in json.load(open("vc_score.json")) if r["verdict"] == "SCORED"]
uns  = [r for r in json.load(open("vc_score.json")) if r["verdict"] != "SCORED"]
dr = np.array([r["d_ppmR"] for r in rows]); ra = np.array([r["ratio"] for r in rows])
db = np.array([r["d_ppmB"] for r in rows]); wr = np.array([r["width_ratio"] for r in rows])
tbl = "\n".join(
    "| `%s` | %d | %+.1f | %+.1f | %+.1f | %.1f | %.3f | %+.1f | %.4f |" %
    (r["subject"], r["n_paired"], r["ppmR_old"], r["ppmR_new"], r["d_ppmR"],
     r["nsigma"], r["ratio"], r["d_ppmB"], r["width_ratio"]) for r in rows)
unst = "\n".join("| `%s` | %s | %s |" % (r["subject"], r["verdict"], r.get("note","")) for r in uns)
t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

txt = """# V-REVIEW: independent scoring of DELIVER-V6's CA re-fit -- INTERIM

Written %s, at session wind-down. **This is unfinished and says so.** 11 of 26
subjects are scored; the remaining 15 had not rendered when compute was handed
back to the render.

I am the independent eye on this render per ORCH's assignment. I scored the
images, not DELIVER-V6's report; I have read none of its conclusions.

## 1. Endpoint, and why it is not the statistic you distrusted

Signed radial displacement of R against G, in ppm of radius, measured at
gradient sites and **sign-symmetric by construction**. It is deliberately NOT a
magenta counter. The statistic that scored `--fix-ca off` as 1.82x better counts
magenta specifically and is therefore blind to the opposite-sign orange/cyan
shape that over-correction produces. This endpoint sees both signs.

Sites are chosen once from the OLD master's green channel and applied to both
images, so every comparison is **paired per site**. That is not cosmetic: the
unpaired form injected +16.8 ppm of phantom signal on `dry-erase` and -97.7 ppm
on the ruler, purely from which sites voted.

## 2. Commissioning (MEASURED, through the shipped entry point `score()`)

| arm | result |
|---|---|
| identity, old vs itself | `d_ppmR` 0.000000000, ratio 1.000000000, width_ratio 1.000000000 |
| positive, planted -508.4 ppm | recovered **-508.6 ppm** at 41.5 sigma |
| specificity, blue untouched | **+0.0 ppm** |
| confound null, pure resample | width_ratio **1.0000** |

The positive plant is deliberately the exact magnitude of the coefficient under
test. An identity test alone proves only that the instrument is quiet.

## 3. Result

| subject | n | ppmR old | ppmR new | delta | sigma | ratio | d_ppmB | widthR |
|---|---|---|---|---|---|---|---|---|
%s

| subject | verdict | why |
|---|---|---|
%s

- scored: **%d**; ratio < 1 (improved) on **%d of %d**; ratio > 1 on **%d**
- `d_ppmR` median **%+.1f ppm**, range %+.1f .. %+.1f, all at %.1f sigma or better
- ratio median **%.3f**, range %.3f .. %.3f

**Reading: the re-fit reduces red-green misregistration on every subject that
could be scored, by roughly half to two-thirds. No subject got worse.**

## 4. What this does NOT say

1. **Improvement, not cure.** `ppmR_new` remains positive (+30.9 .. +251.4).
   Residual outward CA is present on every subject.
2. **Pre-registered P3 -- "blue unchanged" -- is REFUTED as stated.** Blue moved
   at %.1f to %.1f sigma. It moves ~%.0fx less than red (median |dB/dR| %.3f), so
   it cannot account for red's change, and a generic build difference would have
   moved both alike. But P3 failed and is recorded as failed.
3. **The pre-named control subject is UNRESOLVED.** `highly-angled-ruler-mm-cpl`
   never rendered. See section 6.
4. **%d subjects are UNSCORED, which is not the same as clean.**

## 5. Build-difference confound, bounded by measurement

Old and new masters come from different builds, so any difference not
attributable to CA is confounded. Bound rather than argument:

- paired edge-width variance ratio old vs new: **%.4f .. %.4f**; worst is
  `flat-on-ruler-cpl` at %.4f, about 0.23 px of added sigma.
- measured paired blur sensitivity of the CA endpoint: **exactly +0.0 ppm at
  sigma=0.3 on all four subjects tested**; non-zero only at sigma >= 0.6, worst
  -77.2 ppm at sigma=1.2 on the ruler.

A ~187 ppm effect therefore sits far above the confound floor in this regime.

## 6. The ruler prediction is OPEN

`PREDICT-ruler.md` was committed in `82b1c411` with the master verified absent
from disk. It predicts `d_ppmR` in -237 .. -132, `ppmR_new` about **-394**,
ratio about **1.9** -- i.e. the one subject the fix makes worse, because its
baseline is already the opposite sign (`ppmR_old` = -207.1, MEASURED).

**It never rendered, so the prediction is neither confirmed nor refuted.** To
resolve it, one command after the master exists:

    python vc_score.py highly-angled-ruler-mm-cpl

## 7. Instrument failures I am disclosing rather than hiding

- **`vc_ca.py` FAILS its BLUR-ONLY arm on the ruler** (4/5 arms; paired -77.2 ppm
  at sigma=1.2, 7.3 sigma from zero) while passing **5/5** on `dry-erase`. I did
  not loosen the tolerance to make it pass.
- **`vc_sharp.py`'s sigma-equivalent estimator FAILED commission** on all three
  width statistics below ~0.5 px (errors -0.19 to -0.59 against planted sigma).
  Its numbers are used nowhere. Only the raw paired width RATIO, whose null is
  exactly 1.000, is used.
- Two defects in my own estimator were found by commissioning and fixed before
  any scoring: a missing `align` division, and orientation-dependent aliasing in
  `profile()` that measured gain **0.170 at 45 degrees**. The latter alone had
  produced a spurious 1.114 "real-edge asymmetry" that vanished to 0.988 once
  fixed.
""" % (t, tbl, unst, len(rows), int((ra<1).sum()), len(ra), int((ra>1).sum()),
       np.median(dr), dr.max(), dr.min(), min(r["nsigma"] for r in rows),
       np.median(ra), ra.min(), ra.max(),
       min(r["nsigmaB"] for r in rows), max(r["nsigmaB"] for r in rows),
       1.0/np.median(np.abs(db/dr)), np.median(np.abs(db/dr)),
       len(uns), wr.min(), wr.max(), wr.max())
io.open("V6-CA-interim.md", "w", newline="\n", encoding="utf-8").write(txt)
print("wrote V6-CA-interim.md")
