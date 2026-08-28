"""Extract the per-subject, per-band `averaged` fractions from a render log.

WHAT THE NUMBER IS, quoted from the code that prints it
(`crates/strehl-cli/examples/blend-render.rs:571-576`):

    "per level, the fraction of coefficients where NO frame cleared the noise
     floor and the merge therefore averaged instead of selecting. Near 0%
     everywhere would mean the gate is not gating and this is a naive pyramid
     stacker."

So a LOW number means the merge SELECTED, and a high number means it fell back
to averaging. This is the shipping renderer reporting, per subject and per
pyramid level and with no extra instrumentation, which regime the merge was in.

Why that is worth tabulating: fact 1843 measured that selecting rather than
averaging multiplies noise power by 2.16x to 240.70x depending on depth, via
the max-of-N order statistic. This log line therefore says, for free and for
every delivered master, HOW MUCH OF EACH BAND was exposed to that premium.

The log is UTF-16-ish in places (the per-subject header lines are written with
interleaved NULs by the shell that produced it), so bytes are decoded
defensively and NULs stripped rather than assuming an encoding.

Usage:
    python orch_avgband.py <render.log> [--csv out.csv]
"""

import argparse
import re
import sys
from pathlib import Path

HEAD = re.compile(r"\[\s*(\d+)\s*/\s*(\d+)\s*\]\s*(\S+)\s+frames=(\d+)\s+secs=([\d.]+)\s+ok=(\w+)")
AVG = re.compile(r"averaged\s*:\s*([0-9.%\s]+)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--csv")
    args = ap.parse_args()

    raw = Path(args.log).read_bytes()
    text = raw.decode("utf-8", errors="replace").replace("\x00", "")

    rows, cur = [], None
    for line in text.split("\n"):
        line = line.strip()
        m = HEAD.search(line)
        if m:
            cur = {"idx": int(m.group(1)), "subject": m.group(3), "frames": int(m.group(4)),
                   "secs": float(m.group(5)), "ok": m.group(6)}
            continue
        m = AVG.search(line)
        if m and cur is not None:
            vals = [float(v.rstrip("%")) for v in m.group(1).split()]
            cur["bands"] = vals
            rows.append(cur)
            cur = None

    if not rows:
        sys.stderr.write("NO ROWS PARSED -- the log format changed; refusing to report.\n")
        return 2

    nb = max(len(r["bands"]) for r in rows)
    if any(len(r["bands"]) != nb for r in rows):
        sys.stderr.write("BAND COUNT VARIES BETWEEN SUBJECTS; refusing to tabulate.\n")
        return 2

    hdr = ["subject", "N"] + [f"b{i}" for i in range(nb)]
    print(f"{hdr[0]:<40s} {hdr[1]:>4s} " + " ".join(f"{h:>7s}" for h in hdr[2:]))
    print("-" * (46 + 8 * nb))
    for r in sorted(rows, key=lambda r: -r["frames"]):
        print(
            f"{r['subject']:<40s} {r['frames']:>4d} "
            + " ".join(f"{v:7.1f}" for v in r["bands"])
        )

    print()
    print(f"subjects parsed : {len(rows)}")
    # The mid bands are the ones that carry perceived sharpness. Report how many
    # subjects sit essentially entirely in the SELECTING regime there.
    for b in range(1, nb - 1):
        vals = [r["bands"][b] for r in rows]
        n_sel = sum(1 for v in vals if v < 1.0)
        print(
            f"band {b}: averaged fraction min={min(vals):.2f}% max={max(vals):.2f}% "
            f"mean={sum(vals)/len(vals):.2f}%  -- {n_sel}/{len(rows)} subjects below 1%"
        )
    b0 = [r["bands"][0] for r in rows]
    print(f"band 0: min={min(b0):.1f}% max={max(b0):.1f}% mean={sum(b0)/len(b0):.1f}%")

    if args.csv:
        with open(args.csv, "w", encoding="utf-8", newline="") as fh:
            fh.write(",".join(hdr) + "\n")
            for r in sorted(rows, key=lambda r: -r["frames"]):
                fh.write(
                    f"{r['subject']},{r['frames']},"
                    + ",".join(f"{v}" for v in r["bands"])
                    + "\n"
                )
        print(f"csv written     : {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
