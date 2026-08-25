"""O9 -- convert the measured through-focus response into blur, in pixels.

o8 measured amplitude loss per forced frame offset in four bands. If one focus
step is equivalent to a Gaussian blur of sigma px, then amplitude in a band
centred at f cyc/px falls as exp(-2 pi^2 sigma^2 f^2) -- the same closed form
o3c used to convict scipy. Fitting one sigma per offset ACROSS the four bands is
therefore a test as well as a conversion: if the four bands do not agree on a
single sigma, the response is not a defocus blur and the number must not be
quoted as one.

No bar is registered here either. This reads o8's JSON and fits it; it adds no
new data. The residual across bands is printed so the fit can be judged.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from o3_commission import OUTD  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

PLANE_PITCH_UM = 10.2162


def main() -> int:
    d = json.load(open(os.path.join(OUTD, "o8_owner.json"), encoding="utf-8"))
    out = {}
    for nm, roi in d.items():
        print("\n" + "=" * 74)
        print(nm)
        rows = []
        for r in roi["rows"]:
            if r["offset"] == 0:
                continue
            fs, ys = [], []
            for k, v in r["bands"].items():
                lo, hi = (float(x) for x in k.split("-"))
                f = 0.5 * (lo + hi)
                a = 1.0 + v["amp_pct"] / 100.0
                if a <= 0.0:
                    continue
                fs.append(f)
                ys.append(-np.log(a))
            fs, ys = np.asarray(fs), np.asarray(ys)
            x = 2.0 * (np.pi ** 2) * fs * fs
            s2 = float(np.sum(x * ys) / np.sum(x * x))
            sig = float(np.sqrt(max(s2, 0.0)))
            pred = np.exp(-x * s2)
            meas = np.exp(-ys)
            resid = 100.0 * (pred - meas)
            print(f"  offset +{r['offset']}: sigma = {sig:.4f} px   "
                  f"band residuals (model minus measured, amplitude %) "
                  f"{' '.join('%+.2f' % v for v in resid)}")
            rows.append(dict(offset=r["offset"], sigma_px=sig,
                             max_abs_resid_pct=float(np.max(np.abs(resid)))))
        s1 = rows[0]["sigma_px"]
        print(f"  one focus step  = {s1:.4f} px of Gaussian blur on the binned plane")
        print(f"  = {s1 * PLANE_PITCH_UM:.3f} um at the binned pitch of "
              f"{PLANE_PITCH_UM} um")
        r2 = rows[1]["sigma_px"]
        print(f"  quadrature check: two steps should give "
              f"{s1*2:.4f} px if sigma is linear in offset, "
              f"{s1*np.sqrt(2):.4f} px if it adds in quadrature; measured {r2:.4f}")
        out[nm] = dict(rows=rows, one_step_sigma_px=s1,
                       one_step_um=s1 * PLANE_PITCH_UM)

    print("\n" + "=" * 74)
    s = [v["one_step_sigma_px"] for v in out.values()]
    print(f"one focus step across three ROIs: "
          f"{' '.join('%.4f' % x for x in s)} px  "
          f"(mean {np.mean(s):.4f}, spread {max(s)-min(s):.4f})")
    with open(os.path.join(OUTD, "o9_sigma.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=float)
    print(f"wrote {os.path.join(OUTD, 'o9_sigma.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
