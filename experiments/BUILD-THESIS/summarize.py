"""The final table: does the shipped merge resolve more detail than argmax?

Assembles what was measured into one sheet, and -- the part that matters --
puts every subject number next to the size of the difference the SAME
instrument reports when there is provably no detail difference at all.

The noise null is the yardstick. The two arms differ in noise by 1.06x to
2.68x, and limits.py measured what each statistic reports for that noise
difference alone with zero blur planted. A subject number smaller than its own
noise null is not a detail result; it is the arms' noise, restated in pixels.
"""
import json
import pathlib

import numpy as np

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS")
STATS = ["S1_norm", "S2_f50", "S3_acf"]
FRAMES = {"bee-3-cpl": 299, "bee-1-cpl": 299, "leaf-2-cpl": 182,
          "flowers-cpl": 176, "tweezers-cpl": 100, "flat-on-ruler-cpl": 79}
ORDER = ["bee-3-cpl", "bee-1-cpl", "leaf-2-cpl", "flowers-cpl",
         "tweezers-cpl", "flat-on-ruler-cpl"]


def load(p):
    return json.loads((OUT / p).read_text(encoding="utf8"))


def main():
    meas = {r["subject"]: r for r in load("measure-subjects.json")}
    mins = {r["subject"]: r for r in load("measure-min.json")}
    blur = {r["subject"]: r for r in load("blureq-subjects.json")}
    lim = load("limits.json")

    null = {}
    for r in lim["noise_null"]:
        null.setdefault(r["subject"], []).append(r)
    nullmag = {s: {k: float(np.median([abs(r[k]) for r in v])) for k in STATS}
               for s, v in null.items()}

    shas = {meas[s]["sha256"] for s in meas}
    print("BINARY (both arms, every subject):", ", ".join(shas))
    print("\nINSTRUMENT RESOLUTION (limits.py): planted blur recovered exactly")
    for r in lim["resolution"]:
        print(f"   planted {r['planted']:.2f} px -> " +
              "  ".join(f"{k} {r[k]:+.3f}" for k in STATS))

    print("\n" + "=" * 108)
    print("EQUIVALENT GAUSSIAN BLUR SEPARATING THE ARMS, px."
          "  + = shipped merge finer, - = argmax-baseline finer")
    print(f"{'subject':<20}{'N':>5}{'FOV':>7}{'sig a/m':>9}"
          f"{'S1':>9}{'null':>7}{'S2':>9}{'null':>7}{'S3':>9}{'null':>7}   verdict")
    print("-" * 108)
    rows = []
    for s in ORDER:
        m, b = meas[s], blur[s]
        n = nullmag.get(s, {k: float('nan') for k in STATS})
        vals = {k: float(np.median([t[f"{k}_blur_px"] for t in b["tiles"]])) for k in STATS}
        over = [k for k in STATS if abs(vals[k]) > 1.5 * n[k]]
        if not over:
            verdict = "no detail difference above the noise null"
        elif all(vals[k] > 0 for k in over):
            verdict = "merge finer (" + ",".join(x[:2] for x in over) + ")"
        elif all(vals[k] < 0 for k in over):
            verdict = "argmax finer (" + ",".join(x[:2] for x in over) + ")"
        else:
            verdict = "STATISTICS DISAGREE -- see report"
        print(f"{s:<20}{FRAMES[s]:>5}{m['fov_scale_logged']:>7.4f}"
              f"{m['sigma_ratio_argmax_over_merge']:>9.3f}"
              + "".join(f"{vals[k]:>+9.2f}{n[k]:>7.2f}" for k in STATS)
              + f"   {verdict}")
        rows.append(dict(subject=s, frames=FRAMES[s],
                         fov_scale=m["fov_scale_logged"],
                         sigma_ratio=m["sigma_ratio_argmax_over_merge"],
                         blur_px={k: vals[k] for k in STATS},
                         noise_null_px=n, verdict=verdict))

    print("\n" + "=" * 108)
    print("RATIO FORM, and the same conclusion under a second site rule")
    print(f"{'subject':<20}" + "".join(f"{k + ' mean':>14}{k + ' min':>13}" for k in STATS))
    print("-" * 108)
    for s in ORDER:
        line = f"{s:<20}"
        for k in STATS:
            a = np.median([t[f"{k}_gain"] for t in meas[s]["tiles"]])
            c = np.median([t[f"{k}_gain"] for t in mins[s]["tiles"]])
            line += f"{a:>14.3f}{c:>13.3f}"
        print(line)

    (OUT / "SUMMARY.json").write_text(
        json.dumps(dict(binary_sha256=sorted(shas), subjects=rows,
                        instrument_resolution=lim["resolution"]), indent=1),
        encoding="utf8")
    print(f"\nwrote {OUT / 'SUMMARY.json'}")


if __name__ == "__main__":
    main()
