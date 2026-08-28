# -*- coding: utf-8 -*-
"""V-DILUTE probe: what is actually in V-NEVERWORSE's bundle for 112MSDCF?

Read-only. I inherit their gauge rather than building a rival one, so the
240.70x baseline I must beat is measured by the same instrument that produced
it. This only reports geometry and the through-focus curve.
"""
import io
import json
import os
import sys

import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")

BUNDLE = r"C:\dev\strehl-out\V-NEVERWORSE\bundle"


def main():
    subj = sys.argv[1] if len(sys.argv) > 1 else "112MSDCF"
    z = np.load(os.path.join(BUNDLE, "%s.npz" % subj))
    meta = json.load(io.open(os.path.join(BUNDLE, "%s.json" % subj),
                             encoding="utf-8"))
    ok = {r["frame"] for r in meta["rows"] if r["state"] == "OK"}
    keys = [k for k in sorted(z.files)
            if k.startswith("b") and k != "bw" and int(k[1:]) in ok]
    print("subject      : %s" % subj)
    print("npz members  : %d   OK frames: %d" % (len(z.files), len(keys)))
    a = z[keys[0]]
    print("frame shape  : %s   dtype %s" % (a.shape, a.dtype))
    print("meta keys    : %s" % sorted(meta.keys()))
    if "rows" in meta and meta["rows"]:
        print("row[0]       : %s" % json.dumps(meta["rows"][0])[:220])
    states = {}
    for r in meta["rows"]:
        states[r["state"]] = states.get(r["state"], 0) + 1
    print("states       : %s" % states)

    # Through-focus curve: is focus SMOOTH in frame index? My proposed design
    # depends on it, so it must be measured, not assumed.
    print("\nthrough-focus curve (global sharpness vs frame index):")
    sh = []
    for k in keys:
        g = z[k][:, :, 1].astype(np.float64)
        lap = (g[1:-1, 1:-1] * 4.0 - g[:-2, 1:-1] - g[2:, 1:-1]
               - g[1:-1, :-2] - g[1:-1, 2:])
        sh.append(float((lap ** 2).mean()))
    sh = np.array(sh)
    shn = sh / sh.max()
    for i in range(0, len(shn), max(1, len(shn) // 24)):
        bar = "#" * int(round(shn[i] * 50))
        print("  f%-4d %.4f %s" % (i, shn[i], bar))
    d1 = np.abs(np.diff(shn))
    print("\n  peak at frame %d of %d" % (int(np.argmax(shn)), len(shn)))
    print("  mean |delta| between adjacent frames : %.5f" % d1.mean())
    print("  max  |delta| between adjacent frames : %.5f" % d1.max())
    print("  SMOOTHNESS: adjacent-frame change is %.1f%% of full range"
          % (100.0 * d1.mean() / (shn.max() - shn.min())))


if __name__ == "__main__":
    main()
