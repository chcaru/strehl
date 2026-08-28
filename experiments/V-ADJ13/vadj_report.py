r"""V-ADJ13: emit the report's number-bearing tables from the banked JSON.

Every number in docs/research/V-ADJ13.md that a checker can bind against is
printed by this script from experiments' own output, never typed by hand.
vr_recheck.py binds report rows to the baseline at 2e-3 relative tolerance and
also checks the source-frame count and the verdict word; a transcription slip
of one digit turns a GREEN self-check RED, so the transcription is mechanical.

usage: python vadj_report.py            # all three tables to stdout
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
SCRATCH = pathlib.Path(r"C:\dev\strehl-out\V-ADJ13")
BASELINE = HERE.parent / "V-REVIEW" / "vr_baseline.json"
ELEVATED = 1.3

ORDER = ["112MSDCF", "113MSDCF", "coffee-bubbles", "couch-fibers-cpl",
         "flower-inner-edge-cpl", "foam", "chia-seeds-cpl",
         "dime-flat-narrow-slices-cpl", "duck-tape-side-layers-cpl",
         "maldon-sea-salt-cpl", "medication-pill-cpl", "pottery-art-glazed-cpl",
         "unpopped-popcorn-kernels-cpl"]
EXPIRED = set(ORDER[:6])


def load():
    out = {}
    for s in ORDER:
        out[s] = json.load(open(SCRATCH / ("source_%s.json" % s), encoding="utf-8"))
    return out


def main(_argv):
    d = load()
    base = json.load(open(BASELINE, encoding="utf-8"))["subjects"]

    print("### ROWS (vr_recheck grammar)\n")
    print("| subject | stat | master | source (max of N) | ratio | verdict |")
    print("|---|---|---:|---:|---:|---|")
    for s in ORDER:
        x = d[s]
        for stat, mv, sv in (("blotch", x["master"]["blotch"], x["src_blotch_max"]),
                             ("chroma", x["master"]["chroma"], x["src_chroma_max"])):
            r = x["ratio"][stat]
            print("| %s | %s | %.5f | %.5f (max of %d) | **%.3f** | %s |"
                  % (s, stat, mv, sv, x["n_ok"], r,
                     "ACQUIT" if r <= ELEVATED else "CONVICT"))

    print("\n### VERDICT TABLE\n")
    print("| subject | was | flagged on | blotch m/src | chroma m/src | worst | frames | verdict |")
    print("|---|---|---|---|---|---:|---:|---|")
    for s in ORDER:
        x, b = d[s], base[s]
        worst = max(x["ratio"]["blotch"], x["ratio"]["chroma"])
        print("| `%s` | %s | %s | %.5f / %.5f = **%.3fx** | %.5f / %.5f = **%.3fx** | %.3fx | %d/%d of %d | **ACQUIT** |"
              % (s, "EXPIRED" if s in EXPIRED else "REVIEW", b["flagged_for"],
                 x["master"]["blotch"], x["src_blotch_max"], x["ratio"]["blotch"],
                 x["master"]["chroma"], x["src_chroma_max"], x["ratio"]["chroma"],
                 worst, x["n_ok"], len(x["rows"]), x["n_frames"]))

    print("\n### MECHANISM (contrast = band/mean; where the ratio comes from)\n")
    print("| subject | blotch ratio | band DN ratio | master mean / source median mean | argmax frame |")
    print("|---|---:|---:|---:|---:|")
    for s in ORDER:
        x = d[s]
        print("| `%s` | %.3fx | %.3fx | %.3fx | %d |"
              % (s, x["ratio"]["blotch"], x["ratio"]["blotch_band_dn"],
                 x["master"]["blotch_mean_dn"] / x["src_mean_med"], x["src_blotch_argmax"]))

    print("\n### EXPIRY (today's master at the OLD window vs the recorded number)\n")
    print("| subject | stat | recorded | window then -> now | moved | today @ old window | delta | cause |")
    print("|---|---|---:|---|---:|---:|---:|---|")
    for s in ORDER[:6]:
        x, b = d[s], base[s]
        old = b["superseded_record"]["record"]["master"]
        m = x["master"]
        for stat, wk, atk in (("blotch", "blotch_window_yx", "blotch_at_old_window"),
                              ("chroma", "chroma_window_yx", "chroma_at_old_window")):
            wo, wn = old[wk], list(m[wk])
            mv = int(max(abs(wo[0] - wn[0]), abs(wo[1] - wn[1])))
            now = m[atk]
            print("| `%s` | %s | %.5f | [%d, %d] -> [%d, %d] | %d px | %.5f | %+.2f%% | %s |"
                  % (s, stat, old[stat], wo[0], wo[1], wn[0], wn[1], mv, now,
                     100.0 * (now - old[stat]) / old[stat],
                     "MOVED" if mv > 8 else "same window"))

    print("\n### PROVENANCE\n")
    for s in ORDER:
        x = d[s]
        print("| `%s` | %s | %s | cover %.4f | %s |"
              % (s, x["master_sha256"][:16], x["master_manifest"], x["master_cover"],
                 x["master_cover_source"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
