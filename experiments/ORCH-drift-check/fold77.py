"""Fold the then-vs-now measurement. Facts 1425-1426, discipline 708."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1425, "**AGAINST THE ARTEFACTS THE OWNER ACTUALLY JUDGED, THE RENDER HAS CHANGED ENORMOUSLY -- WHICH IS "
           "THE OTHER HALF OF FACT 1424 AND MUST BE READ WITH IT.** The judged files are "
           "`C:\\dev\\strehl-out\\bee3-full.png` and siblings, written **2026-08-23 23:37-23:47**, and "
           "M105b measured them to carry **five defects at once**: binned to half linear resolution, no "
           "alignment, no colour management, underexposed, plus the merge defects. Measured directly this "
           "session: `bee3-full.tif` is **3516x2344 = 8.24 MP**; HEAD `d42fac4` renders the same stack at "
           "**7032x4688 = 32.97 MP**, a ratio of **4.00x** confirmed by pixel count rather than file size. "
           "Four of the five are fixed -- resolution `56bd846`, alignment `885e9f7`, colour `e59f1b0`, "
           "exposure `925d03d`.",
     "**Fact 1424's 'the render has not moved one byte tonight' is true against the 10:46 freeze and "
     "misleading if read as 'no progress since the complaint'.** Both are needed: nothing has moved since "
     "10:46, and a great deal moved between 23:37 and 07:45. **The owner's verdict was against a render that "
     "no longer exists**, and it would be a serious error -- of the exact class M105b made and retracted "
     "(fact 1344) -- to keep attributing softness work to a complaint about a different image. Any future "
     "quality claim must name **which render** it is measured against.",
     "ORCH `then_vs_now.py`, R1/R2/R3 registered and passed (MEASURED); M105b fact 1344 (MEASURED)"),

    (1426, "**THE EXPOSURE-MATCHED CONTROL SHOWS THE GAIN IS NOT MERELY BRIGHTNESS, AND THE WAXY-BLOB "
           "ARTEFACT IS PRESENT IN ALL THREE PANELS.** Applying the new render's exact `+1.54` stops "
           "(**2.9079x**, in linear light before the transfer curve) to the old pixels holds brightness "
           "equal, and the residual difference -- hair separation, specular structure along individual "
           "hairs, colour -- remains plainly visible. **But the smooth, plasticky patches are in the judged "
           "render, in its exposure-matched control, and in HEAD alike.**",
     "**Independent confirmation of M103's finding (`10131c2`) that the waxy blobs predate the gain "
     "correction, from a different instrument on a different pair of images.** It also holds the honest "
     "line: brightness is a display change and fully recoverable, so it must never be sold as a quality "
     "gain (M105b's warning against conflating its correction with the unrecoverable SNR of "
     "`captures-needed.md` §22). **The montage's argument is panel 2 against panel 3, not panel 1 against "
     "panel 3.** Registration was deliberately integer-only and the old panel upscaled with NEAREST, "
     "because a smooth kernel would have added blur the old data never had and flattered the new render.",
     "ORCH `then_vs_now.py` exposure-matched control (MEASURED); corroborates M103 `10131c2`"),
]

DISCIPLINES = [
    (708, "**A before/after montage is an argument, so build the control that removes its cheapest "
          "explanation.** Most of the visible difference between the judged render and HEAD is brightness, "
          "and brightness is free -- a third panel applying the new exposure to the old pixels costs "
          "nothing and converts the montage from a flattering comparison into a measurement. Likewise: "
          "upscale the *older, worse* image with NEAREST rather than a smooth kernel, and register with "
          "**integer** offsets only, or the presentation itself blurs the quantity being compared. Facts "
          "1425, 1426."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1424 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^707\. ", l))
    assert disc_idx > fact_idx, "discipline list must follow the fact table"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        r = f"| {fid} | {claim} | {interp} | {src} |"
        n = r.count("|") - r.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes"
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
    print("folded facts 1425-1426, discipline 708")


if __name__ == "__main__":
    main()
