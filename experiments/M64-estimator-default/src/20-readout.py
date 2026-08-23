"""M64's own reading of M62's acceptance JSON, plus the two arms M62's spec
cannot carry because they did not exist when it was written.

Nothing here re-scores anything. It reads `out/10-acceptance-<tag>.json`, which
`10-acceptance.py` wrote, and prints the fields the M64 pre-registration is
graded on -- including the SHA-256 of each arm's output image, which is how
PR4 ("`stack` and `merge` are the same path") is decided.

    python src/20-readout.py [--tag m64]
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import harness as H  # noqa: E402

SQRT30 = math.sqrt(30.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="m64")
    a = ap.parse_args()

    rec = json.loads((H.EVID / f"10-acceptance-{a.tag}.json").read_text(encoding="utf-8"))
    arms = rec["summary"]

    print(f"verdict        : {rec.get('overall')}")
    print(f"reason         : {rec.get('reason')}")
    prov = rec.get("provenance", {})
    print(f"binary sha256  : {prov.get('binary_sha256')}")
    print(f"repo HEAD      : {prov.get('head')}  crates dirty: {prov.get('crates_dirty')}")
    print()
    print(f"{'arm':<24} {'verdict':<10} {'ratio':>10} {'eff':>8} {'n_eff':>8}  out sha256")
    for k, v in arms.items():
        cli = v.get("cli") or {}
        eff = v.get("efficiency")
        print(
            f"{k:<24} {str(v.get('verdict')):<10} "
            f"{v.get('ratio_mean', float('nan')):>10.6f} "
            f"{(eff if eff is not None else float('nan')):>8.4f} "
            f"{cli.get('mean_n_eff', float('nan')):>8.3f}  "
            f"{str(v.get('out_sha256'))[:32]}"
        )

    print()
    print("--- M64 pre-registration readout ---")
    d = arms.get("DEFAULT", {})
    s = arms.get("SELECTOR-shipped", {})
    e = arms.get("ESTIMATOR-explicit", {})
    z = arms.get("SELECTOR-same-binary", {})

    def verdict(ok):
        return "MET" if ok else "NOT MET"

    r = d.get("ratio_mean", float("nan"))
    rel = abs(r - SQRT30) / SQRT30
    print(f"PR1 default within 2% of sqrt(30): {r:.6f}, rel {100*rel:.3f}%  -> {verdict(rel <= 0.02)}")
    eff = d.get("efficiency", float("nan"))
    print(f"PR2 efficiency in [0.98, 1.02]   : {eff:.6f}  -> {verdict(0.98 <= eff <= 1.02)}")
    same_r = s.get("ratio_mean") == d.get("ratio_mean")
    same_sha = s.get("out_sha256") == d.get("out_sha256")
    print(
        f"PR4 `stack` == `merge`           : ratio identical {same_r}, "
        f"output sha256 identical {same_sha}  -> {verdict(same_r and same_sha)}"
    )
    re8 = abs(e.get("ratio_mean", float("nan")) - SQRT30) / SQRT30
    print(
        f"PR5 gate 8 within 0.5%           : {e.get('ratio_mean'):.6f}, "
        f"rel {100*re8:.4f}%  -> {verdict(re8 <= 0.005)}"
    )
    r0 = z.get("ratio_mean", float("nan"))
    print(f"PR6 gate 0 <= 1.05               : {r0:.6f}  -> {verdict(r0 <= 1.05)}")
    lad = {k: v for k, v in arms.items() if k.startswith("A0-ladder")}
    worst = max(
        (abs(v["ratio_mean"] - math.sqrt(v["k"])) / math.sqrt(v["k"]), k)
        for k, v in lad.items()
    )
    b1 = max(abs(arms[n]["ratio_mean"] - 1.0) for n in ("B1a-const-selector", "B1b-random-selector"))
    print(
        f"PR8 instrument calibrated        : worst ladder {100*worst[0]:.4f}% ({worst[1]}), "
        f"worst placebo |1-x| {b1:.6f}  -> {verdict(worst[0] <= 0.01 and b1 <= 0.005)}"
    )
    det = d.get("determinism")
    print(f"    determinism (M62 required)   : {det}")


if __name__ == "__main__":
    main()
