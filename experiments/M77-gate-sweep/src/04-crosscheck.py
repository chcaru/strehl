"""M77 cross-check -- does the Python reimplementation agree with the shipped Rust?

The ROI rule is computed in Python; the sweep is computed by the shipped binary.
If the two disagree about what the ROI contains, the ROI rule is selecting on a
different quantity from the one the invariant then reports.

The CLI prints, for the flat ROI, `reference hp sd : median M DN over N frames
min .. max` (merge_cmd.rs, via flat_ratio::FlatReference). This script recovers
the same three numbers from the saved per-tile scan and compares them.

  contam = hp_sd / (HP_NOISE_GAIN * model_sigma)   =>   hp_sd = contam * gain * sigma

`model_sigma` is level dependent, so the per-frame ROI mean is re-decoded for the
selected tile only -- five ROIs, not four hundred.
"""

import json
import pathlib
import re
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m77  # noqa: E402

REF = re.compile(
    r"reference hp sd : median\s+([0-9.]+) DN over (\d+) frames\s+min\s+([0-9.]+)"
    r" \(frame (\d+)\)\s+max\s+([0-9.]+) \(frame (\d+)\)"
)
TILE = 256
R = m77.HP_BOX_RADIUS


def main():
    m77.banner("M77 cross-check -- Python ROI statistic vs the shipped Rust")
    rois = json.loads((m77.OUT / "01b-rois.json").read_text(encoding="utf-8"))
    rows = []
    for stack in m77.STACKS:
        log = (m77.OUT / f"02b-{stack}.log").read_text(encoding="utf-8")
        m = REF.search(log)
        if not m:
            raise SystemExit(f"{stack}: no reference line")
        cli = {"median": float(m.group(1)), "n": int(m.group(2)),
               "min": float(m.group(3)), "max": float(m.group(5))}
        roi = rois[stack]["flat_roi"]
        iso = rois[stack]["iso"]
        files = m77.stack_files(stack)
        hp = []
        for f in files:
            a = m77.green_luma_plane(f)[roi["y"]:roi["y"] + TILE,
                                        roi["x"]:roi["x"] + TILE]
            resid = (a - m77.box_mean(a, R))[R:-R, R:-R]
            hp.append(float(resid.std()))
        hp = np.array(hp)
        py = {"median": float(np.median(hp)), "min": float(hp.min()),
              "max": float(hp.max()), "n": len(hp)}
        print(f"\n  --- {stack}  ROI x{roi['x']},y{roi['y']}")
        print(f"      {'':10}{'CLI (Rust)':>14}{'M77 (Python)':>16}{'ratio':>12}")
        for k in ("median", "min", "max"):
            print(f"      {k:10}{cli[k]:14.3f}{py[k]:16.3f}"
                  f"{py[k] / cli[k]:12.5f}")
        print(f"      frames    {cli['n']:14d}{py['n']:16d}")
        rows.append({"stack": stack, "cli": cli, "py": py,
                     "ratio_median": py["median"] / cli["median"]})
    r = np.array([x["ratio_median"] for x in rows])
    print(f"\n  median-hp-sd agreement across five stacks: "
          f"{r.min():.5f} .. {r.max():.5f}   (1.00000 = exact)")
    (m77.OUT / "04-crosscheck.json").write_text(json.dumps(rows, indent=2),
                                                encoding="utf-8")
    print("  wrote out/04-crosscheck.json")


if __name__ == "__main__":
    main()
