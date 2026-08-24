"""Retract fact 1436's headline. Its author refuted it with their own placebo.

I folded -33.0% about an hour ago, with M104c's caveat attached. The caveat was
the whole story: the pre-registered flat-ROI placebo, run after publication,
showed the flat ROI dropping 30.3% against the detail ROI's 33.0% -- ratio 0.92,
which is branch (a) of the rule M104c registered BEFORE seeing the number, i.e.
noise-dominated.

Annotated in place rather than deleted, per the corpus's practice, so a reader
arriving from a citation sees the correction.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

RETRACTION = (
    " **>>> HEADLINE RETRACTED BY ITS OWN AUTHOR'S PRE-REGISTERED PLACEBO, ~1 HOUR AFTER THIS ROW WAS "
    "FOLDED. The -33.0% is NOT a sharpness confound: ~92% of it is interpolation smoothing NOISE.** The "
    "flat ROI -- almost pure sensor noise, with no detail to lose -- dropped **-30.3%** against the "
    "detail ROI's -33.0%, ratio **0.92**, which is branch (a) of the rule M104c registered before seeing "
    "the number. **Corrected, noise-normalised: the resample+FOV cost is -3.88%, registration buys back "
    "+6.88%, and the estimator is +2.73% NET AHEAD of an unregistered render rather than handicapped.** "
    "The interpretation in this row -- \"the estimator carries a net resampling penalty its control never "
    "pays\" -- is therefore **wrong and reversed in sign**. See fact 1439. The `STREHL_ALIGN=zoom` "
    "sidecar-pollution defect and the refuted A0 identity-warp prediction in this row both stand. <<<"
)

FACTS = [
    (1439,
     "**RAW HIGH-BAND ENERGY IS A NOISE METRIC AT THIS RIG'S MAGNIFICATION, NOT A SHARPNESS METRIC: THE "
     "FLAT TILE CARRIES MORE OF IT THAN THE DETAIL TILE.** On `coffee-bean --limit 8 --demosaic`, the "
     "high-band energy fraction is **0.000487 on the flattest tile against 0.000289 on the "
     "highest-variance tile** -- the region with no subject detail scores **1.69x higher** than the "
     "region with it. Consequence, measured: an alignment comparison scored this way reported "
     "**-33.0%** on a detail ROI and **-30.3%** on a flat ROI, ratio **0.92**. Noise-normalising by the "
     "flat ROI gives resample+FOV cost **-3.88%**, registration gain **+6.88%**, **net +2.73% in the "
     "estimator's favour**.",
     "**\"Softer\" can mean \"cleaner\", and this metric cannot tell you which** -- so any sharpness "
     "claim in this corpus scored on raw high-band energy without a flat-ROI placebo is substantially "
     "reporting noise suppression. The mechanism is the rig: fact 12 measured MTF@Nyquist at 0.036 at "
     "f/5.6 and 0.000 beyond at m=2.0, so **diffraction has already removed most true high-frequency "
     "signal and what remains in the band is mostly sensor noise.** M104c raised this as a HIGH defect "
     "and pointedly did **not** assert that M95's 59% figure is affected, having not read its method -- "
     "the claim is that it is the same metric family and the failure is **invisible without a placebo**. "
     "Two bounds on this correction itself: the \"flat\" ROI was the flattest of nine tiles (variance "
     "4.4e6), **not a true flat field**, so if it retains structure the normalisation over-corrects and "
     "true detail loss lies somewhere in **[-3.88%, -33%]**; and it is one stack, 8 frames, ~0.08 px "
     "inter-frame drift, so **+2.73% net is a floor** -- on a high-drift bracket (232.7 px on "
     "`bee-3-cpl`) registration should gain far more while resampling costs the same. A slanted-edge MTF "
     "on `flat-on-ruler-cpl` does not have this failure mode and was not built.",
     "M104c-verify, flat-ROI placebo with its interpretation rule pre-registered before the number was "
     "seen (MEASURED)"),
]

DISCIPLINES = [
    (720,
     "**A placebo that is pre-registered but not yet run does not protect anything -- run it BEFORE the "
     "headline, not after.** M104c had the flat-ROI placebo registered in their design table when they "
     "published -33.0% with a caveat. Running it cost **one command**, inverted the conclusion, and "
     "moved the number by ~8x. The caveat was not a footnote, it was the finding. **If a control is "
     "cheap enough to be worth registering, it is cheap enough to run before you report the thing it "
     "controls for.** Facts 1436, 1439."),
    (721,
     "**Before trusting any energy-in-a-band metric, measure the band on a region with NO signal in it.** "
     "The decisive datum was that the flat tile scored **1.69x higher** than the detail tile -- once seen, "
     "the metric's meaning is obvious and no further argument is needed. This generalises past sharpness: "
     "for any ratio metric, evaluate it where the numerator's subject is known absent and check that it "
     "reads small. If it does not, the metric is measuring something else. Fact 1439."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    m = re.search(r"^\| 1436 \|.*$", text, re.M)
    assert m, "fact 1436 row not found"
    row = m.group(0)
    assert "HEADLINE RETRACTED" not in row, "already annotated"
    cells = re.split(r"(?<!\\)\|", row)
    assert len(cells) == 6, f"fact 1436 has {len(cells)-2} cells, expected 4"
    assert "|".join(cells) == row, "split/join does not round-trip"
    cells[2] = cells[2].rstrip() + RETRACTION + " "
    newrow = "|".join(cells)
    k = newrow.count("|") - newrow.count("\\|")
    assert k == 5, f"annotated 1436 has {k} unescaped pipes"
    text = text[:m.start()] + newrow + text[m.end():]
    print("annotated fact 1436 with its author's own retraction")

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1438 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^719\. ", l))
    assert disc_idx > fact_idx

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        r = f"| {fid} | {claim} | {interp} | {src} |"
        k = r.count("|") - r.count("\\|")
        assert k == 5, f"fact {fid}: {k} unescaped pipes"
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
        rows.append(r)
    drows = []
    for did, body in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"
        drows.append(f"{did}. {body}")

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print("folded fact 1439, disciplines 720-721")


if __name__ == "__main__":
    main()
