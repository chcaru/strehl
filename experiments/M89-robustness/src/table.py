"""Fold the survey JSON lines into the contamination table in the report.

Reads every ``out/survey-*.txt``, pulls the single ``JSON {...}`` line each one
emits, and prints a Markdown table sorted by the primary statistic. Nothing here
computes a number the Rust harness did not already compute: this is formatting,
so that a transcription error cannot become a finding.
"""

import json
import pathlib
import re
import sys

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"


def load(pattern="survey-*.txt"):
    rows = []
    for path in sorted(OUT.glob(pattern)):
        text = path.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^JSON (\{.*\})$", text, re.M)
        if not m:
            continue
        raw = m.group(1)
        # The harness prints Rust's Option<f32> Debug for the ISO; make it JSON.
        raw = re.sub(r"Some\(([-0-9.eE]+)\)", r"\1", raw).replace("None", "null")
        rows.append(json.loads(raw))
    return rows


def main():
    rows = load()
    if not rows:
        sys.exit("no survey JSON found")
    rows.sort(key=lambda r: -r["tail8"])
    ruler = next(r for r in rows if r["stack"].startswith("highly-angled"))
    print(f"{'stack':<38} {'n':>4} {'ISO':>6} {'meanz2':>8} {'>8sig':>10} "
          f"{'x null':>8} {'flag%':>7} {'worstF':>7} {'wF/med':>9} {'p99tile':>8}")
    for r in rows:
        ratio = r["tail8"] / ruler["tail8"] if ruler["tail8"] else float("nan")
        wfm = r["worst_frame_frac"] / r["median_frame_frac"] if r["median_frame_frac"] else float("inf")
        print(f"{r['stack']:<38} {r['n']:>4} {r['iso']:>6.0f} {r['mean_z2']:>8.3f} "
              f"{r['tail8']:>10.3e} {ratio:>8.1f} {100*r['pixels_flagged']:>7.3f} "
              f"{r['worst_frame']:>7} {wfm:>9.1f} {r['p99_tile']:>8.4f}")

    print()
    print("--- matched detail-SNR bins: >8 sigma rate, foam / null ---")
    foam = next(r for r in rows if r["stack"] == "foam")
    edges = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0]
    print(f"{'SNR bin':>12} {'null n':>10} {'null rate':>11} {'foam n':>10} "
          f"{'foam rate':>11} {'ratio':>8}")
    num = den = 0.0
    for k, e in enumerate(edges):
        nn, fn = ruler["n_by_snr"][k], foam["n_by_snr"][k]
        nr, fr = ruler["tail8_by_snr"][k], foam["tail8_by_snr"][k]
        if nn == 0 or fn == 0:
            continue
        w = min(nn, fn)
        num += w * fr
        den += w * nr
        ratio = fr / nr if nr else float("inf")
        print(f"{e:>12.1f} {nn:>10} {nr:>11.3e} {fn:>10} {fr:>11.3e} {ratio:>8.1f}")
    print(f"min(n)-weighted matched ratio: {num/den:.1f}x" if den else "null has no events")


if __name__ == "__main__":
    main()
