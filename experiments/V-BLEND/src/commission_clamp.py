"""Commission the clamp detector.

A null that contains no dark pixels is not a null for this detector -- it never
exercises the statistic. Each case below therefore puts REAL mass near zero and
asks the detector to tell apart three ways of getting it:

  smooth density that happens to reach zero   -> must read SMOOTH
  a smooth darkening (the rival hypothesis)   -> must read SMOOTH
  a hard clamp                                -> must read CLAMP, exact count
"""
import sys
import numpy as np

sys.path.insert(0, r"C:\dev\strehl-out\V-BLEND")
from zerocensus import census, verdict

H, W = 1200, 1600
N = H * W
rng = np.random.default_rng(20260825)
results = []


def as_img(x):
    return np.clip(np.rint(x), 0, 65535).astype(np.uint16)


def run(tag, img, expect, planted=None, note=""):
    print("\n" + "=" * 74)
    print(f"{tag}   EXPECT: {expect}")
    if note:
        print(f"   {note}")
    print("=" * 74)
    frac0 = (img == 0).mean()
    frac_lo = (img <= 256).mean()
    print(f"  mass at 0 = {frac0*100:.4f}% of samples;  mass <=256 = {frac_lo*100:.4f}%")
    r = census(img, tag)
    verdict(r, tag)
    got = []
    for c in "RGB":
        if r[c]["p0"] < 1e-4:
            got.append("none")
        elif r[c]["spike"] >= 20.0:
            got.append("CLAMP")
        else:
            got.append("SMOOTH")
    agree = all(g == expect or (expect == "SMOOTH" and g == "none") for g in got)
    exact = None
    if planted is not None:
        exact = all(r[c]["count0"] == planted[i] for i, c in enumerate("RGB"))
        print("\n  RECOVERY CHECK (amplitude, not just presence):")
        for i, c in enumerate("RGB"):
            print(f"     {c}: planted {planted[i]:,}  reported {r[c]['count0']:,}  "
                  f"{'EXACT' if r[c]['count0'] == planted[i] else 'MISMATCH'}")
    results.append((tag, expect, got, agree, exact))
    return r


# 1. smooth, with real mass in the low levels but almost none at exactly 0
base = rng.gamma(shape=2.0, scale=1500.0, size=(H, W, 3))
run("CASE1-smooth-gamma", as_img(base), "SMOOTH",
    note="gamma(2,1500): ~1.3% of samples below level 256, essentially none at 0")

# 2. THE REAL NULL FOR THE SPIKE STATISTIC: meaningful mass sitting AT zero,
#    but smoothly -- density at level 0 equals density at levels 1..200.
flat = rng.uniform(0.0, 200.0, size=(H, W, 3))
run("CASE2-smooth-mass-AT-zero", as_img(flat), "SMOOTH",
    note="uniform[0,200]: ~0.25% land on level 0 by rounding, density is flat, "
         "so the detector must NOT call this a clamp")

# 3. the rival hypothesis: a genuine smooth darkening, large
run("CASE3-smooth-darkening-0.06x", as_img(base * 0.06), "SMOOTH",
    note="same data scaled to 6%: now very dark with lots of low pixels, still no clamp")

# 4. hard clamp, sized to the effect actually claimed (~2.2% of frame)
q = np.quantile(base, 0.022)
shifted = base - q
planted = [int((as_img(np.clip(shifted[:, :, c], 0, None))) .__eq__(0).sum()) for c in range(3)]
img4 = np.stack([as_img(np.clip(shifted[:, :, c], 0, None)) for c in range(3)], axis=2)
planted = [int((img4[:, :, c] == 0).sum()) for c in range(3)]
run("CASE4-hard-clamp-2.2pct", img4, "CLAMP", planted=planted,
    note=f"subtract {q:.1f} DN and clip: a clamp of the size claim 1 asserts")

# 5. black scene: zero signal plus read noise, folded at zero by the sensor
dark = np.abs(rng.normal(0.0, 400.0, size=(H, W, 3)))
run("CASE5-black-scene-noise", as_img(dark), "SMOOTH",
    note="|N(0,400)|: a genuinely black region. Mass at 0 is real, not clamped.")

print("\n" + "=" * 74)
print("COMMISSION SUMMARY")
print("=" * 74)
allok = True
for tag, expect, got, agree, exact in results:
    ok = agree and (exact is not False)
    allok &= ok
    ex = "" if exact is None else f"  exact-count={'PASS' if exact else 'FAIL'}"
    print(f"  {'PASS' if ok else 'FAIL'}  {tag:<28} expect {expect:<7} got {got}{ex}")
print(f"\n  OVERALL: {'PASS -- detector discriminates clamp from smooth, and recovers amplitude' if allok else 'FAIL'}")
