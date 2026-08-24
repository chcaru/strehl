"""M100 clipping accounting on the renders the SHIPPED binary actually wrote.

sweep.py simulated the rule in numpy to choose its two constants. This script
does not simulate anything: it reads the `auto-<stack>.tif` files produced by
`strehl stack --srgb --auto-exposure` and the zero-stop `tune-<stack>-srgb.tif`
files produced by the same binary without the flag, and reports

  - the fraction of pixels at 65535 in any channel and in all three,
  - encoded luma p99.9 under both candidate definitions of "luma",

before and after, so the pre-registered bars B3 and B4 can be judged on real
output. It also diffs the stops the binary chose against the stops sweep.py
predicted, which is the check that the shipped rule is the rule I tuned.

READ-ONLY on D:\\. Writes nothing but stdout.
"""
import glob
import json
import os
import numpy as np
import tifffile

SRC = r"C:\dev\strehl-out\M100"
HERE = os.path.dirname(os.path.abspath(__file__))
# Row 1 of SRGB_TO_XYZ_D65 in crates/strehl-core/src/color.rs.
YW = np.array([0.2126729, 0.7151522, 0.0722750], dtype=np.float64)


def read_log(path):
    """PowerShell's 2> writes UTF-16LE with a BOM; be robust to either."""
    raw = open(path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    return raw.decode("utf-8", errors="replace")


def stats(path):
    a = tifffile.imread(path)
    at_max = a == 65535
    enc = a.astype(np.float64) / 65535.0
    return dict(
        w=int(a.shape[1]), h=int(a.shape[0]),
        any_clip=float(at_max.any(axis=2).mean()),
        all_clip=float(at_max.all(axis=2).mean()),
        mean_p50=float(np.percentile(enc.mean(axis=2), 50)),
        mean_p999=float(np.percentile(enc.mean(axis=2), 99.9)),
        bt709_p999=float(np.percentile(enc @ YW, 99.9)),
    )


def main():
    with open(os.path.join(HERE, "sweep.json")) as fh:
        sweep = json.load(fh)
    predicted = {}
    for name, rows in sweep.items():
        for r in rows:
            if r["p"] == 99.9 and r["target"] == 0.90:
                predicted[name] = r["stops"]

    chosen = {}
    for f in sorted(glob.glob(os.path.join(SRC, "logs", "auto-*.err"))):
        name = os.path.basename(f)[len("auto-"):-len(".err")]
        for line in read_log(f).splitlines():
            if line.startswith("exposure"):
                tok = line.split(":", 1)[1].strip().split()[0]
                chosen[name] = float(tok)
                break

    print("=" * 92)
    print("BEFORE (no flag) -> AFTER (--auto-exposure), shipped binary, full "
          "frame counts")
    print("  %-28s %7s %7s %9s %9s %9s %9s"
          % ("stack", "stops", "pred", "any-clip%", "all-clip%",
             "p99.9mean", "p99.9709"))
    worst_any = worst_all = 0.0
    worst_added_any = worst_added_all = 0.0
    min_mean = min_709 = 1.0
    for f in sorted(glob.glob(os.path.join(SRC, "auto-*.tif"))):
        name = os.path.basename(f)[len("auto-"):-len(".tif")]
        b = stats(os.path.join(SRC, "tune-%s-srgb.tif" % name))
        a = stats(f)
        print("  %-28s %7s %7s %9s %9s %9.4f %9.4f"
              % (name + " before", "0.00", "",
                 "%.4f" % (100 * b["any_clip"]),
                 "%.4f" % (100 * b["all_clip"]),
                 b["mean_p999"], b["bt709_p999"]))
        print("  %-28s %+7.2f %+7.2f %9s %9s %9.4f %9.4f"
              % (name + " after", chosen.get(name, float("nan")),
                 predicted.get(name, float("nan")),
                 "%.4f" % (100 * a["any_clip"]),
                 "%.4f" % (100 * a["all_clip"]),
                 a["mean_p999"], a["bt709_p999"]))
        worst_any = max(worst_any, a["any_clip"])
        worst_all = max(worst_all, a["all_clip"])
        worst_added_any = max(worst_added_any, a["any_clip"] - b["any_clip"])
        worst_added_all = max(worst_added_all, a["all_clip"] - b["all_clip"])
        min_mean = min(min_mean, a["mean_p999"])
        min_709 = min(min_709, a["bt709_p999"])

    print()
    print("PRE-REGISTERED BARS, judged on the shipped output, AS WRITTEN")
    print("  B3 any-channel clipping  worst %.4f%%  ceiling 0.50%%   %s"
          % (100 * worst_any, "PASS" if worst_any <= 0.005 else "FAIL"))
    print("  B3 all-channel clipping  worst %.4f%%  ceiling 0.20%%   %s"
          % (100 * worst_all, "PASS" if worst_all <= 0.002 else "FAIL"))
    print("  B4 luma p99.9 (mean-of-channels) min %.4f  bar 0.90   %s"
          % (min_mean, "PASS" if min_mean >= 0.90 else "FAIL"))
    print("  B4 luma p99.9 (BT.709 relative)  min %.4f  bar 0.90   %s"
          % (min_709, "PASS" if min_709 >= 0.90 else "FAIL"))
    print()
    print("POST-HOC (declared as post-hoc, NOT a moved bar): clipping ADDED by")
    print("the exposure change, i.e. after minus before, floored at zero. B3 as")
    print("written is an absolute ceiling and so charges the rule for highlights")
    print("that were already blown at zero stops.")
    print("  added any-channel  worst %+.4f%%   %s"
          % (100 * worst_added_any,
             "<= 0.50% ceiling" if worst_added_any <= 0.005 else "OVER"))
    print("  added all-channel  worst %+.4f%%   %s"
          % (100 * worst_added_all,
             "<= 0.20% ceiling" if worst_added_all <= 0.002 else "OVER"))


if __name__ == "__main__":
    main()
