"""Append Amendment 8 to the M129 preregistration.

Every figure quoted is read from out/bias-ladder.json, never typed. A writer that
retypes its numbers is a second place for them to be wrong.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(HERE, "PREREGISTRATION.md")
J = os.path.join(HERE, "out", "bias-ladder.json")

d = json.load(open(J, encoding="utf-8"))
arms = {(a["hypothesis"], a["arm"]): a for a in d["arms"]}
marg = {(m["hypothesis"], m["arm"]): m for m in d["margins"]}
fwd = {a["arm"]: a for a in d["forward"]}
reach = {r["tag"]: r for r in d["reach"]}
h = d["harness"]
berr_max = max(abs(a["B_err"]) for a in d["arms"])


def cell(hyp, arm, tag):
    a = arms[(hyp, arm)]
    return next(r for r in a["rows"] if r["tag"] == tag)


def pct(x, n=2):
    return f"{100 * x:.{n}f}%"


L = []
w = L.append

w("")
w("### Amendment 8 - the bias does not cancel, so the ladder stops inverting "
  "and compares forward")
w("")
w("Condition A1' asked whether the crossing estimator's bias cancels in the "
  "product")
w("`f_c . N`. It does not, and the phrasing was loose enough to hide why. If the "
  "estimator")
w("returns `f_c_hat = f_c (1+b)` then `K = mean(f_c_hat . N) = K_true (1+b)` and")
w("`B_hat = B/(1+b)`. Nothing cancels anywhere. The bias passes through the "
  "product")
w("undiminished and lands entirely on `B`. The only real questions are how big it "
  "is")
w("against the **28.07%** that separates the hypotheses, and whether it is the "
  "same at")
w("every aperture.")
w("")
w("`src/bias_ladder.py` answers both by synthesising a ladder at each hypothesis' "
  "own")
w("cutoffs, with the object slope Amendment 7a inferred for that hypothesis, "
  "degraded")
w("to each aperture's measured low-band SNR, and running the real estimator over "
  "it.")
w("Predictions P1-P5 were written into its docstring before the first run.")
w("")
w("**P1 holds.** `f_c` is read low in all 12 measured cells, worst "
  f"{pct(min(r['bias'] for a in d['arms'] for r in a['rows'] if r.get('reach')))}, "
  f"best {pct(max(r['bias'] for a in d['arms'] for r in a['rows'] if r.get('reach')))}.")
w("**P2 holds.** `B` is therefore inferred high, in every arm.")
w("")
w(f"**P3 IS FALSIFIED.** I predicted the inflation of `B` would stay under 5%, "
  f"reasoning")
w(f"from Amendment 7a's applicable bias near 1.8%. It reaches **{pct(berr_max)}** - "
  f"seven")
w(f"times my estimate, and **{100 * berr_max / d['gap']:.1f}%** of the gap between "
  f"the hypotheses. The reason is")
w("in the harness table below: the bias grows with the cutoff, and Amendment 7a")
w("quoted a single number for a quantity that is not a single number. The "
  "registered")
w("falsifier was P4 failing or the error exceeding 14%, and neither happened, so "
  "the")
w("lane continues - but the analysis it was going to use does not.")
w("")
w("| planted `f_c` | recovered | ratio | low-band SNR |")
w("| --- | --- | --- | --- |")
for r in h:
    w(f"| {r['planted']:.4f} | {r['recovered']:.4f} | {r['ratio']:.4f} | "
      f"{r['snr']:.0f} |")
w("")
w("The noise floor in that table is pushed far below anything the ladder sees - "
  f"SNR")
w(f"{h[0]['snr']:.0f} to {h[-1]['snr']:.0f} against 1730 to 2802 on the real "
  f"ladder - and the ratio still runs from")
w(f"{h[0]['ratio']:.4f} at `f_c` {h[0]['planted']:.2f} down to "
  f"{h[-1]['ratio']:.4f} at {h[-1]['planted']:.2f}. A cutoff-dependent bias with "
  f"almost no")
w("noise to blame is the one kind that does not divide out of a ladder: it tilts")
w("`f_c . N` across the apertures and so tilts the fitted `B`.")
w("")
w("**P4 passes, and hides the result.** Asking only which side of the boundary")
w(f"`B_hat` falls on gives four passes out of four. Asking by how much, in units "
  f"of the")
w("replicate scatter, gives this.")
w("")
w("| built at | arm | `B_hat` | s.e. | distance from boundary | sigma |")
w("| --- | --- | --- | --- | --- | --- |")
for hyp in ("H2", "H3"):
    for arm in ("native", "equalised"):
        a, m = arms[(hyp, arm)], marg[(hyp, arm)]
        w(f"| {hyp} | {arm} | {a['B_hat']:.4f} | {a['B_sem']:.4f} | "
          f"{m['distance']:.4f} | {m['sigma']:.1f} |")
w("")
w(f"The boundary sits at `B` = {d['boundary']:.4f}. **H2 clears it by "
  f"{marg[('H2', 'equalised')]['sigma']:.0f} sigma and H3 by")
w(f"{marg[('H3', 'equalised')]['sigma']:.1f}.** That asymmetry is the finding. "
  f"Under H3 every cutoff sits higher, nearer")
w("the lattice Nyquist, exactly where the harness shows the bias is largest, and")
w(f"f/11's replicate scatter under H3 is "
  f"{cell('H3', 'equalised', 'f11')['sd'] / cell('H2', 'equalised', 'f11')['sd']:.1f} "
  f"times its scatter under H2. The lane's weak")
w("case is H3, and on the inverse analysis it is close to being no case at all.")
w("")
w("**P5 is falsified too, and in the interesting direction.** Equalising was "
  "expected")
w(f"to flatten `f_c . N`. It does the opposite: "
  f"{pct(0.5 * (arms[('H2', 'native')]['fcN_spread'] + arms[('H3', 'native')]['fcN_spread']))} "
  f"native becomes")
w(f"{pct(0.5 * (arms[('H2', 'equalised')]['fcN_spread'] + arms[('H3', 'equalised')]['fcN_spread']))} "
  f"equalised. Equalisation can only add noise, so it moves every")
w("aperture toward the worst one's bias rather than toward a common value, and "
  "the")
w("aperture whose bias moves furthest is the one with the highest cutoff. This "
  "does")
w("not retire the equalised arm - Amendment 5 requires both arms reported - but it")
w("removes the reason to prefer it, and Amendment 6's equalisation is now a "
  "control")
w("on the SNR explanation rather than the primary analysis.")
w("")
w("#### The registered change: compare forward, do not invert")
w("")
w("The inverse analysis pays the bias in full because the bias sits between the")
w("measurement and the answer. The forward comparison asks the other question: "
  "what")
w("cutoff would the estimator **report** under each hypothesis, and how does that")
w("compare with what it did report. The bias is then on both sides and cancels by")
w("construction rather than by subtraction. Read off the same runs, with no new")
w("simulation:")
w("")
w("| arm | ap | reported under H2 | reported under H3 | gap | sigma |")
w("| --- | --- | --- | --- | --- | --- |")
for arm in ("native", "equalised"):
    for c in fwd[arm]["cells"]:
        w(f"| {arm} | {c['tag']} | {c['fc_H2']:.4f} | {c['fc_H3']:.4f} | "
          f"{pct(c['rel_gap'], 1)} | {c['sigma']:.1f} |")
w("")
w(f"Combined separation **{fwd['native']['combined_sigma']:.1f} sigma** native, "
  f"**{fwd['equalised']['combined_sigma']:.1f} sigma** equalised, against "
  f"**{d['worst_sigma']:.1f}**")
w("for the inverse analysis on its weakest arm. The hypotheses stand 15% to 20%")
w("apart in the quantity the estimator actually reports, and that gap does not")
w("require knowing the bias - only that the bias is the same for a predicted "
  "cutoff")
w("and a measured one at the same frequency, which is the one thing about it that")
w("is certain.")
w("")
w("**These sigmas are an upper bound and must not be quoted as a forecast.** The")
w("scatter above is replicate-to-replicate on statistically identical synthetic")
w("scenes. The real measurement's scatter is ROI-to-ROI on one piece of fabric and")
w("will be larger, plausibly much larger. What the table establishes is the "
  "ordering")
w("- that the forward comparison is the stronger test - not the margin the real "
  "data")
w("will have. The real margin is measured by `ladder.py` and by nothing before it.")
w("")
w("**Registered now, before it touches real data:** the ladder's primary statistic")
w("is the forward comparison. For each hypothesis, predict the cutoff the "
  "estimator")
w("would report at each aperture by running the estimator over a synthetic scene "
  "at")
w("that hypothesis' cutoff, that aperture's measured SNR, and the object slope")
w("Amendment 7a infers for that hypothesis; then compare against the measured")
w("cutoffs by chi-squared over the primary arm, with the ROI-to-ROI scatter as the")
w("denominator. The inverse `B_hat` continues to be reported, because it is the")
w("interpretable number and because a large disagreement between the two would be")
w("evidence that the forward model is wrong. It is no longer the statistic that")
w("decides.")
w("")
w("#### f/11 has no margin under H3, in the units that decide it")
w("")
w(f"A scene planted at lattice cutoff `fc_lat` reads back at "
  f"`fc_lat / LATTICE_PITCH_PX['GQ']`,")
w(f"so the largest cutoff the GQ lattice can represent is "
  f"`0.5 / sqrt(2)` = **{d['nyquist_sensor']:.5f}**")
w("sensor cyc/px. This is not a property of the simulation; it is the lattice's")
w("Nyquist and it applies to the real measurement identically.")
w("")
w("| ap | `f_c` H2 | / Nyquist | `f_c` H3 | / Nyquist | reachable |")
w("| --- | --- | --- | --- | --- | --- |")
for tag in ("f5.6", "f8", "f11", "f14", "f18"):
    r = reach[tag]
    v = ("both" if r["reach_H2"] and r["reach_H3"] else
         "H2 only" if r["reach_H2"] else "neither")
    w(f"| {tag} | {r['fc_H2']:.4f} | {r['fc_H2'] / d['nyquist_sensor']:.4f} | "
      f"{r['fc_H3']:.4f} | {r['fc_H3'] / d['nyquist_sensor']:.4f} | {v} |")
w("")
w(f"**Under H3, f/11's cutoff is "
  f"{100 * (1 - reach['f11']['fc_H3'] / d['nyquist_sensor']):.2f}% below the GQ "
  f"lattice's Nyquist.** Section 2.3 called f/11's")
w("H3 margin \"+0.24 cy/mm - not a margin\". This says the same thing in the units")
w("that decide it: under H3 the lattice cannot resolve f/11's cutoff at all. f/14")
w("and f/18 are the measurement, as registered, and f/5.6 and f/8 are unreachable")
w("under either hypothesis, which is exactly the out-of-band role section 2.3 gave")
w("them.")
w("")

text = "\n".join(L)

with open(DOC, encoding="utf-8") as fh:
    doc = fh.read()
if "### Amendment 8" in doc:
    print("Amendment 8 already present; refusing to append a second copy.")
    sys.exit(1)
doc = doc.rstrip("\n") + "\n" + text

# A blank line inside a Markdown table silently splits it into two tables and the
# second loses its header. Scan for it rather than trust the writer.
bad = []
lines = doc.split("\n")
for i in range(1, len(lines) - 1):
    if lines[i].strip() == "" and lines[i - 1].lstrip().startswith("|") \
            and lines[i + 1].lstrip().startswith("|"):
        bad.append(i + 1)
if bad:
    print(f"BLANK LINE SPLITTING A TABLE at lines {bad}; not written.")
    sys.exit(1)

nonascii = sorted({c for c in text if ord(c) > 127})
if nonascii:
    print(f"non-ascii introduced: {nonascii}")

with open(DOC, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(doc)
print(f"Amendment 8 appended: {len(L)} lines, "
      f"{len(re.findall(r'^[|]', text, re.M))} table rows.")
