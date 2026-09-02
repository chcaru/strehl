"""Generate Amendment 10 and append it to PREREGISTRATION.md.

Every figure is read from the JSON the scripts wrote and formatted here. Nothing
is retyped from a terminal, because a number typed twice is a number that can
disagree with itself and no checker downstream would ever see the original.
"""

import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
OUT = os.path.join(LANE, "out")
PRE = os.path.join(LANE, "PREREGISTRATION.md")


def load(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as fh:
        return json.load(fh)


def main():
    db = load("defocus-b.json")
    rb = load("defocus-robust.json")
    sn = load("defocus-sens.json")
    vd = load("defocus-verdict.json")

    # ---- recomputations, so the document is not merely a transcript ----
    rows = sn["rows"]
    waves = sn["waves"]
    ir = waves.index(0.25)
    d = [r["series"][ir]["B"] - r["series"][0]["B"] for r in rows]
    assert min(abs(x) for x in d) - sn["S3_at_rayleigh"]["min_abs"] < 1e-9, \
        "S3 magnitude does not reproduce from the per-ROI series"
    assert all(x < 0 for x in d), "the sign of the defocus response is not uniform"

    wpf = vd["waves_per_frame"]
    r14 = sum(wpf["f14"]) / len(wpf["f14"])
    r18 = sum(wpf["f18"]) / len(wpf["f18"])
    assert abs(r14 / r18 - vd["ratio_measured"]) < 1e-6, "ratio disagrees"

    ncur = len(db["cells"])
    nneg = sum(1 for c in db["cells"] if c["curv"] < 0)
    assert nneg == ncur, "not every real cell has negative curvature"

    vmax = max(db["agg"][k]["vertex_absmax"] for k in ("f14", "f18"))
    assert abs(vmax - max(abs(c["vertex"]) for c in db["cells"])) < 1e-9, \
        "the recorded worst vertex disagrees with the per-cell values"

    gaps = rb["gap_by_common_offset"]
    assert all(v > 0 for v in gaps.values()), "a common-offset gap is not positive"

    per_wave = sn["verdict"]["per_wave"]
    lo, hi = rb["gap_span_adversarial"]

    t = []
    a = t.append
    a("")
    a("---")
    a("")
    a("## Amendment 10 - residual defocus is excluded, and by the opposite sign")
    a("")
    a("Amendment 9 left one thing unresolved: apparent `B` falls as the aperture")
    a("closes, f/14 above f/18 by a gap that no candidate could be pinned on.")
    a("Threat T1 named residual defocus as the leading suspect, because f/14's")
    a("depth of field is shallower and an identical residual focus step therefore")
    a("costs more defocus there. This amendment closes T1. It is excluded, and not")
    a("by a bound that happened to come out small - by the direction of the effect,")
    a("which is opposite to the one T1 requires.")
    a("")
    a("Four scripts, run in this order. Two of them failed as registered and both")
    a("failures are recorded here rather than repaired out of sight.")
    a("")

    # 10.1
    a("### 10.1 The direct test failed its own control")
    a("")
    a("`defocus_b.py` walked the frame offset from -3 to +3 in each of the twelve")
    a("in-band cells, refitted `B` at every offset and fitted a parabola. Its")
    a("control C1 required the parabola vertex to sit within one frame of the")
    a("frame the focus map had already chosen.")
    a("")
    a(f"| check | registered | measured | verdict |")
    a(f"| --- | --- | --- | --- |")
    a(f"| P8 | curvature positive at both apertures | "
      f"{db['agg']['f14']['curv']:+.4f} and {db['agg']['f18']['curv']:+.4f} | FAIL |")
    a(f"| P9 | f/14 curvature exceeds f/18 | "
      f"{'larger' if abs(db['agg']['f14']['curv']) > abs(db['agg']['f18']['curv']) else 'smaller'}"
      f" in magnitude, "
      f"{'larger' if db['agg']['f14']['curv'] > db['agg']['f18']['curv'] else 'smaller'}"
      f" in sign | FAIL as coded |")
    a(f"| P10 | gap below 0.05 after correction | "
      f"{db['gap_vertex']:+.4f} at the vertices | FAIL |")
    a(f"| C1 | vertex within 1 frame of the focus map | "
      f"worst {vmax:+.2f} frames | VOID |")
    a("")
    a("P9 has the same prose-versus-code split that 10.3 records for S3, and it is")
    a("noted here for the same reason. Its prose says the f/14 curvature exceeds")
    a("f/18, glossed as rising faster; the code compared the two signed values.")
    a("Under P8's premise that both parabolas open upward those are the same")
    a("comparison. Once the curvatures came out negative they are opposites, and")
    a("the two readings disagree. Nothing turns on it, because C1 voided the whole")
    a("group, but a discrepancy found and left unrecorded is one that gets")
    a("rediscovered as a contradiction later.")
    a("")
    a("C1 failed, so P8 through P10 are not interpretable and **are not claimed**,")
    a("here or anywhere else. They are listed because a registered prediction that")
    a("is quietly dropped is indistinguishable from one that was never made.")
    a("")
    a(f"The curvature is negative at {nneg} of {ncur} cells: fitted `B` is")
    a("**highest** near best focus and falls away on both sides. I read that at the")
    a("time as the estimator failing, on the reasoning that a fit which assumes a")
    a("diffraction-limited MTF has no business being trusted on a deliberately")
    a("defocused frame. That reading is retracted in 10.3. The reasoning was sound")
    a("and the conclusion was wrong.")
    a("")

    # 10.2
    a("### 10.2 What the voided test still established")
    a("")
    a("`defocus_robust.py` asked what the per-offset values say about Amendment 9")
    a("regardless of where the true optimum lies, since they are measurements and")
    a("not fits to any theory of focus.")
    a("")
    a(f"| question | measured | verdict |")
    a(f"| --- | --- | --- |")
    a(f"| does the exclusion of H3 survive an adversarial frame choice | "
      f"the largest `B` any f/18 cell reaches at any offset is "
      f"{rb['f18_max_any_offset']:.4f}, still {rb['H3_se_above_worst']:.1f} s.e. "
      f"below H3 | PASS |")
    a(f"| could a frame-selection bias have made the gap | letting the two "
      f"apertures take different offsets, the reachable gap spans "
      f"{lo:+.4f} to {hi:+.4f} | PASS, never closes |")
    a("")
    a("The gap keeps its sign at every offset held in common:")
    a("")
    a("| offset | gap |")
    a("| --- | --- |")
    for k in sorted(gaps, key=lambda x: int(x)):
        a(f"| {int(k):+d} | {gaps[k]:+.4f} |")
    a("")
    a(f"Within a single stack `B` swings by about "
      f"{rb['stats']['f14']['within']:.2f} across the seven offsets, which is")
    a("larger than the gap under investigation. That the gap survives anyway is")
    a("because the swing is largely cell-specific and averages away over six ROIs,")
    a("while the gap does not.")
    a("")
    a("**That conclusion rested on an unexamined premise**: that moving the frame")
    a("moves the estimator. A blind instrument would also have shown a gap that")
    a("survives every offset. Closing that is what 10.3 is for.")
    a("")

    # 10.3
    a("### 10.3 Commissioning the estimator against a known defocus")
    a("")
    a("`defocus_sens.py` measures the estimator's defocus response on synthetic")
    a("data where the truth is known exactly. Each real in-band PSD is fitted once,")
    a("a clean PSD is regenerated from those parameters on the identical frequency")
    a("grid and bin counts, defocus is applied to that, and the fit is repeated.")
    a("Nothing but the defocus changes.")
    a("")
    a("The defocused MTF is computed from first principles as the normalised")
    a("autocorrelation of the complex pupil, not from a published closed form.")
    a("Closed forms for the defocus MTF circulate with several different constants")
    a("inside the Bessel argument, and the wrong one would silently rescale the")
    a("wave axis and every number derived from it.")
    a("")
    a(f"| check | registered | measured | verdict |")
    a(f"| --- | --- | --- | --- |")
    a(f"| S0 | pupil code matches `mtf_diffraction` at zero defocus, rms < 2e-3 | "
      f"{sn['S0_rms']:.3e} | PASS |")
    a(f"| S1 | round trip recovers the seeded cutoff to 1% | "
      f"{sn['S1_worst_fc_pct']:.3f}% worst | PASS |")
    a(f"| S2p | fitted `B` rises with defocus | it falls | FAIL |")
    a(f"| S5 | null control: 0.01 waves moves `B` under 0.01 | "
      f"{sn['S5_worst']:.4f} worst | PASS |")
    a(f"| S3 | a quarter wave moves `B` by more than 0.05 | "
      f"{sn['S3_at_rayleigh']['min_abs']:.4f} at the least responsive ROI | "
      f"PASS as worded |")
    a("")
    a("**S3 was written two ways and they disagree.** The registered prose asks")
    a("whether the estimator moves `B` by more than 0.05 and glosses a pass as")
    a("\"the estimator is not blind\", which is a question about magnitude. The code")
    a("as first written also demanded the sign S2 predicted. Once that direction")
    a("turned out to be wrong the two readings separated, so both are reported and")
    a("the script prints both. The blindness question is the magnitude one and it")
    a(f"passes by a factor of {sn['S3_at_rayleigh']['min_abs'] / 0.05:.1f} at the")
    a("worst cell. The signed reading fails for the same reason S2p fails and is")
    a("not independent evidence.")
    a("")
    a("**An earlier run of this script failed and the failure was mine.** Run 1")
    a("multiplied the analytic diffraction MTF by the value returned from the pupil")
    a("code, which already contains that envelope, so the envelope was applied")
    a("twice. The signature was unmistakable in hindsight: fitted `B` jumped +0.51")
    a("at 0.05 waves, a defocus that is optically negligible. Run 1 is preserved at")
    a("`out/defocus-sens-run1.txt`. S5, the null control, was added afterwards")
    a("precisely because it is the check that would have caught it, and it now")
    a("stands permanently alongside S3: a positive control alone cannot tell a")
    a("sensitive instrument from one that lurches at any input.")
    a("")
    a(f"**The measured response.** Defocus LOWERS fitted `B`, by")
    a(f"{per_wave:+.4f} per wave over the monotone range")
    a(f"{sn['monotone_waves']}. Lower `B` means a LARGER fitted cutoff, which is")
    a("the opposite of the naive expectation registered as S2. The reason is")
    a("visible in S4: the slope absorbs the defocus, alpha steepening from")
    a(f"{sn['S4_alpha0']:.4f} to {sn['S4_alphaR']:.4f} over a quarter wave, and a")
    a("steeper scene term needs a wider diffraction term to trace the same curve.")
    a("The two free parameters trade, and the cutoff moves against the eye.")
    a("")
    a("**This overturns 10.1's diagnosis.** The peak in `B` at best focus is not")
    a("the estimator failing. It is the estimator's genuine response, in the same")
    a("direction, measured where the answer is known. The real B-versus-offset")
    a("curves are defocus curves. C1 still stands as failed and P8 through P10 are")
    a("still not claimed, because P8 asked for a curvature sign now known to be the")
    a("wrong way round, and a registered prediction cannot be reinterpreted into a")
    a("pass after the fact.")
    a("")

    # 10.4
    a("### 10.4 The real curves match the calibrated law")
    a("")
    a("`defocus_verdict.py` puts the twelve measured curvatures through the")
    a("synthetic law. The two ends were measured independently - the synthetic side")
    a("knows nothing about focus rails, the real side nothing about wavefronts - so")
    a("agreement is not built in anywhere.")
    a("")
    a(f"| check | registered | measured | verdict |")
    a(f"| --- | --- | --- | --- |")
    a(f"| V1 | the law is quadratic, exponent in [1.8, 2.2] | "
      f"abs(dB) = {vd['law_c']:.4f} W20^{vd['law_q']:.4f} | PASS |")
    a(f"| V2 | implied defocus per frame below a quarter wave everywhere | "
      f"worst {max(max(wpf['f14']), max(wpf['f18'])):.5f} waves | PASS |")
    a(f"| V3 | spread across the six ROIs, cv below 0.40 | "
      f"{vd['cv']['f14']:.3f} at f/14, {vd['cv']['f18']:.3f} at f/18 | PASS |")
    a(f"| V4 | defocus has the sign needed to explain the gap | it has the "
      f"opposite sign | PASS, T1 excluded |")
    a("")
    a("V1 matters beyond itself. A quadratic in wavefront error, with defocus")
    a("linear in frame offset, makes `B` a parabola in offset - which is the form")
    a("`defocus_b.py` fitted before any of this was known.")
    a("")
    a(f"The implied defocus is {r14:.5f} waves per frame at f/14 and")
    a(f"{r18:.5f} at f/18, so {0.25 / r14:.2f} frames at f/14 and "
      f"{0.25 / r18:.2f} at f/18 to")
    a("the Rayleigh quarter wave. That is a sensibly sampled stack, and V3 says")
    a("the whole field agrees on it.")
    a("")
    a("**A consistency observation, and it is labelled as such because the ratio")
    a("was worked out by hand before the check was written.** It carries no pass or")
    a("fail. A constant physical step would give f/14")
    a(f"{vd['ratio_fixed_step']:.3f} times the defocus per frame, since the")
    a("wavefront error goes as the reciprocal of the squared effective f-number,")
    a(f"which is {vd['n_eff']['f14']:.2f} at f/14 and {vd['n_eff']['f18']:.2f} at")
    a("f/18. A step scaled to the diffraction depth of field would give exactly 1,")
    a("since that depth carries the same squared factor. Measured:")
    a(f"{vd['ratio_measured']:.3f}.")
    a(f"That favours {vd['favours']}, which is the standard way to bracket a macro")
    a("stack, and it means the two stacks carry comparable defocus per frame rather")
    a("than f/14 carrying half again as much.")
    a("")

    # 10.5
    a("### 10.5 What is settled and what is not")
    a("")
    a("**Threat T1 is excluded.** T1 says f/14 carries more residual defocus. More")
    a("defocus lowers fitted `B`. So T1 predicts f/14 measures **lower** than f/18")
    a(f"and the gap should be negative. The measured gap is {vd['gap']:+.4f},")
    a(f"{'positive' if vd['gap'] > 0 else 'negative'}. The prediction and the")
    a("observation have opposite signs.")
    a("")
    a("This does not depend on the calibration constant, on the focus step, on")
    a("which frame the focus map chose, or on the parabola fit. It depends on two")
    a("independently measured signs, both large.")
    a("")
    a("**What it does not settle.** The aperture trend itself remains unexplained.")
    a("Defocus is now off the list; aberration and rig geometry remain, they share")
    a("a sign, and two in-band apertures cannot separate them. Section 34 of")
    a("`docs/captures-needed.md` still stands and its priority is unchanged: a")
    a("third and fourth in-band aperture are what distinguishes the survivors.")
    a("")
    a("**A side result worth carrying forward.** The estimator's defocus response")
    a("is now calibrated, so `B` measured across a focus sweep is a usable focus")
    a("metric with a physical scale attached, reading out directly in waves. The")
    a("vertex of the parabola locates best focus to a fraction of a frame. Whether")
    a("that beats the mid-band focus score the survey currently uses is untested")
    a("and is not claimed.")
    a("")
    a("**A pattern in my own errors, recorded because three is enough to be one.**")
    a("Amendment 9 retracted a shape diagnosis that was an artefact of a wrong `B`.")
    a("This amendment retracts a failure diagnosis that was an artefact of a wrong")
    a("assumed direction, and records a registered direction, S2, that was simply")
    a("backwards. In all three the magnitudes were sound and the signs and")
    a("baselines were not. The corrective that worked every time was the same:")
    a("compute the thing forward from a known truth instead of reasoning about")
    a("which way it ought to go. House rule 18 asks for the direction to be stated")
    a("before measuring, which these did. Stating it did not make it right; only")
    a("the synthetic forward model did.")
    a("")

    text = "\n".join(t)
    shutil.copy2(PRE, os.path.join(os.environ.get("TEMP", "."),
                                   "PREREGISTRATION.before-a10.md"))
    with open(PRE, "r", encoding="utf-8") as fh:
        cur = fh.read()
    if "Amendment 10" in cur:
        print("Amendment 10 already present; refusing to append twice")
        return 1
    with open(PRE, "a", encoding="utf-8") as fh:
        fh.write(text)

    n = len(open(PRE, encoding="utf-8").read().splitlines())
    print(f"appended Amendment 10, PREREGISTRATION.md is now {n} lines")
    print(f"backup at {os.path.join(os.environ.get('TEMP', '.'), 'PREREGISTRATION.before-a10.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
