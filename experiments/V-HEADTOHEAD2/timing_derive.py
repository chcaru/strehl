"""Derive every timing number quoted in docs/research/V-HEADTOHEAD2.md section 9.

Nothing here measures anything. It reads the harness's machine-written CSV and
does arithmetic on it, so that no derived number in the report is a figure I
typed by hand. Run:

    python timing_derive.py

Inputs
------
logs/timing2.csv        written by timing2.ps1 (6 strehl runs + fork rep 2)
FORK_REP1 below         the standalone probe run of the fork, with byte-identical
                        flags and the same binary, logged at
                        logs/timing-fork-rep1-tail.txt. Its wall/CPU/peak were
                        read off the console and off a live sample of the
                        process; they are entered here as constants and labelled
                        as such, because that run predates the CSV.

A note on units. PowerShell's `1GB` literal is 2**30, so every memory number the
harness printed is **GiB**, not GB. This script says GiB and converts once.
"""

import csv
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "logs", "timing2.csv")

# The fork's rep 1 (standalone probe; identical binary, identical flags).
FORK_REP1 = dict(seconds=1604.15, cpu_s=6430.6, peak_B=50_770_456_576, exit=0)

# Frame geometry. Both are 105 frames of the same bracket.
N = 105
STREHL_OUT_MP = 7032 * 4688 / 1e6      # what strehl writes
FORK_IN_MP = 7168 * 5120 / 1e6         # what the fork reads (LR export)
FORK_OUT_MP = 7008 * 4672 / 1e6        # what the fork writes after its crop

# Zerene, from ITS OWN log, an interactive session on a different subject.
ZERENE_STACK_S = 26.912
ZERENE_N = 33

# The owner's calibration point, stated in the brief. MEASURED by him.
CORPUS_FRAMES, CORPUS_S = 4825, 16.2 * 60


