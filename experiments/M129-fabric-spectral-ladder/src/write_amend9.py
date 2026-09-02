"""Generate Amendment 9. Every figure is read from JSON; nothing is retyped.

R2's two scorings are RECOMPUTED here from ladder.json's cells rather than copied
from any earlier note, so the honest score and the rescoped score are both derived
from the same source the verdict came from.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
DOC = os.path.join(ROOT, "PREREGISTRATION.md")
TAGS = ["f5.6", "f8", "f11", "f14", "f18"]
INBAND = ["f14", "f18"]


def J(n):
    with open(os.path.join(OUT, n), encoding="utf-8") as fh:
        return json.load(fh)


def main():
    lad, guard = J("ladder.json"), J("reach-guard.json")
    fb, fbf, pc, diag = J("fit-b.json"), J("fit-b-fine.json"), J("pixel-check.json"), J("ladder-diag.json")
    cells, meas = lad["cells"], lad["measured"]
    g = {r["tag"]: r for r in guard}
    rA, rAp = fb["route_A"]["pooled"], fb["route_A"]["per_aperture"]
    pa, on, off = fbf["per_aperture"], pc["routes"]["on"], pc["routes"]["off"]
    bnd = pc["bound"]

    rois = sorted({c["roi"] for c in cells})

    def mono(tags, strict):
        ok = 0
        for r in rois:
            v = [next((c["f_c"] for c in cells
                       if c["roi"] == r and c["aperture"] == t), None) for t in tags]
            if not all(x is not None for x in v):
                continue
            good = all((v[i] > v[i + 1]) if strict else (v[i] >= v[i + 1])
                       for i in range(len(v) - 1))
            ok += good
        return ok, len(rois)

    r2_all, n_all = mono(TAGS, False)
    r2_all_s, _ = mono(TAGS, True)
    r2_pri, n_pri = mono(["f11", "f14", "f18"], True)
    r2_in, n_in = mono(INBAND, True)
    assert (r2_all, n_all) == (lad["monotone"]["ok"], lad["monotone"]["tested"]), (
        "recomputed R2 disagrees with the score ladder.py recorded")
    bad = set()
    for r in rois:
        v = [next(c["f_c"] for c in cells
                  if c["roi"] == r and c["aperture"] == t) for t in TAGS]
        for i in range(len(TAGS) - 1):
            if v[i] <= v[i + 1]:
                bad.add(TAGS[i])
                bad.add(TAGS[i + 1])

    L = []
    A = L.append
    A("")
    A("### Amendment 9 - all three hypotheses are rejected, and B is measured instead")
    A("")
    A("Amendment 8 registered the forward comparison as the primary statistic and")
    A("`ladder.py` ran it. It rejected **both** live hypotheses, with every residual")
    A("of the same sign: the real cutoffs sit ABOVE what either predicts.")
    A("")
    A("| ap | n | measured `f_c` | s.e. | H2 predicted | z | H3 predicted | z |")
    A("| --- | --- | --- | --- | --- | --- | --- | --- |")
    zt = {h: {x["tag"]: x["z"] for x in lad["chi2_primary"][h]["terms"]}
          for h in ("H2", "H3")}
    for t in ["f11"] + INBAND:
        m = meas[t]
        h2 = lad["predicted"]["H2"][t].get("fc_hat")
        h3 = lad["predicted"]["H3"][t].get("fc_hat")
        A(f"| {t} | {m['n']} | {m['mean']:.4f} | {m['sem']:.4f} | "
          f"{h2:.4f} | {zt['H2'][t]:+.2f} | {h3:.4f} | {zt['H3'][t]:+.2f} |")
    A("")
    A(f"Chi-squared over the arm as registered: H2 "
      f"{lad['chi2_primary']['H2']['chi2']:.2f}, H3 "
      f"{lad['chi2_primary']['H3']['chi2']:.2f}, on "
      f"{lad['chi2_primary']['H3']['dof']} terms. H3 is the better of the two and")
    A("is still rejected outright.")
    A("")
    A("A rejection in which every residual shares a sign is not a coin landing")
    A("badly; it is a parameter set wrongly. This amendment records what was wrong,")
    A("retracts one diagnosis that turned out to be a consequence rather than a")
    A("cause, and replaces the two-way test with a measurement of `B` itself.")
    A("")
    A("#### 9.1 f/11 is out of band, so the primary arm was mis-scoped")
    A("")
    A("The out-of-band detector is not a judgement call. `knee_model_fit` reports")
    A("`above_reach` when the fitted cutoff exceeds the highest frequency the")
    A("lattice can measure, and M5's commissioning validated it at 36/36 with no")
    A("false alarms. Asked about this data it says:")
    A("")
    A("| ap | `above_reach` | crossing `f_c` | model-fit `f_c` | floor slope |")
    A("| --- | --- | --- | --- | --- |")
    for t in TAGS:
        r = g[t]
        A(f"| {t} | {r['above_reach']}/{r['n']} | {r['knee_fc']:.4f} | "
          f"{r['fit_fc']:.4f} | {r['floor_slope']:.3f} |")
    A("")
    A("**f/11 is out of band, 6/6.** Section 2.3 registered it as \"a supporting")
    A("point\" whose H3 margin \"is not a margin\", and Amendment 8 sharpened that to")
    A("0.35% below the lattice Nyquist. The data has now demoted it the rest of the")
    A("way: at f/11 the crossing rule is not reporting a diffraction cutoff at all.")
    A("")
    A("An independent statistic agrees without being asked. The fitted floor slope")
    A(f"is {g['f5.6']['floor_slope']:.2f}, {g['f8']['floor_slope']:.2f} and "
      f"{g['f11']['floor_slope']:.2f} at the three out-of-band apertures - steeply")
    A("negative, which is signal still falling, not a floor - against")
    A(f"{g['f14']['floor_slope']:.3f} and {g['f18']['floor_slope']:.3f} at f/14 and")
    A("f/18, which are flat. The three apertures whose guard fires are exactly the")
    A("three that never reach a floor, and their crossing cutoffs cluster at")
    A(f"{g['f5.6']['knee_fc']:.4f}, {g['f8']['knee_fc']:.4f}, "
      f"{g['f11']['knee_fc']:.4f} - the fabric's own texture limit, which is a")
    A("property of the subject and not of the aperture.")
    A("")
    A("**The chi-squared that rejected H2 and H3 included f/11 and should not")
    A("have.** That does not rescue either hypothesis - section 9.3 rejects them")
    A("far more decisively on the two apertures that are in band - but the")
    A("mis-scoping is recorded as an error in the registered analysis, not")
    A("silently corrected.")
    A("")
    A("#### 9.2 R2 was mis-scoped by me, and both scores are reported")
    A("")
    A("R2 was registered as \"`f_c` falls monotonically with f-number in every")
    A("ROI\", over all five apertures. The registered wording does not say whether")
    A("a tie counts as falling, and the two readings differ:")
    A("")
    A(f"* ties allowed, which is how `ladder.py` scored it: **{r2_all}/{n_all}**")
    A(f"* ties disallowed, the literal reading of \"falls\": **{r2_all_s}/{n_all}**")
    A("")
    A("Either way it failed. The ambiguity is not a loophole worth arguing over,")
    A("because the ties are an artefact of the instrument rather than of the")
    A("subject: the crossing rule reports a radial bin, bins are 4.34% of `f_c`")
    A("wide, and two apertures whose cutoffs differ by less than a bin must report")
    A("the same number.")
    A("")
    A(f"Over the three-aperture primary arm R2 is **{r2_pri}/{n_pri}** and over the")
    A(f"two in-band apertures **{r2_in}/{n_in}**, both under the strict reading.")
    A("")
    A("**Every tie and every rise involves only "
      f"{', '.join(sorted(bad, key=TAGS.index))}.** The f/11 -> f/14 -> f/18 chain")
    A("never ties and never rises in any ROI. The prediction failed exactly and")
    A("only where section 9.1 has just shown the estimator is not measuring optics.")
    A("")
    A("The registered scoring is the one that counts and it failed. But the")
    A("prediction was unsatisfiable as written, and that is my error rather than")
    A("the subject's: an aperture whose cutoff lies beyond the lattice cannot roll")
    A("off inside the band, so f/5.6 and f/8 cannot be monotone with anything. A")
    A("prediction that no possible sensor could satisfy tested nothing. Both")
    A("numbers are quoted here permanently so the failure cannot be read off as a")
    A("success by quoting only the primary arm.")
    A("")
    A("#### 9.3 Retraction: the \"shape excess\" was a wrong B, not a wrong shape")
    A("")
    A("`ladder_diag.py` compared the real spectrum against the model's with each")
    A("normalised by its own low band, so only shape was compared, and found the")
    A("real spectrum running above the model through the roll-off. It named the")
    A("candidate causes before testing them and concluded the real MTF rolls off")
    A("more slowly than ideal diffraction. **That conclusion is withdrawn.** It was")
    A("computed at H3's `B`, and H3's `B` is wrong. Rebuilt at the fitted `B`, in")
    A("the same bins with the same normalisation, the excess collapses:")
    A("")
    A("| ap | peak real/synth at H3 | peak at fitted `B` |")
    A("| --- | --- | --- |")
    for t in INBAND:
        pr = max(r["ratio"] for r in diag["shape"] if r["tag"] == t)
        A(f"| {t} | {pr:.2f} | {fbf['peaks'][t]:.2f} |")
    A("")
    A("The registered threshold was that both peaks fall below 1.25, and both do.")
    A("The diffraction MTF shape was never in trouble; the cutoff it was evaluated")
    A("at was. This is recorded as a retraction because the earlier reading would")
    A("have sent the lane after a new optical model it did not need.")
    A("")
    A("#### 9.4 `B` measured two ways, and why they agree")
    A("")
    A("`B` is the effective-f-number multiplier, `N_eff = B N`. All three")
    A("hypotheses of section 2.2 carry the same magnification - `(B-1)p` is")
    A(f"{', '.join(f'{(b - 1) * p:.4f}' for b, p in [(3.7319, 0.9956), (3.0763, 1.3099), (2.4020, 1.9400)])}")
    A(f"- so they differ only in pupil magnification through `B = 1 + m/p` with")
    A(f"`m` = {fb['m']:.4f}. **Measuring `B` measures `p`.**")
    A("")
    A("| route | what it assumes | what it pays | `B` |")
    A("| --- | --- | --- | --- |")
    A(f"| A model fit | diffraction shape | no crossing bias | "
      f"{rA['B']:.4f} +- {rA['sem']:.4f} |")
    A(f"| B forward | diffraction shape | the bias, on both sides | "
      f"{fbf['best']['B']:.2f} |")
    A("")
    A("The two routes agree to "
      f"{abs(fbf['best']['B'] - rA['B']):.4f} in `B`. That agreement was checked")
    A("rather than admired. Route A calls `knee_model_fit`, whose `pixel_mtf`")
    A("argument defaults to true, so it models the 5.12 um photosite; route B")
    A("synthesises through `equalise._scene`, which applies `mtf_diffraction` and")
    A("nothing else, so it does not. Refitting route A with the photosite term off")
    A("is therefore a like-for-like comparison, and it was registered in advance")
    A("that `B` must RISE:")
    A("")
    A("| route A setting | f/14 `B` | f/18 `B` | mean `B` | distance to route B |")
    A("| --- | --- | --- | --- | --- |")
    for k, r in (("photosite on", on), ("photosite off", off)):
        A(f"| {k} | {r['per']['f14']['B']:.4f} | {r['per']['f18']['B']:.4f} | "
          f"{r['B']:.4f} | {abs(r['B'] - pc['route_B']):.4f} |")
    A("")
    A(f"Modelled like for like the two routes differ by "
      f"{abs(off['B'] - pc['route_B']):.4f}. The entire original disagreement was")
    A("the photosite, and it is now accounted for rather than merely small. An")
    A("independent estimator that does not pay the crossing bias and a forward")
    A("comparison that pays it on both sides land in the same place.")
    A("")
    A("#### 9.5 One `B` does not fit both apertures")
    A("")
    A("| ap | route A `B` | route B `B` | route B |z|<=1 | implied `p` |")
    A("| --- | --- | --- | --- | --- |")
    for t in INBAND:
        iv = pa[t]["interval"]
        A(f"| {t} | {rAp[t]['B']:.4f} +- {rAp[t]['B_sem']:.4f} | "
          f"{pa[t]['B']:.2f} | {iv[0]:.2f} to {iv[1]:.2f} | {pa[t]['p']:.4f} |")
    A("")
    A(f"The gap is {rAp['f14']['B'] - rAp['f18']['B']:+.4f} by route A and")
    A(f"{fbf['gap']:+.2f} by route B - two routes, one answer - and the intervals")
    A("do not overlap. **The apparent `B` falls as the aperture closes**, which a")
    A("single bellows factor cannot do.")
    A("")
    A("The photosite is excluded as the cause, and was excluded by a test that")
    A("expected to fail so that a pass would have been news. Removing the term")
    A(f"moves the gap by only {pc['P7_gap_delta']:.4f}, against a registered")
    A("threshold of 0.05. A term already in the model cannot explain a residual the")
    A("model still has.")
    A("")
    A("**What this lane cannot decide.** The surviving candidates are residual")
    A("defocus - registered as threat T1 - lens aberration, and vibration. All")
    A("three inflate the apparent `B`, and all three inflate it more at the wider")
    A("aperture: defocus and aberration because they worsen as the pupil opens, an")
    A("absolute blur because diffraction has less roll-off of its own to hide")
    A("behind. They share a sign, so two in-band apertures cannot separate them,")
    A("and section 9.1 has just removed the third. **This lane does not identify")
    A("which, and no later section should claim it did.**")
    A("")
    A("#### 9.6 What survives: a one-sided bound, which is what the evidence supports")
    A("")
    A("Because every surviving candidate biases `B` upward, the aperture least")
    A("contaminated by them bounds the true value from above. That is a weaker")
    A("claim than a two-sided interval and it is the one the evidence actually")
    A("supports - a two-parameter fit to two apertures would have zero degrees of")
    A("freedom and could not be wrong.")
    A("")
    A(f"**`B` <= {bnd['B']:.4f} +- {bnd['sem']:.4f}** (at {bnd['aperture']}, "
      f"n = {bnd['n']}), hence **`p` >= {pc['p_lower']:.4f}**.")
    A("")
    A("| hypothesis | `B` | `p` | s.e. above the bound | verdict |")
    A("| --- | --- | --- | --- | --- |")
    for k, (Bh, ph) in {"H1": (3.7319, 0.9956), "H2": (3.0763, 1.3099),
                        "H3": (2.4020, 1.9400)}.items():
        z = (Bh - bnd["B"]) / bnd["sem"]
        A(f"| {k} | {Bh:.4f} | {ph:.4f} | {z:+.1f} | "
          f"{'EXCLUDED' if z > 3 else 'not excluded'} |")
    A("")
    A("All three registered hypotheses are excluded, H3 - the survivor the lane was")
    A("built to test - by "
      f"{(2.4020 - bnd['B']) / bnd['sem']:.1f} standard errors. The pupil")
    A("magnification is larger than any of them assumed, so the bellows factor at")
    A(f"{fb['m']:.2f}x magnification is smaller, the true cutoff is higher, and")
    A("there is more recoverable detail at a given marked aperture than the")
    A("registered hypotheses allowed.")
    A("")
    A("**Registered now, before anything acts on it:** the successor lane must")
    A("recover a third in-band aperture before the residual trend can be")
    A("attributed. f/16 sits between the two survivors and is in band under the")
    A("measured `B`; a capture at f/16 and f/22 would give four in-band points and")
    A("two spare degrees of freedom, which is the minimum that can distinguish a")
    A("defocus term from an absolute blur. Until then the one-sided bound is the")
    A("result.")
    A("")

    txt = "\n".join(L)
    with open(DOC, "r", encoding="utf-8") as fh:
        cur = fh.read()
    assert "Amendment 9" not in cur, "Amendment 9 already present"
    with open(DOC, "w", encoding="utf-8") as fh:
        fh.write(cur.rstrip("\n") + "\n" + txt)
    n = txt.count("\n")
    print(f"appended Amendment 9: {n} lines, "
          f"{sum(1 for x in L if x.startswith('|'))} table rows")
    print(f"R2 scored: all {r2_all}/{n_all} (ties allowed), {r2_all_s}/{n_all} "
          f"(strict), primary {r2_pri}/{n_pri}, in-band {r2_in}/{n_in}")
    print(f"apertures involved in any tie or rise: "
          f"{', '.join(sorted(bad, key=TAGS.index))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
