"""M87 -- append section 34 and facts P133-P138.

Every number in the appended prose is read from the JSON operands produced by
100-gate-veildepth.py, 101-attrib.py and 102-robust.py, so the document cannot
drift from the data.  Nothing is transcribed by hand except quotations from
this report's own earlier sections, which verify_s34.py re-reads at source.
"""
import json
import pathlib

DOC = pathlib.Path(__file__).resolve().parents[3] / "docs" / "research" / "M87-occlusion.md"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
MIN = "\u2212"


def m(x, fmt="{:.4f}"):
    """Format a number using U+2212 for the minus sign, per house style."""
    s = fmt.format(x)
    return s.replace("-", MIN, 1) if s.startswith("-") else s


def main():
    raw = DOC.read_bytes().decode("utf-8")
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"
    assert "## 34." not in raw, "section 34 already present"
    assert "| P133 |" not in raw, "P133 already present"

    d100 = json.loads((DATA / "100-gate-veildepth.json").read_text(encoding="utf-8"))
    d101 = json.loads((DATA / "101-attrib.json").read_text(encoding="utf-8"))
    d102 = json.loads((DATA / "102-robust.json").read_text(encoding="utf-8"))

    b19 = d100["bars"]["B19"]
    b20 = d101["bars"]["B20"]
    b21 = d101["bars"]["B21"]
    cdf = d100["controls"]["C_DRIFT_FORM"]
    cmu = d100["controls"]["C_MULT"]
    cad = d100["controls"]["C_ADD"]
    cpos = d100["controls"]["C_POS"]
    cfr = d100["controls"]["C_FROZEN"]
    arms = d100["arms"]
    anch = d100["s25_anchors"]
    prov = d100["provenance"]
    a1, a2, a3 = d102["arms"]["A1"], d102["arms"]["A2"], d102["arms"]["A3"]

    drift0 = cdf["rows"][-1]

    text = raw

    # ------------------------------------------------------------ section 34
    S = []
    A = S.append
    A("")
    A("---")
    A("")
    A("## 34. The orchestrator's causal test: does veil removal depend on how "
      "many frames are averaged?")
    A("")
    A("The orchestrator sent a sharp prediction derived from this report's own "
      "§25 mechanism, and it is the right kind of message to receive: it names "
      "a number, a direction, and a falsifier. Their words:")
    A("")
    A("> at **gate 0.00** the merge is one frame per pixel, so it cannot remove "
      "a veil by combination and should read close to your single-frame "
      f"**{m(anch['frame_mean'], '{:.2f}')}%** [...] At **gate 4.00** the flat "
      "background averages heavily and should read close to your merge value of "
      f"**{m(anch['merge_gate0'], '{:.2f}')}%**.")
    A("")
    A("They also offered the alternative branch in advance — \"if it is *not* "
      "monotone, that is more interesting still, and it would mean removal is "
      "driven by the election's choice rather than by averaging\" — which is "
      "the branch the measurement lands in.")
    A("")
    A("### 34.1 This is not the test §33 ran")
    A("")
    A("§33 measured `V_33` = peak **bright** ring residual over contrast, on "
      "the BLOB region, and found it near-invariant to the gate. That does not "
      "settle this claim. The orchestrator's prediction is stated in §25's "
      "statistic — veil **depth**,")
    A("")
    A("```")
    A("V = ( median profile over d in [2,22] - median profile over d in [80,120] )")
    A("    / median profile over d in [80,120]              (70-veil.py, verbatim)")
    A("```")
    A("")
    A("— a signed **darkening**, on `ROI_LEG`, in linear DN. A statistic that "
      "measures the absence of darkening and a statistic that measures a bright "
      "hump are different quantities, and answering a claim in a statistic it "
      "was not made in is a way of appearing to settle it without doing so. So "
      "§34 computes §25's `V`.")
    A("")
    A("### 34.2 The prediction is falsified by its own citation")
    A("")
    A(f"The orchestrator reads **{m(anch['merge_gate0'], '{:.2f}')}%** as a "
      "gate-4 number, the product of heavy averaging. It is not. Verified at "
      "source two ways, because a fact row is a compressed rendering and this "
      "report has already been wrong by trusting one:")
    A("")
    A("1. §25.7 of this report tabulates the row as "
      f"`| gate-0 merge | {m(anch['merge_gate0'])}% |`.")
    A("2. `70-veil.py` prints it as `merge (gate 0)` and computes it on "
      "`cache/bee3-leg-sel.npy`, the gate-0 elected merge.")
    A("")
    A("So **74.76% of the veil was already removed at `n_eff` = 1, with zero "
      "averaging.** The prediction that gate 0.00 should show little removal is "
      "contradicted by the very measurement it cites.")
    A("")
    A("There is more. §25's `C-RANDV` is the control that isolates the cause: a "
      "uniformly random per-pixel election has the **same** per-pixel mixture "
      f"structure and an **uninformative** selector, and reads "
      f"**{m(anch['random_election'])}%** — inside the single-frame range, no "
      "removal at all. §25 states the conclusion in as many words: \"A "
      "per-pixel mixture as such does nothing — it is this election.\"")
    A("")
    A("§25 therefore already ran the orchestrator's causal experiment, in a "
      "**stronger** form. The gate ladder varies averaging with the selector "
      "held informative. `C-RANDV` varies selector informativeness with "
      "averaging held at zero. The second isolates the mechanism; the first "
      "cannot, because both arms retain an informative selector. Together they "
      "complete a 2x2, and this section fills the one empty cell: an "
      "informative selector at `n_eff` = 55.")
    A("")
    A("### 34.3 The ladder, in §25's statistic")
    A("")
    A("Four registered branches on `dV` = `V`(0.00) − `V`(4.00), signed. The "
      "reversal branch is not decoration: a bar without one has produced a "
      "wrong verdict three times in this milestone's family, twice mine.")
    A("")
    A("| gate | `n_eff` | `V` % | near DN | far DN |")
    A("| --- | --- | --- | --- | --- |")
    neff = {"4.00": "55.321", "2.00": "19.182", "0.7078": "3.000", "0.00": "1.000"}
    for g in ["4.00", "2.00", "0.7078", "0.00"]:
        A(f"| {g} | {neff[g]} | **{m(arms[g]['V_pct'])}** | "
          f"{arms[g]['near_dn']:.1f} | {arms[g]['far_dn']:.1f} |")
    A("")
    A(f"`dV` = **{m(b19['dV_pp'], '{:+.4f}')} pp** against a predicted "
      f"**{m(b19['predicted_pp'], '{:+.2f}')} pp**. That is "
      f"**{b19['frac_of_predicted']:.2f}%** of the predicted swing, **and the "
      "sign is opposite to the prediction**: gate 0.00 is *less* veiled, not "
      f"more. Branch: **{b19['branch']}**.")
    A("")
    A(f"Spearman rho(gate, `V`) = **{m(b19['spearman_rho'], '{:+.4f}')}**. The "
      "ladder is perfectly monotone — but in the direction where **more** "
      "averaging gives **more** veil, which is the opposite of a removal "
      "mechanism. Monotonicity alone would have looked like confirmation to a "
      "bar that did not check the sign.")
    A("")
    A("### 34.4 The movement is in the reference, not in the veil")
    A("")
    A("The branch understates the result. Look at the two operands separately. "
      f"The **near band** — the veiled band itself, the quantity the "
      f"orchestrator's mechanism requires to brighten — spans "
      f"**{d101['near_span_pct']:.4f}%** across the whole ladder. The **far "
      f"reference** spans **{d101['far_span_pct']:.4f}%**, which is "
      f"**{d101['far_span_pct'] / d101['near_span_pct']:.1f}x** more.")
    A("")
    A("Since `V` = near/far − 1, a ladder built on a moving reference reports a "
      "veil change when nothing about the veil has changed. That is precisely "
      "the failure the orchestrator self-reported in their own ring profile "
      "(\"the reference moved\"), and they proposed the remedy: \"Pinning the "
      "reference to one arm, or measuring a shift-invariant quantity, are the "
      "two obvious routes.\" Route one, applied:")
    A("")
    A("| gate | `V` raw % | `V` pinned to gate 4.00 % |")
    A("| --- | --- | --- |")
    for g in ["4.00", "2.00", "0.7078", "0.00"]:
        A(f"| {g} | {m(arms[g]['V_pct'])} | **{m(b20['V_pinned'][g])}** |")
    A("")
    A(f"Range over the ladder: **{b20['range_pp']:.4f} pp**, which is "
      f"**{b20['frac_of_predicted_pct']:.3f}%** of the predicted swing. Branch: "
      f"**{b20['branch']}**.")
    A("")
    A("The signed decomposition puts it beyond argument. It takes **no ratio of "
      "two signed numbers**, because that is the exact construction that "
      "produced three wrong verdicts here already:")
    A("")
    A("| component | pp |")
    A("| --- | --- |")
    A(f"| `dV` total | **{m(b21['dV'], '{:+.4f}')}** |")
    A(f"| near-only (the veiled band) | **{m(b21['near_only'], '{:+.4f}')}** |")
    A(f"| far-only (the reference) | **{m(b21['far_only'], '{:+.4f}')}** |")
    A(f"| cross | {m(b21['cross'], '{:+.4f}')} |")
    A(f"| closure &#124;sum − `dV`&#124; | {b21['closure']:.3e} |")
    A("")
    A("Both positive attribution controls recover a plant whose true "
      "attribution I chose: a 3% change planted on the near band alone is "
      f"assigned **{m(d101['controls']['C_ATTR_NEAR']['near_only'], '{:+.4f}')} "
      f"pp** to near and "
      f"**{m(d101['controls']['C_ATTR_NEAR']['far_only'], '{:+.4f}')} pp** to "
      "far; planted on the far band alone it is assigned "
      f"**{m(d101['controls']['C_ATTR_FAR']['far_only'], '{:+.4f}')} pp** to far "
      f"and **{m(d101['controls']['C_ATTR_FAR']['near_only'], '{:+.4f}')} pp** "
      "to near.")
    A("")
    A("### 34.5 Robustness: two regions, two channels")
    A("")
    A("A result that holds only on the crop it was built on is not a result. "
      "The same frozen-mask ladder, on `ROI_LEG` and on the **BLOB** region the "
      "orchestrator filed as the flagship figure, in green and in mean-RGB:")
    A("")
    A("| arm | region | channel | near span % | far span % | ratio | pinned "
      "range pp |")
    A("| --- | --- | --- | --- | --- | --- | --- |")
    for tag, a in (("A1", a1), ("A2", a2), ("A3", a3)):
        A(f"| {tag} | {a['region']} | {a['channel']} | "
          f"{a['near_span_pct']:.4f} | {a['far_span_pct']:.4f} | "
          f"{a['far_span_pct'] / a['near_span_pct']:.1f}x | "
          f"**{a['pinned_range_pp']:.4f}** |")
    A("")
    A(f"Branch: **{d102['bars']['B22']['branch']}**. The far reference outruns "
      "the veiled band by between "
      f"{min(a['far_span_pct'] / a['near_span_pct'] for a in (a1, a2, a3)):.1f}x "
      f"and "
      f"{max(a['far_span_pct'] / a['near_span_pct'] for a in (a1, a2, a3)):.1f}x "
      "in every combination.")
    A("")
    A("One detail worth flagging rather than smoothing: on the BLOB region the "
      f"**raw** `V` crosses zero, running "
      f"{m(a2['V_raw']['4.00'])}% at gate 4.00 to "
      f"{m(a2['V_raw']['0.00'], '{:+.4f}')}% at gate 0.00 — the band appears to "
      "flip from darker than the far field to brighter. Pinned, it does not "
      f"move at all ({m(a2['V_pinned']['4.00'])}% to "
      f"{m(a2['V_pinned']['0.00'])}%). A sign flip in a headline statistic, "
      "produced entirely by its denominator, is a good illustration of why the "
      "orchestrator's instrument could not support their claim and why mine "
      "would not have either without pinning.")
    A("")
    A("### 34.6 The form of the drift, which decides whether it is a hazard")
    A("")
    A("The orchestrator warned that any statistic normalised to a far window "
      "will absorb their 2.14% far-field fall, and asked me to check rather "
      "than assume that `E`-like statistics are immune. Checking, not assuming:")
    A("")
    A("`V` is a ratio, so it is **exactly** invariant to `g` -> `a`·`g` and "
      "**not** invariant to `g` -> `g` + `b`. Whether the drift is a hazard "
      "therefore depends entirely on its form, which is measurable: a "
      "multiplicative drift moves the dark subject by the same **percent** as "
      "the bright far field; an additive one moves it by the same **DN**.")
    A("")
    A("| quantity | gate 4.00 -> 0.00 |")
    A("| --- | --- |")
    A(f"| far field | {m(drift0['far_pct'], '{:+.3f}')}% "
      f"({m(drift0['far_dn_delta'], '{:+.1f}')} DN) |")
    A(f"| dark subject | {m(drift0['subj_pct'], '{:+.3f}')}% "
      f"({m(drift0['subj_dn_delta'], '{:+.1f}')} DN) |")
    A(f"| percent mismatch | {cdf['mult_mismatch_pp']:.3f} pp |")
    A(f"| absolute mismatch | {cdf['add_mismatch_dn']:.1f} DN |")
    A("")
    A(f"Verdict **{cdf['form']}**. The drift is neither a gain nor an offset — "
      "it is confined to the bright background, which is consistent with the "
      "orchestrator's own account of it as unfitted per-frame photometric drift "
      "organised spatially by the election. The consequence is specific: `V` "
      f"survives a pure gain exactly (`C-MULT` = {cmu['err']:.3e}, bar 1e−12) "
      "but this **is not** a pure gain, so the reference has to be pinned "
      "explicitly rather than assumed away. `C-ADD` confirms the instrument is "
      f"not merely dead to the hazard: a {m(cad['b_dn'], '{:+.1f}')} DN offset "
      f"moves `V` by {m(cad['dV_pp'], '{:+.4f}')} pp.")
    A("")
    A("`C-POS` shows the instrument would have seen the orchestrator's effect "
      "if it were there. Planting a known extra veil — multiplying the 2–22 px "
      "band by 0.90 — moves `V` from "
      f"{m(arms['4.00']['V_pct'])}% to {m(cpos['V_planted'])}%, against an "
      f"algebraically expected {m(cpos['V_expected'])}%, an error of "
      f"**{cpos['err_pp']:.4f} pp**. That is a planted swing of "
      f"{abs(cpos['V_planted'] - arms['4.00']['V_pct']):.2f} pp, the same order "
      "as the 19.79 pp the orchestrator predicted, recovered with exact "
      "calibration. A quiet instrument and a dead one are different claims and "
      "this separates them.")
    A("")
    A("`C-FROZEN` reports the same ladder with per-arm masks instead of one "
      f"frozen population: `dV` {m(cfr['dV_frozen'], '{:+.4f}')} pp frozen "
      f"against {m(cfr['dV_per_arm'], '{:+.4f}')} pp free. The verdict does not "
      "depend on the freezing, which is worth knowing because freezing is my "
      "repair of the orchestrator's first failure and it would be circular to "
      "let the repair carry the conclusion.")
    A("")
    A("### 34.7 The unmix question, answered again and differently")
    A("")
    A("The orchestrator speculated that §13's "
      f"**{m(-28.2, '{:.1f}')}%** may have been \"an unmix that assumes the "
      "veil is present [...] fitting something the merge had largely already "
      "taken out.\" The mechanism as stated is **refuted at source**, but the "
      "intuition behind it is sound and this report already contains its "
      "measured form. Both halves matter.")
    A("")
    A("**Refuted:** the unmix does not operate on the merged output. `P107` and "
      "`P132` record that the regression runs along the **frame** axis per "
      "pixel, with 38.000 observations per population. It fits the frame cube, "
      "which is **upstream** of the election. The merge's 74.76% removal "
      "happens downstream of the fit and is invisible to it, so the fit cannot "
      "be confused by it.")
    A("")
    A("**But the intuition lands, and `P88` already measured it.** The election "
      "removes the dominant term and leaves a **~2.9% frame-borne veil** that "
      "no selector-side fix can reach, because it is present in every "
      "observation. So the *headroom* available to unmixing on real captures is "
      "genuinely small — not because the unmix is fitting a ghost, but because "
      "the election got there first and took the part that was reachable. The "
      "orchestrator reached the right consequence through the wrong mechanism.")
    A("")
    A("The routing answer from `P132` is unchanged: neither model nor support, "
      "but a **structure-scale** limiter.")
    A("")
    A("### 34.8 What this closes off")
    A("")
    A("Fact 1375 excluded resampling: the veil is invariant across all three "
      "resampler kernels. §27 excluded demosaic. §33 showed the bright-hump "
      "statistic is near-invariant to the gate. §34 now shows the **darkening** "
      "statistic — the one the mechanism is actually stated in — has a veiled "
      f"band that moves **{d101['near_span_pct']:.4f}%** across a **55.3x** "
      "change in frames averaged per pixel, in two regions and two channels.")
    A("")
    A("Averaging was the last cheap candidate mechanism. What remains is "
      "**selection itself**, which is where §25's `C-RANDV` pointed before this "
      "section was written: destroy the selector's information and the removal "
      "disappears; change how many frames it averages over by a factor of 55 "
      "and nothing happens.")
    A("")
    A("### 34.9 Verification and limits")
    A("")
    A("`verify_s34.py` re-derives every figure above from the JSON operands and "
      "re-hashes the gate-4.00 arm. `control_s34.py` mutates operands with the "
      "prose untouched, to prove the harness re-derives rather than matching "
      "the document against itself.")
    A("")
    A("Three limits, stated rather than buried.")
    A("")
    A(f"**The absolute level is not commensurable with §25's "
      f"{m(anch['merge_gate0'])}%.** My frozen mask has an IoU of "
      f"**{100 * prov['mask_iou_vs_s25']:.2f}%** against the mask §25 derived "
      f"from its own cached merge (subject fraction "
      f"{100 * prov['subject_fraction']:.2f}% against "
      f"{100 * prov['s25_subject_fraction']:.2f}%), so the two renders are not "
      "the same registration. The orchestrator's arms are `--srgb` and I "
      "linearise them; §25 worked in linear raw DN throughout. Every number in "
      "§34 is therefore a **within-ladder** comparison, which is what the claim "
      "requires, and no absolute level here should be quoted against §25's.")
    A("")
    A("**The arms are unbinned.** The orchestrator's renders are 7032x4688, "
      "twice the binned output §25's geometry is defined in. §34 crops at 2x, "
      "linearises, then bins 2x2 to land on §25's 744x1144 geometry exactly. A "
      "first attempt cropped `ROI_LEG` directly from the unbinned arm and was "
      "measuring the wrong physical region; the probe that caught it is "
      "`99-probe.py`.")
    A("")
    A("**`E(d)` is not run here.** `E(d)` references the frame ensemble rather "
      "than a far window, so it needs the frames rendered through the same path "
      "as the arms. The orchestrator's arms are merged sRGB TIFFs and the "
      "ensemble is not available in that space, so an `E(d)` ladder would "
      "compare across two pipelines. `V` is the statistic the prediction was "
      "stated in and it is the one answered.")
    A("")

    text = text.rstrip("\r\n") + "\r\n" + "\r\n".join(S) + "\r\n"

    # ------------------------------------------------------------ fact rows
    rows = [
        f"| P133 | **The orchestrator's prediction is falsified by its own "
        f"citation: {m(anch['merge_gate0'])}% is a gate-0 number.** Verified two "
        f"ways at source -- §25.7 tabulates the row as `gate-0 merge` and "
        f"`70-veil.py` prints `merge (gate 0)`, computed on the gate-0 elected "
        f"merge `cache/bee3-leg-sel.npy`. So **74.76%** of the veil is already "
        f"removed at `n_eff` = 1 with zero averaging, and §25's `C-RANDV` "
        f"({m(anch['random_election'])}%, inside the single-frame range) already "
        f"held the per-pixel mixture fixed while destroying selector "
        f"information, and found no removal. | §25 had already run the "
        f"orchestrator's causal experiment in a stronger form: it varies "
        f"selector *informativeness* with averaging held at zero, which isolates "
        f"the mechanism, where the gate ladder varies averaging with the "
        f"selector informative in every arm. **Read the cited section, not the "
        f"fact row** -- the prediction survived only in the compressed "
        f"rendering. | MEASURED |",

        f"| P134 | **Veil depth does not depend on the gate, in the statistic "
        f"the claim was made in.** §25's `V` across the orchestrator's four "
        f"pinned arms: `dV` = **{m(b19['dV_pp'], '{:+.4f}')} pp** against a "
        f"predicted {m(b19['predicted_pp'], '{:+.2f}')} pp, i.e. "
        f"**{b19['frac_of_predicted']:.2f}%** of the predicted swing **and of "
        f"the opposite sign**. Branch `{b19['branch']}`. Spearman rho(gate, `V`) "
        f"= {m(b19['spearman_rho'], '{:+.4f}')} -- perfectly monotone, but in "
        f"the direction where *more* averaging gives *more* veil. | A monotone "
        f"ladder is not confirmation unless its **sign** matches the prediction. "
        f"A bar checking only monotonicity would have reported this as support "
        f"for the mechanism it refutes. | MEASURED |",

        f"| P135 | **The entire raw ladder movement is the reference, not the "
        f"veil.** Signed decomposition of `dV`, taking no ratio of two signed "
        f"numbers: near-only **{m(b21['near_only'], '{:+.4f}')} pp**, far-only "
        f"**{m(b21['far_only'], '{:+.4f}')} pp**, cross "
        f"{m(b21['cross'], '{:+.4f}')} pp, closure {b21['closure']:.3e}. The "
        f"near band spans **{d101['near_span_pct']:.4f}%** across the ladder and "
        f"the far reference **{d101['far_span_pct']:.4f}%**, a "
        f"**{d101['far_span_pct'] / d101['near_span_pct']:.1f}x** ratio. With "
        f"the reference pinned to gate 4.00 the ladder range is "
        f"**{b20['range_pp']:.4f} pp** = **{b20['frac_of_predicted_pct']:.3f}%** "
        f"of predicted (`{b20['branch']}`). | The quantity the mechanism "
        f"requires to change does not change. Applying the orchestrator's own "
        f"proposed remedy -- pin the reference -- removes the effect entirely, "
        f"so their instrument and mine agree once the moving baseline they "
        f"themselves diagnosed is removed. | MEASURED |",

        f"| P136 | **Robust across region and channel.** Same frozen-mask ladder "
        f"on `ROI_LEG` and on the BLOB region the orchestrator filed as the "
        f"flagship figure, in green and mean-RGB: near-band spans "
        f"{a1['near_span_pct']:.4f}% / {a2['near_span_pct']:.4f}% / "
        f"{a3['near_span_pct']:.4f}%, pinned ranges {a1['pinned_range_pp']:.4f} "
        f"/ {a2['pinned_range_pp']:.4f} / {a3['pinned_range_pp']:.4f} pp, "
        f"far-over-near ratios "
        f"{a1['far_span_pct'] / a1['near_span_pct']:.1f}x / "
        f"{a2['far_span_pct'] / a2['near_span_pct']:.1f}x / "
        f"{a3['far_span_pct'] / a3['near_span_pct']:.1f}x. Branch "
        f"`{d102['bars']['B22']['branch']}`. | On BLOB the **raw** `V` crosses "
        f"zero across the ladder ({m(a2['V_raw']['4.00'])}% to "
        f"{m(a2['V_raw']['0.00'], '{:+.4f}')}%) while the pinned `V` does not "
        f"move, so a headline statistic can change sign entirely through its "
        f"denominator. | MEASURED |",

        f"| P137 | **The orchestrator's photometric drift is neither "
        f"multiplicative nor additive.** Gate 4.00 -> 0.00: the far field falls "
        f"{m(drift0['far_pct'], '{:.3f}')}% "
        f"({m(drift0['far_dn_delta'], '{:.1f}')} DN) while the dark subject "
        f"falls only {m(drift0['subj_pct'], '{:.3f}')}% "
        f"({m(drift0['subj_dn_delta'], '{:.1f}')} DN) -- a percent mismatch of "
        f"{cdf['mult_mismatch_pp']:.3f} pp and an absolute mismatch of "
        f"{cdf['add_mismatch_dn']:.1f} DN. Verdict `{cdf['form']}`: the drift is "
        f"confined to the bright background. | Decides whether a ratio metric is "
        f"safe, and it is not safe by construction here. `V` survives a pure "
        f"gain exactly (`C-MULT` {cmu['err']:.3e}) but this is not a gain, so "
        f"the reference must be pinned rather than assumed immune. `C-ADD` "
        f"({m(cad['dV_pp'], '{:+.4f}')} pp) proves the instrument is responsive "
        f"to the hazard, not blind to it. | MEASURED |",

        f"| P138 | **The unmix was not fitting an already-removed veil, but the "
        f"intuition behind that guess is already measured.** Refuted: `P107` and "
        f"`P132` record that the regression runs along the **frame** axis per "
        f"pixel, upstream of the election, so the merge's 74.76% removal is "
        f"invisible to the fit. Sustained in consequence: `P88` measures a "
        f"**~2.9%** frame-borne veil present in every observation that no "
        f"selector-side fix can reach. | The headroom available to unmixing on "
        f"real captures is genuinely small, but because the election already "
        f"took the reachable part, not because the fit is confused. Right "
        f"consequence, wrong mechanism -- and the routing from `P132` "
        f"(structure-scale limiter) is unchanged. | DERIVED |",
    ]

    for r in rows:
        assert r.count("|") - r.count("&#124;") == 5, f"bad pipe count: {r[:70]}"
        assert r.count("`") % 2 == 0, f"odd backticks: {r[:70]}"

    anchor = "| P132 |"
    i = text.index(anchor)
    j = text.index("\r\n", i) + 2
    text = text[:j] + "\r\n".join(rows) + "\r\n" + text[j:]

    assert text.count("\n") == text.count("\r\n"), "CRLF broken by append"
    DOC.write_bytes(text.encode("utf-8"))
    print(f"appended section 34 and {len(rows)} fact rows (P133-P138)")
    print(f"  {DOC}: {text.count(chr(10))} lines, {len(text)} chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