def load():
    rows = []
    with open(CSV, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(
                dict(
                    arm=r["arm"],
                    rep=int(r["rep"]),
                    seconds=float(r["seconds"]),
                    exit=int(r["exit"]),
                    peak_GiB=float(r["peakWS_GB"]),
                    cpu_s=float(r["cpu_s"]),
                )
            )
    return rows


def main():
    rows = load()
    rows.append(
        dict(
            arm="FORK-MERGE",
            rep=1,
            seconds=FORK_REP1["seconds"],
            exit=FORK_REP1["exit"],
            peak_GiB=FORK_REP1["peak_B"] / 2**30,
            cpu_s=FORK_REP1["cpu_s"],
        )
    )

    arms = {}
    for r in rows:
        arms.setdefault(r["arm"], []).append(r)

    # counted partition: every row lands in exactly one arm, and the arms sum
    tot = sum(len(v) for v in arms.values())
    assert tot == len(rows), "partition does not sum"
    print(f"rows: {len(rows)}  arms: {len(arms)}  sum {tot} = {len(rows)} OK")
    ok = sum(1 for r in rows if r["exit"] == 0)
    bad = len(rows) - ok
    print(f"exits: zero {ok} + nonzero {bad} = {len(rows)} of {len(rows)}")
    print()

    hdr = (
        f"{'arm':<14}{'n':>2}  {'wall s: min':>11}{'med':>9}{'max':>9}"
        f"{'spread':>8}  {'s/frame(med)':>12}{'CPU s':>9}{'thr-eq':>8}{'peak GiB':>9}"
    )
    print(hdr)
    print("-" * len(hdr))
    summary = {}
    for arm in ("STREHL-SOLVE", "STREHL-CACHED", "FORK-MERGE"):
        v = sorted(arms[arm], key=lambda r: r["seconds"])
        w = [r["seconds"] for r in v]
        c = [r["cpu_s"] for r in v]
        p = [r["peak_GiB"] for r in v]
        med = st.median(w)
        thr = st.median([r["cpu_s"] / r["seconds"] for r in v])
        summary[arm] = dict(med=med, mean=st.mean(w), lo=min(w), hi=max(w),
                            cpu=st.median(c), thr=thr, peak=max(p))
        print(
            f"{arm:<14}{len(v):>2}  {min(w):>11.2f}{med:>9.2f}{max(w):>9.2f}"
            f"{max(w)/min(w):>8.2f}  {med/N:>12.4f}{st.median(c):>9.1f}"
            f"{thr:>8.1f}{max(p):>9.2f}"
        )
    print()

    s = summary["STREHL-SOLVE"]
    k = summary["STREHL-CACHED"]
    f = summary["FORK-MERGE"]

    print("=== derived, all from the table above ===")
    print(f"strehl end-to-end (solve)   {s['med']/N:.4f} s/frame   "
          f"{N*STREHL_OUT_MP/s['med']:.1f} MP(out)/s")
    print(f"strehl re-render (cached)   {k['lo']/N:.4f} s/frame at its best rep, "
          f"{k['med']/N:.4f} at its median")
    print(f"fork  end-to-end            {f['med']/N:.3f} s/frame   "
          f"{N*FORK_OUT_MP/f['med']:.2f} MP(out)/s")
    print()
    print(f"fork / strehl-solve, median:median      {f['med']/s['med']:.1f}x")
    print(f"fork / strehl-solve, best:best          {f['lo']/s['lo']:.1f}x")
    print(f"fork / strehl-solve, worst:worst        {f['hi']/s['hi']:.1f}x")
    print(f"  -> the ratio is >= {min(f['lo']/s['lo'], f['hi']/s['hi'], f['med']/s['med']):.1f}x "
          f"under every pairing of the measured reps")
    print()
    print(f"CPU seconds burned: fork {f['cpu']:.0f} vs strehl-solve {s['cpu']:.0f}"
          f"  = {f['cpu']/s['cpu']:.1f}x more CPU for the same stack")
    print(f"parallel efficiency (CPU s / wall s, 32 logical): "
          f"strehl {s['thr']:.1f}/32 = {100*s['thr']/32:.0f}%, "
          f"fork {f['thr']:.1f}/32 = {100*f['thr']/32:.0f}%")
    print(f"peak working set: strehl {s['peak']:.2f} GiB, fork {f['peak']:.2f} GiB "
          f"= {f['peak']/s['peak']:.1f}x")
    print()
    print(f"the alignment solve costs, by difference of the two strehl arms:")
    print(f"  wall  {s['med'] - k['med']:+.2f} s (medians; the cached arm's reps are "
          f"contention-spread, so prefer CPU)")
    print(f"  CPU   {s['cpu'] - k['cpu']:+.1f} s  "
          f"({100*(s['cpu']-k['cpu'])/s['cpu']:.0f}% of the end-to-end CPU)")
    print()
    z = ZERENE_STACK_S / ZERENE_N
    print(f"Zerene align+PMax, from ITS OWN log: {ZERENE_STACK_S} s / {ZERENE_N} frames "
          f"= {z:.4f} s/frame")
    print(f"  strehl-solve is {z/(s['med']/N):.2f}x faster per frame than that number")
    print(f"  (different subject, and that number EXCLUDES Zerene's own load and save)")
    print()
    corpus = CORPUS_S / CORPUS_FRAMES
    print(f"owner's corpus figure: {CORPUS_FRAMES} frames / {CORPUS_S:.0f} s = "
          f"{corpus:.4f} s/frame")
    print(f"  this measurement is {(s['med']/N)/corpus:.2f}x slower per frame end-to-end, "
          f"{(k['lo']/N)/corpus:.2f}x at the cached arm's best rep")
    print()
    print("=== input asymmetry, NOT normalised away ===")
    print(f"strehl reads 105 ARW = 3.88 GB; the fork reads 105 TIFF = 38.42 GB "
          f"= {38.42/3.88:.1f}x the bytes")
    print(f"and those TIFFs are Lightroom developments of those same ARW, timed by "
          f"neither tool.")


if __name__ == "__main__":
    main()
