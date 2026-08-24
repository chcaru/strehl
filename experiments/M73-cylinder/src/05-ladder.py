"""M73 step 05 — the gate ladder, EXPLORATORY and post-hoc.

Added after the pre-registration was committed at 700f87b. No registered decision
reads it, and it draws no threshold conclusion: it exists because the shipped
gate turned out to admit 1.24 and 1.77 frames of 130 and 120, and a report that
merely asserted "the gate is nearly inert here" would be asserting rather than
showing. The curve says what the gate does as it opens, and where on it M67's
plant regime (`n_eff/N` = 0.2736) actually sits for this subject.

Choosing an operating gate from this curve would be exactly the circularity the
pre-registration forbids. The whole curve is reported; no point on it is picked.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
SEED = 0x5CA1AB1E

spec = importlib.util.spec_from_file_location("score03", ROOT / "src" / "03-score.py")
s3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s3)


def main() -> int:
    rng = np.random.default_rng(SEED)
    out: dict = {}
    for tag, stack in (("s1", "wrapped-text-1"), ("s2", "wrapped-text-2")):
        prefix = OUT / tag
        hdr = json.loads(prefix.with_suffix(".json").read_text(encoding="utf-8"))
        h, w, k = hdr["height"], hdr["width"], hdr["frames"]
        rows = np.arange(s3.MARGIN, h - s3.MARGIN)
        cols = np.arange(s3.MARGIN, w - s3.MARGIN)
        sub = np.ix_(rows, cols)

        def rd(name: str) -> np.ndarray:
            return np.fromfile(prefix.with_suffix(f".{name}.bin"), dtype=np.uint16).reshape(h, w)

        win_e = rd("win_E").astype(np.float64)
        ref = s3.column_line_fit(win_e[:, cols], rows)
        exact = float((np.abs(win_e[sub] - ref) < 0.5).mean())

        print(f"\n{'=' * 78}\n{stack}: K = {k}   election exact-index {100.0 * exact:.2f}%")
        print(f"{'=' * 78}")
        print("gate   n_eff    n_eff/N   H_rep     null    margin    span_mean  lift_pp")
        rows_out = []
        for t in hdr["gate_ladder"]:
            g = int(t)
            lo = rd(f"lo_g{g}")[sub].astype(np.float64)
            hi = rd(f"hi_g{g}")[sub].astype(np.float64)
            n = rd(f"nadm_g{g}")[sub].astype(np.float64)
            span = hi - lo + 1.0
            hr = float(((lo - 0.5 <= ref) & (ref <= hi + 0.5)).mean())
            start = rng.random(span.shape) * (k - span)
            hn = float(((start - 0.5 <= ref) & (ref <= start + span - 0.5)).mean())
            ne = float(n.mean())
            print(f"{g:>4}  {ne:8.4f}  {ne / k:8.5f}  {100 * hr:7.3f}%  {100 * hn:6.3f}%  "
                  f"{100 * (hr - hn):+7.3f}pp  {float(span.mean()):8.3f}  "
                  f"{100 * (hr - exact):+6.2f}")
            rows_out.append({
                "gate": g, "n_eff": ne, "n_eff_over_N": ne / k, "H_rep": hr,
                "H_null": hn, "margin_pp": 100 * (hr - hn),
                "span_mean": float(span.mean()), "lift_pp": 100 * (hr - exact),
            })
        out[stack] = {"K": k, "exact_index_E": exact, "ladder": rows_out}
        print("\nM67's plant sat at n_eff/N = 0.2736 with H(E) = 99.955% against a")
        print("shape-matched null of 32.36%. On this subject that n_eff/N is reached")
        print("only near gate 64, sixteen times the shipped DEFAULT_GATE of 4.0.")

    (OUT / "05-ladder.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nwrote", OUT / "05-ladder.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
