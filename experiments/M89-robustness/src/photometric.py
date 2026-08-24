"""Separate photometric disagreement from the rest, per stack.

Two independent measurements meet here.

* ``survey`` measures ``mean z^2``: the fourth difference of each *pixel*, in
  sigmas of the calibrated noise model.
* ``levels`` measures ``d4_rms``: the fourth difference of each *frame's global
  mean level*, as a fraction. It touches no pixel statistic, no noise model and
  no strata.

Write frame ``f``'s level at a pixel as ``L_f = a_f * S`` for a static scene
under a fluctuating illumination ``a_f``. A residual kernel with ``sum r = 0``
annihilates ``S`` and leaves ``S * sum(r_j a_j)``. Dividing by the predicted
variance ``sum(r^2) * (g*S + rn^2)`` gives, per pixel,

    E[z^2] = 1 + S^2 * d4^2 / (sum(r^2) * (g*S + rn^2))

so averaging over pixels needs only the mean level, which ``levels`` reports.
That prediction is made from the frame means alone. Whatever it does not
account for is disagreement that is *not* a global illumination change: it is
spatially structured, which is what motion is.

The arithmetic is here rather than in prose because a load-bearing number
should be reproducible by running a file, not by trusting a paragraph.
"""

import json
import pathlib
import re
import sys

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"

# sum(r_j^2) for the primary operator w=5 p=2, whose residual kernel is the
# fourth difference [1, -4, 6, -4, 1] / 6:  (1 + 16 + 36 + 16 + 1) / 36.
R2_SUM = 70.0 / 36.0

# The noise model's affine coefficients are not restated here. The harness
# prints the ones it extracted from strehl_core::noise in each survey header,
# and this file parses that line, so a transcription cannot silently rescale a
# prediction.
MODEL_RE = re.compile(r"var\(L\) = ([0-9.eE+-]+)\*L \+ ([0-9.eE+-]+)")


def read_json(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^JSON (\{.*\})$", text, re.M)
    if not m:
        return None
    raw = re.sub(r"Some\(([-0-9.eE]+)\)", r"\1", m.group(1)).replace("None", "null")
    out = json.loads(raw)
    mm = MODEL_RE.search(text)
    if mm:
        out["_g"] = float(mm.group(1))
        out["_rn2"] = float(mm.group(2))
    return out


def main():
    surveys = {}
    for p in OUT.glob("survey-*.txt"):
        j = read_json(p)
        if j:
            surveys[j["stack"]] = j
    levels = {}
    for p in OUT.glob("levels-*.txt"):
        j = read_json(p)
        if j:
            levels[j["stack"]] = j

    rows = []
    for name, s in surveys.items():
        lv = levels.get(name)
        if lv is None:
            continue
        iso = int(round(s["iso"]))
        if "_g" not in s:
            print(f"  (skipping {name}: survey header carried no model line)")
            continue
        g, rn2 = s["_g"], s["_rn2"]
        big_s = lv["mean_level"]
        d4 = lv["d4_rms"]
        excess = big_s * big_s * d4 * d4 / (R2_SUM * (g * big_s + rn2))
        pred = 1.0 + excess
        meas = s["mean_z2"]
        share = excess / (meas - 1.0) if meas > 1.0 else float("nan")
        rows.append((name, s["n"], iso, lv["pp"], d4, meas, pred, share))

    rows.sort(key=lambda r: -(r[5] - 1.0))
    print(f"{'stack':<38} {'n':>4} {'ISO':>5} {'p-p%':>7} {'d4 rms':>9} "
          f"{'meas z2':>8} {'photo z2':>9} {'photo share':>12}")
    for name, n, iso, pp, d4, meas, pred, share in rows:
        sh = "n/a" if share != share else f"{100*share:>10.1f}%"
        print(f"{name:<38} {n:>4} {iso:>5} {100*pp:>7.2f} {d4:>9.2e} "
              f"{meas:>8.3f} {pred:>9.3f} {sh:>12}")

    print()
    print("Residual (measured minus photometric prediction), the part a global")
    print("illumination change cannot explain:")
    for name, n, iso, pp, d4, meas, pred, share in rows:
        print(f"  {name:<38} {meas - pred:>8.3f}")


if __name__ == "__main__":
    main()
