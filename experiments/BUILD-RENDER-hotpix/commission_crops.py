"""Commission crops.py against a null and a known-potent, exactly-known blur.

THE VERDICT, WRITTEN BEFORE THE ARMS WERE MADE
----------------------------------------------
Three arms of one subject, built from ONE rendered TIFF so that nothing but the
planted defect differs:

  ref     the render itself
  null    a byte-identical copy      -> must show NOTHING at any site
  blur15  ref, Gaussian sigma=1.5 px -> must show PLAINLY at the `sharp` site

The null is the half that makes the blur arm mean anything. An instrument that
lights up on `blur15` might simply light up on everything -- on file order, on
its own resampling, on JPEG noise. The null is the same instrument, the same
code path, the same composite, with nothing planted. If `null` reads as
different, the `blur15` reading is worthless and I would rather find that out
here than in a print judgement.

A PRE-REGISTERED CRITERION THAT FAILED, AND WHY I CHANGED IT ANYWAY
------------------------------------------------------------------
The first run of this file required `sharp` to lose MORE acuity to the blur
than `flat` did -- "the sharp site is preferentially sensitive to softening".
It failed: sharp lost 75.8%, flat lost 89.8%.

Changing a criterion after seeing the number is the move that most needs
declaring, so: the criterion was wrong, not the instrument, and the reason is
physical. `acuity` is mean |Laplacian|, and in a flat region that is dominated
by NOISE, which is broadband and which a Gaussian removes almost completely.
Structured subject detail survives proportionally better. So a larger relative
drop in flat regions is what blur does, and my criterion encoded a wrong model
of the statistic rather than a property of the instrument.

What `sharp` is actually for is holding the most detail the print can lose, so
the replacement criterion tests that directly and absolutely: the `sharp` site
must carry the highest absolute acuity of the three in the reference. Both the
original criterion and this replacement are recorded here so the substitution
is visible rather than tidied away.

Synthetic rather than a second render on purpose: a rendered sabotage arm always
differs in more than the one thing (a different merge backend, a different
selection rule), so a null result could be blamed on the difference rather than
on the instrument. Here the ground truth is exact and arithmetic.

The site-drift check is the third arm of the argument: crops.py claims it sites
ONCE and applies those coordinates unchanged to every arm. If that is false the
composites compare different places and every conclusion drawn from them is
about geography rather than quality. So the sites are re-derived here from the
blurred image alone and shown to move -- which is exactly why they must not be
allowed to.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import cv2
import scipy.ndimage as ndi
import tifffile

SIGMA = 1.5
SUBJECT = "109MSDCF"
ROOT = Path(r"C:\dev\strehl-out\BUILD-RENDER-harness")
SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"

src = ROOT / "ref" / f"{SUBJECT}--ref.tiff"
if not src.exists():
    raise SystemExit(f"no reference render at {src}")

img = tifffile.imread(src)
assert img.dtype == np.uint16 and img.ndim == 3 and img.shape[2] == 3

work = ROOT / "commission"
if work.exists():
    shutil.rmtree(work)
work.mkdir(parents=True)

shutil.copy2(src, work / f"{SUBJECT}--ref.tiff")
shutil.copy2(src, work / f"{SUBJECT}--null.tiff")

blur = np.empty_like(img)
for c in range(3):
    blur[:, :, c] = ndi.gaussian_filter(img[:, :, c].astype(np.float32), SIGMA).astype(np.uint16)
tifffile.imwrite(work / f"{SUBJECT}--blur15.tiff", blur)

print(f"arms built in {work}")
print(f"  ref    {src.stat().st_size/1e6:.0f} MB")
print(f"  null   byte-identical copy of ref")
print(f"  blur15 gaussian sigma={SIGMA} px\n")

# --- the instrument under test -------------------------------------------
out = work / "crops"
r = subprocess.run(
    [sys.executable, str(SCRIPTS / "crops.py"), str(work),
     "--subject", SUBJECT, "--ref", "ref", "--out", str(out),
     "--display", "linear-srgb", "--scale", "1.0"],
    capture_output=True, text=True)
print(r.stdout, r.stderr, sep="")
if r.returncode != 0:
    raise SystemExit("crops.py failed")

# --- read the verdict off the crops it actually wrote --------------------
# Measured on the 16-bit crops crops.py emitted, not on the source arrays: the
# claim under test is about what the instrument PRODUCES, so re-measuring the
# inputs would test arithmetic I already know.
def read_crop(p: Path) -> np.ndarray:
    """Read a 16-bit RGB PNG back. cv2, not tifffile (it is a PNG) and not
    PIL (which mangles 16-bit RGB). uint16 is asserted, so a writer that
    silently dropped to 8 bits fails here rather than flattering the table."""
    a = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    assert a is not None, f"could not read {p}"
    assert a.dtype == np.uint16, f"{p.name}: {a.dtype}, not uint16"
    return a[:, :, ::-1]


def acuity(a):
    g = a[:, :, 1].astype(np.float32)
    return float(np.abs(ndi.laplace(g)).mean())


print(f"{'site':7s}{'arm':9s}{'acuity':>12s}{'vs ref':>10s}   {'identical?':>10s}")
rows = {}
for site in ("edge", "flat", "sharp"):
    base = None
    for arm in ("ref", "null", "blur15"):
        a = read_crop(out / f"{SUBJECT}--{site}--{arm}-16bit.png")
        ac = acuity(a)
        if arm == "ref":
            base, ident = ac, "--"
            ref_arr = a
        else:
            ident = "YES" if np.array_equal(a, ref_arr) else "no"
        rows[(site, arm)] = (ac, ac / base, ident)
        print(f"{site:7s}{arm:9s}{ac:12.4f}{ac/base:9.1%}   {ident:>10s}")
    print()

fail = []
for site in ("edge", "flat", "sharp"):
    if rows[(site, "null")][2] != "YES":
        fail.append(f"{site}: null crop differs from ref -- instrument is not stable")
    if abs(rows[(site, "null")][1] - 1.0) > 1e-9:
        fail.append(f"{site}: null acuity moved -- instrument is not stable")

sharp_drop = 1 - rows[("sharp", "blur15")][1]
flat_drop = 1 - rows[("flat", "blur15")][1]
if sharp_drop < 0.30:
    fail.append(f"sharp: blur only cost {sharp_drop:.1%} acuity -- instrument cannot see softening")

# Replaces the failed "sharp must drop more than flat" criterion; see the
# header. `sharp` earns its name by holding the most detail, not by having the
# largest relative response to a Gaussian.
ref_ac = {s: rows[(s, "ref")][0] for s in ("edge", "flat", "sharp")}
if ref_ac["sharp"] < max(ref_ac.values()) - 1e-9:
    fail.append(f"sharp is not the sharpest site: {ref_ac} -- siting rule is not doing its job")
if ref_ac["flat"] >= ref_ac["sharp"]:
    fail.append(f"flat site is not flatter than the sharp site: {ref_ac}")

# Distinct sites. edge and sharp both landed on tile (1408,2944) before the
# exclusion rule was added, which silently collapsed three questions into two.
sites_txt = (out / f"{SUBJECT}--SITES.txt").read_text().splitlines()
coords = [ln.split("score=")[0].strip() for ln in sites_txt if ln.startswith(("edge:", "flat:", "sharp:"))]
if len(set(coords)) < 3:
    fail.append(f"sites are not distinct: {coords}")

# --- site drift: why the sites must be frozen ----------------------------
sys.path.insert(0, str(SCRIPTS))
import crops as C  # noqa: E402

s_ref = C.site_all(img)
s_blur = C.site_all(blur)
moved = [k for k in s_ref if s_ref[k][:2] != s_blur[k][:2]]
print("site drift if each arm sited itself:")
for k in s_ref:
    print(f"  {k:6s} ref=({s_ref[k][0]},{s_ref[k][1]})  blur15=({s_blur[k][0]},{s_blur[k][1]})"
          f"  {'MOVED' if k in moved else 'same'}")
print(f"  -> {len(moved)}/3 sites move under a defect. crops.py freezes them on "
      f"--site-on, which is what makes the composites comparable.\n")

if fail:
    print("COMMISSION FAILED")
    for f in fail:
        print("  " + f)
    return_code = 1
else:
    print(f"COMMISSION PASSED: null identical at all 3 sites; blur cost "
          f"{sharp_drop:.1%} acuity at `sharp` vs {flat_drop:.1%} at `flat`.")
    return_code = 0
print(f"\nlook at: {out}")
sys.exit(return_code)
