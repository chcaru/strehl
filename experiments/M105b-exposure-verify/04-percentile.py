"""V6 -- is p99.9 riding a specular tail, and does the choice of percentile matter?

The brief's question: "A specular highlight on chitin is exactly the content
that lives in the top 0.1% of an insect macro, and the owner's subjects are
insects. If a different statistic is better, measure it and say so."

DESIGN. Three stacks, all rendered from ISOLATED COPIES at their FULL capture
depth -- 299, 100 and 105 frames -- i.e. the render the owner would actually
make of each:

    bee-3-cpl    the insect macro the worry is about  (SIGNAL arm)
    foam         no specular, and already correctly exposed  (CONTROL)
    coffee-bean  no specular, already correctly exposed, 1.42% genuinely blown
                 before any exposure is applied           (CONTROL)

    All three rendered `--srgb --exposure 0`, so the tail measured is the
    capture's own and not one this rule created.

DISCLOSED: A FIRST ATTEMPT AT THIS AND WHY IT WAS DISCARDED. The first run
matched all three arms at `--limit 60`, reasoning that equal depth removes a
confound. It does the opposite. `--limit` takes the FIRST n frames in capture
order, not a spread, so 60 of `bee-3-cpl`'s 299 samples only the opening ~20%
of the focus sweep while 60 of `foam`'s 100 samples 60% of it. The arms were
matched in frame COUNT and mismatched in scene COVERAGE, which is the variable
that decides whether an in-focus specular is in the stack at all. It showed:
`p99.99/p99.9` = 1.0051 on the 60-frame bee against 1.1878 on the 299-frame
bee -- a swing produced entirely by my own subsampling. Both numbers are in
`04-percentile.json` (60-frame) and `04-percentile-full.json` (this run), and
the 60-frame file is kept rather than deleted so the discarded arm stays
auditable.

PRE-REGISTERED READING (docs/research/M105b-exposure-ship.md V6, committed at
539ecd7 before any of this ran):

    SUBSTANTIATED  p99.99/p99.9 >= 1.15 on the bee arm AND materially lower on
                   the controls.
    REFUTED        p99.99/p99.9 < 1.15.

THE DECIDING NUMBER, which the bar as written does not capture and which is
added here as a stated extension, not a moved bar: even if the tail IS steep,
it only matters if a different percentile would choose a different exposure.
`p99.9/p99.5` in stops is exactly that sensitivity, because the chosen gain is
`target/percentile` and the stops differ by `log2` of the ratio.

Read-only on D:. Renders from isolated full-depth copies under C:/dev/strehl-out/M105.
"""

import json
import os
import subprocess

import numpy as np
import tifffile

EXE = r"C:\dev\strehl-m105-target\release\strehl.exe"
OUT = r"C:\dev\strehl-out\M105"
LUMA = np.array([0.212_636, 0.715_183, 0.072_192], dtype=np.float64)

ARMS = [
    ("bee-3-cpl", os.path.join(OUT, "isofull-bee-3-cpl"), "SIGNAL"),
    ("foam", os.path.join(OUT, "isofull-foam"), "CONTROL"),
    ("coffee-bean", os.path.join(OUT, "isofull-coffee-bean"), "CONTROL"),
]


def srgb_to_linear(x):
    return np.where(x <= 0.040_45, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def render(name, src):
    tif = os.path.join(OUT, "v6full-%s.tif" % name)
    log = os.path.join(OUT, "v6full-%s.log" % name)
    if os.path.exists(tif):
        return tif
    cmd = [EXE, "stack", src, "--out", tif, "--srgb", "--exposure", "0"]
    with open(log, "wb") as fh:
        subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT)
    return tif


def tail(name, kind, tif):
    a = tifffile.imread(tif)
    lin = srgb_to_linear(a.astype(np.float64) / 65535.0)
    y = (lin * LUMA).sum(axis=2).ravel()
    p99, p995, p999, p9999 = np.percentile(y, [99.0, 99.5, 99.9, 99.99])
    mx = float(y.max())
    return {
        "stack": name,
        "kind": kind,
        "p99_0": float(p99),
        "p99_5": float(p995),
        "p99_9": float(p999),
        "p99_99": float(p9999),
        "max": mx,
        "p9999_over_p999": float(p9999 / p999),
        "max_over_p999": float(mx / p999),
        # The sensitivity that decides whether the statistic matters at all:
        # how many STOPS the chosen exposure moves if the percentile moves.
        "stops_p999_vs_p995": float(np.log2(p999 / p995)),
        "stops_p999_vs_p99": float(np.log2(p999 / p99)),
        "steep_tail": bool(p9999 / p999 >= 1.15),
    }


def main():
    rows = [tail(n, k, render(n, s)) for n, s, k in ARMS]
    sig = [r for r in rows if r["kind"] == "SIGNAL"][0]
    ctl = [r for r in rows if r["kind"] == "CONTROL"]
    worst_ctl = max(r["p9999_over_p999"] for r in ctl)

    verdict = {
        "signal_ratio": sig["p9999_over_p999"],
        "control_ratios": {r["stack"]: r["p9999_over_p999"] for r in ctl},
        "signal_has_steep_tail": sig["steep_tail"],
        "controls_materially_lower": bool(worst_ctl < sig["p9999_over_p999"] - 0.05),
        "max_stops_moved_by_percentile_choice": max(
            abs(r["stops_p999_vs_p995"]) for r in rows
        ),
    }
    if verdict["signal_has_steep_tail"] and verdict["controls_materially_lower"]:
        verdict["V6"] = "SUBSTANTIATED: the bee tail is steep and the controls are not"
    elif verdict["signal_has_steep_tail"]:
        verdict["V6"] = (
            "AMBIGUOUS: the bee tail is steep but the controls are too, so the "
            "steepness is not a property of the specular"
        )
    else:
        verdict["V6"] = "REFUTED: the top 0.1% is flat"

    res = {"arms": rows, "verdict": verdict}
    print(json.dumps(res, indent=2))
    with open(os.path.join(OUT, "04-percentile-full.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)


if __name__ == "__main__":
    main()
