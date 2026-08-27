"""Commission `orch_printready.py`'s corrected clipping gate.

The gate's clip statistic changed from a count of CHANNEL samples at the ceiling
to a count of PIXELS with ALL THREE channels at the ceiling. That change is only
worth anything if the new statistic can still fail, and only correct if it
stops failing the thing it should never have failed. A gate that passes
everything and a gate that is broken produce the same table.

So: four arms on a real master, and every one of them has a predicted verdict
written before it runs.

  CLEAN      untouched copy                      -> PASS   (the anchor)
  NEUTRAL    a patch with ALL THREE channels at  -> FAIL   (must still bite)
             65535, area > CLIP_MAX
  ONECHAN    a patch with EXACTLY ONE channel at -> PASS   (the whole point:
             65535, same area                             the old gate failed
                                                          this by construction)
  TINY       a NEUTRAL patch of area < CLIP_MAX  -> PASS   (threshold, not
                                                          mere presence)

ONECHAN is the discriminating arm. The old statistic counted channel samples,
so a one-channel pin of area A contributed A/3 to a mean over 3A samples and
registered exactly as strongly as a neutral blow of the same area. `gamut_map`
manufactures those pins on EVERY out-of-gamut colour pixel, by construction,
with nothing blown. If ONECHAN fails, the fix did not take.

TINY guards the opposite error: a statistic that fires on a single pixel is not
a gate, it is a presence check, and it would fail every master with one specular.

Usage:  python commission_clip.py <master.tiff>
"""

import pathlib
import subprocess
import sys

import numpy as np
import tifffile

HERE = pathlib.Path(__file__).resolve().parent
GATE = HERE / "orch_printready.py"
CLIP_MAX = 0.001          # must track orch_printready.CLIP_MAX


def plant(a, frac, channels):
    """Set `frac` of the frame's pixels to 65535 on `channels`."""
    out = a.copy()
    h, w = out.shape[0], out.shape[1]
    n = int(round(frac * h * w))
    rows = max(1, n // w)
    for c in channels:
        out[:rows, :, c] = 65535
    actual = rows * w / float(h * w)
    return out, actual


def run_gate(d, arm):
    r = subprocess.run(
        [sys.executable, str(GATE), str(d), arm],
        capture_output=True, text=True)
    return r.stdout + r.stderr


def verdict_of(text, stem):
    for line in text.splitlines():
        if stem in line and line[:6].strip() in ("PASS", "FAIL", "REVIEW"):
            return line[:6].strip(), line.strip()
    return "MISSING", "<no row for %s>" % stem


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    src = pathlib.Path(sys.argv[1])
    if not src.is_file():
        raise SystemExit("no such master: %s" % src)
    a = tifffile.imread(str(src))
    if a.ndim != 3 or a.shape[2] < 3:
        raise SystemExit("not an RGB master: %s" % src)
    a = a[..., :3]

    big = CLIP_MAX * 4.0        # comfortably over
    small = CLIP_MAX * 0.2      # comfortably under

    arms = [
        ("CLEAN",   None,                  "PASS"),
        ("NEUTRAL", (big,   (0, 1, 2)),    "FAIL"),
        ("ONECHAN", (big,   (1,)),         "PASS"),
        ("TINY",    (small, (0, 1, 2)),    "PASS"),
    ]

    root = pathlib.Path(r"C:\dev\strehl-out\ORCH-COMMISSION")
    root.mkdir(parents=True, exist_ok=True)

    print("commissioning the corrected clip gate on %s" % src.name)
    print("CLIP_MAX = %.4f%%   planted-big = %.4f%%   planted-tiny = %.4f%%\n"
          % (CLIP_MAX * 100, big * 100, small * 100))
    print("%-9s %-8s %-8s %s" % ("arm", "expect", "got", "verdict"))
    print("-" * 78)

    ok = True
    for name, spec, expect in arms:
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("*.tiff"):
            old.unlink()
        if spec is None:
            planted, actual = a, 0.0
        else:
            frac, chans = spec
            planted, actual = plant(a, frac, chans)
        stem = "commission-" + name.lower()
        tifffile.imwrite(str(d / ("%s--%s.tiff" % (stem, name))), planted)
        got, row = verdict_of(run_gate(d, name), stem)
        flag = "OK" if got == expect else "*** WRONG ***"
        if got != expect:
            ok = False
        print("%-9s %-8s %-8s %s" % (name, expect, got, flag))
        print("          %s" % row)

    print("-" * 78)
    if ok:
        print("COMMISSION PASSED -- the gate bites on a neutral blow, ignores a\n"
              "one-channel gamut pin, and respects its own threshold.")
        return 0
    print("COMMISSION FAILED -- do not trust any table this gate prints.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
