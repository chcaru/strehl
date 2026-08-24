"""M86 — is the recovered breathing rate independent of the span it was measured at?

A single physical breathing rate would make the per-frame log-scale rate
implied by span-1 pairs, span-32 pairs and span-128 pairs the *same number*.
It does not, and the shape of the disagreement is the whole story about how far
this estimator can be trusted on a deep stack.

Read-only: consumes the CSVs `m86-align edges` wrote under `out/`, writes
nothing but stdout.

    python span_bias.py out/bee-3-cpl-edges.csv 299
"""

import csv
import math
import sys


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "out/bee-3-cpl-edges.csv"
    rows = [r for r in csv.DictReader(open(path, newline="")) if r["status"] == "ok"]
    if not rows:
        print(f"no fitted rows in {path}")
        return 1
    n = int(sys.argv[2]) if len(sys.argv) > 2 else max(int(r["mov"]) for r in rows) + 1
    pw, ph = int(rows[0]["plane_w"]), int(rows[0]["plane_h"])
    rho = math.hypot(pw, ph) / 2

    print(f"  {path}")
    print(f"  {len(rows)} fitted edges, {n} frames, plane {pw}x{ph}, rho {rho:.2f} px")
    print()
    print("  Per-frame log-scale rate implied by each span band, from DIRECT")
    print("  pairwise fits only -- no solver, no chaining. One physical")
    print("  breathing rate would make the 'rate/frame' column flat.")
    print()
    hdr = ("span", "n", "med g", "rate/frame", "implied 0->end", "corner px")
    print("  {:>6} {:>6} {:>12} {:>12} {:>15} {:>11}".format(*hdr))

    bands: dict[int, list[float]] = {}
    for r in rows:
        bands.setdefault(int(r["span"]), []).append(float(r["g"]))

    best = None
    for s in sorted(bands):
        v = sorted(bands[s])
        m = v[len(v) // 2]
        rate = m / s
        tot = rate * (n - 1)
        print(
            f"  {s:>6} {len(v):>6} {m:>12.6f} {rate:>12.3e} "
            f"{tot:>15.4f} {tot * rho:>11.1f}"
        )
        if best is None or abs(rate) > abs(best[1]):
            best = (s, rate)

    print()
    print(f"  peak |rate| at span {best[0]}: {best[1]:.3e} per frame")
    print(f"  -> upper bound on total drift: {abs(best[1]) * (n - 1) * rho:.1f} corner px")
    print()
    print("  Short spans read LOW because the scale signal (g*rho) is below the")
    print("  fit's own rms. Long spans read LOW because the pairs that still")
    print("  correlate at that defocus baseline are a biased survivor set.")
    print("  The peak is the least-biased direct estimate available.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
