"""Correct facts 1595, 1598, 1599, 1601, 1602 per V-M111's audit.

These are AMENDMENTS to already-folded facts, not new facts. Two carried outright
factual errors that ORCH introduced while folding M111 verbatim. Each replacement
below was verified at the primary source by ORCH before being applied:

  0.8209 = bee local-d40 moved_frac_of_treated      -> 21-cost.json (real occluding edge)
  0.8541 = planted-disc local-d40 moved_frac        -> 21-cost.json (real non-occluding)
  0.3943 = "occluding (KB=90, two depths)"          -> 22-plant-truth.json (SYNTHETIC)
  1.0    = "CONTROL non-occluding (KB=KF=40, ...)"  -> 22-plant-truth.json (SYNTHETIC)

The 0.394/1.000 pair is the synthetic plant's; ORCH's fold called 0.394 "the real
occluding scene". That is the factual error.
"""
import io
import re as _re

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    text = fh.read()

EDITS = [
    # ---- 1595: the ~49% is M86's, on a different warp. Disclose the splice.
    (
        1595,
        "Independently, a Catmull-Rom gather destroying ~49 % of gradient energy moves "
        "the halo metric by **+0.6 %, positive**: the metric is a median **level** "
        "profile against distance and is not a sharpness proxy at all.",

        "Independently, the metric is **structurally incapable** of scoring sharpness -- "
        "`score_iso` samples image *levels* along edge normals against a far-field "
        "baseline, with no gradient or Laplacian term (fact 1307) -- and consistent with "
        "that, M87's resampling control moved it **+0.6 %, positive** under a Catmull-Rom "
        "similarity warp (`resample_pct` = +0.5792). **ORCH's fold spliced two "
        "measurements here:** the *~49 % of gradient energy* is **M86's** (M86 P23), taken "
        "on a **half-pixel shift of a single frame** -- the worst case -- and is **not** a "
        "measurement of the warp M87 scored; M87's own docstring says that arm *bounds the "
        "interpolator's lowpass rather than reproducing arm A's exact path*. The "
        "conclusion survives; the number was borrowed from a different experiment "
        "(V-M111).",
    ),
    # ---- 1598: FACTUAL ERROR. 0.394 is the synthetic plant's, not real data.
    (
        1598,
        "On a **non-occluding** control the treated-pixel fraction is **1.000 at every "
        "dose**, against **0.394** on the real occluding scene -- **2.5x more aggressive "
        "on a scene containing no occlusion**.",

        "On M87's **synthetic plant**, the non-occluding control's treated-pixel fraction "
        "is **1.000 at every dose** against **0.394** on the plant's **occluding** arm -- "
        "but that 1.000 is **forced by the control's construction**: every treated pixel "
        "elects within **3** frames of `k_F`, so any delta >= 4 moves all of them. "
        "**ORCH's fold called 0.394 'the real occluding scene'. It is the synthetic "
        "plant's, and the error was ORCH's, introduced in the fold (V-M111).** **The "
        "load-bearing version is on real data**, and it is weaker but still adverse: at a "
        "planted non-occluding disc in the bee image the correction moves **85.4 %** of "
        "treated pixels against **82.1 %** at the bee's **real** occluding edge -- "
        "**1.04x**, so it is *no more* selective on a genuine occlusion than on a "
        "silhouette with nothing behind it.",
    ),
    # ---- 1599: mechanism is ARGUED in the source; ORCH folded it as MEASURED.
    (
        1599,
        "**And it is aimed wrong**: near-silhouette background pixels **inherit the "
        "foreground's election**, so the near band targets the frames those pixels "
        "actually elect, while a displaced band mostly **misses** -- it under-treats, "
        "under-blurs, and scores near zero **by construction**.",

        "**And it is aimed wrong -- but this half is ARGUED, and ORCH folded it as "
        "MEASURED.** M87 §3.3 measures only that near-band pixels elect frames closer to "
        "the foreground's (median \\|k_elected - k_F\\| **32** near against **96** far; "
        "elected-value percentile rank 0.675 against 0.429) and **explicitly labels the "
        "causal reading -- that those pixels are *yoked* to the foreground's election -- "
        "ARGUED**. The *consequence* is measured, on the bee: the treatment moves "
        "**82.1 %** of treated pixels, so a complement band could forbid at most "
        "**17.9 %** -- a **4.6x under-treatment**, scoring near zero by construction. But "
        "on the synthetic plant the same comparison **inverts** (complement 60.6 % against "
        "treatment 39.4 %), so **the argument is scene-dependent**: it holds on the shipped "
        "subject, not universally. The count `79` is additionally a per-pixel **upper "
        "bound** -- the band clips wherever `k_F < 39` or `k_F > 259` (V-M111).",
    ),
    # ---- 1601: the 9.4% is over an ROI window, not the whole shipped frame.
    (
        1601,
        "It destroys **9.4 % of the fine band at the damage site** on the shipped frame.",

        "It destroys **9.4 % of the fine band** at the damage window "
        "(`866,1566 x 1050,2150`, 700 x 1100 px) of the shipped full-frame aligned gate-2 "
        "render -- **a window of that render, not the whole frame**, a qualifier ORCH's "
        "fold dropped (V-M111).",
    ),
    # ---- 1602: the arm is live but sign-blind. Extend rather than replace.
    (
        1602,
        "The same guard also caught its owner writing **-141.9 %** where 141.95215 rounds "
        "to **-142.0 %**. |",

        "The same guard also caught its owner writing **-141.9 %** where 141.95215 rounds "
        "to **-142.0 %**. **V-M111 then confirmed the numeric arm is now genuinely live "
        "and found a SECOND defect in it: it is sign-blind.** The comparison is "
        "`abs(abs(stated) - abs(value)) <= tol`, so flipping a source value from "
        "**-141.95** to **+141.95** leaves the guard **GREEN** -- a sign flip is exactly "
        "the defect a control-vs-treatment comparison exists to catch. **An arm that "
        "cannot see sign is inert against the failure it was built for**, which is the "
        "same lesson as the inert arm one sentence earlier, wearing a different disguise. |",
    ),
]

for fid, old, new in EDITS:
    n = text.count(old)
    assert n == 1, "fact %d: anchor found %d times, need exactly 1" % (fid, n)
    # The anchor must actually live on that fact's row.
    row = [l for l in text.split("\n") if l.startswith("| %d |" % fid)]
    assert len(row) == 1, "fact %d: %d rows" % (fid, len(row))
    assert old in row[0], "fact %d: anchor is not on its own row" % fid
    text = text.replace(old, new, 1)

# Post-conditions on every touched row.
for fid, _old, _new in EDITS:
    row = [l for l in text.split("\n") if l.startswith("| %d |" % fid)][0]
    pipes = len(row.replace("\\|", "").split("|")) - 1
    assert pipes == 5, "fact %d now has %d unescaped pipes: %s" % (fid, pipes, row[:120])
    stripped = _re.sub(r"`[^`]*`", "", row)
    assert stripped.count("**") % 2 == 0, "fact %d: odd ** count" % fid
    assert "V-M111" in row, "fact %d: amendment not attributed" % fid

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(text)

print("amended facts: %s" % ", ".join(str(e[0]) for e in EDITS))
