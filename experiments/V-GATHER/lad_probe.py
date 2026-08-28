r"""Potency + ceiling-invariance probe for the exponent ladder.

TWO QUESTIONS, BOTH OF WHICH MUST BE ANSWERED BEFORE ANY LADDER NUMBER MEANS
ANYTHING.

  POTENCY. Does an exponent arm reach the pixels? ORCH supplied known-potent
  references (--pyramid-exponent 4.0 moves 90.98% of samples). An arm that does
  not move samples by roughly its expected amount is rendering stale bytes, and
  that failure is GREEN, not RED: identical output looks exactly like "the
  parameter does not matter".

  CEILING INVARIANCE. The ladder freezes the per-site focus ceiling from
  sharp.json and varies only the master. That is only legitimate if a source
  frame is merge-independent. STREHL_ONLY_FRAME stacks one frame, and a merge
  over one frame ought to be identity regardless of the selection exponent --
  but "ought to" is not a measurement. If a single-frame render changes with the
  exponent, every frozen ceiling is contaminated by the very variable under test
  and the whole design collapses. This checks it BYTE-WISE.
"""
import hashlib
import os
import subprocess
import sys

import numpy as np
import tifffile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import certmeasure as cm                                           # noqa: E402

LAD = r"C:\dev\strehl-out\V-GATHER\ladder"
SUB = "coffee-bubbles"


def render(sub, out, exponent=None, sharpen=None, only_frame=None):
    env = dict(os.environ)
    env["STREHL_CACHE_DIR"] = os.path.join(LAD, "cache-" + sub)
    os.makedirs(env["STREHL_CACHE_DIR"], exist_ok=True)
    for v in ("STREHL_FIX_CA", "STREHL_EDGE_AWARE", "STREHL_EDGE_TAU",
              "STREHL_EDGE_CONF", "STREHL_ONLY_FRAME"):
        env.pop(v, None)
    if only_frame is not None:
        env["STREHL_ONLY_FRAME"] = str(only_frame)
    cmd = [cm.EXE, "stack", os.path.join(cm.RAW, sub), "--out", out,
           "--linear-srgb", "--demosaic"]
    if exponent is not None:
        cmd += ["--pyramid-exponent", str(exponent), "--pyramid-sharpen", str(sharpen)]
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if p.returncode != 0 or not os.path.exists(out):
        raise SystemExit("render failed exp=%s: %s" % (exponent, p.stderr[-400:]))
    band = [l for l in p.stdout.splitlines() if "per-band exp" in l]
    return band[0].strip() if band else "(no per-band line)"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def moved(pa, pb):
    a = tifffile.imread(pa)
    b = tifffile.imread(pb)
    if a.shape != b.shape:
        raise SystemExit("shape mismatch %s vs %s" % (a.shape, b.shape))
    n = a.size
    d = int(np.count_nonzero(a != b))
    return 100.0 * d / n, n


def main():
    cm.check_binary()
    os.makedirs(LAD, exist_ok=True)
    print("\n=== POTENCY: does the exponent reach the pixels? ===")
    paths = {}
    for tag, e, s in (("default", None, None), ("e1", 1, 1.0), ("e4", 4, 1.0), ("e16", 16, 1.0)):
        p = os.path.join(LAD, "probe-%s.tiff" % tag)
        if not os.path.exists(p):
            line = render(SUB, p, e, s)
            print("  rendered %-8s %s" % (tag, line))
        paths[tag] = p
    for a, b in (("e1", "e4"), ("e1", "e16"), ("e4", "e16"), ("default", "e16")):
        pct, n = moved(paths[a], paths[b])
        print("  %-8s vs %-8s : %7.4f%% of %d samples differ" % (a, b, pct, n))

    print("\n=== NULL: same arm rendered twice must be byte-identical ===")
    p2 = os.path.join(LAD, "probe-e16-rerun.tiff")
    render(SUB, p2, 16, 1.0)
    h1, h2 = sha(paths["e16"]), sha(p2)
    print("  e16      : %s" % h1[:32])
    print("  e16 rerun: %s" % h2[:32])
    print("  IDENTICAL" if h1 == h2 else "  *** NOT REPRODUCIBLE -- ladder is uninterpretable ***")
    os.remove(p2)
    if h1 != h2:
        raise SystemExit(2)

    print("\n=== CEILING INVARIANCE: is a source frame merge-independent? ===")
    hs = {}
    for e in (1, 16):
        p = os.path.join(LAD, "probe-frame7-e%d.tiff" % e)
        render(SUB, p, e, 1.0, only_frame=7)
        hs[e] = sha(p)
        print("  frame 7 @ exponent %-3d : %s" % (e, hs[e][:32]))
        os.remove(p)
    if hs[1] == hs[16]:
        print("  IDENTICAL -- the frozen ceiling is not a function of the exponent. Design holds.")
    else:
        print("  *** DIFFER -- the ceiling moves with the variable under test. Design INVALID. ***")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
