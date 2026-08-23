"""
M29 / 05 -- Is the floor scene texture or shot noise? The answer decides whether
            this measurement can ever be improved by taking more frames.

Script 04 put the detection limit at 32-50% shadow depth, which is far above any
plausible sensor dust (1-15% at working apertures). Before recording that as the
end of the line, the floor has to be attributed, because the two candidates have
opposite consequences:

  if the floor is SHOT NOISE   it falls as 1/sqrt(n) and the limit is a budget
                               problem -- shoot more frames.
  if the floor is SCENE TEXTURE it does not fall with n at all, because the
                               scene is common to every frame of a stack. The
                               limit is then structural and no amount of
                               shooting the SUBJECT will move it.

Discriminator: sweep n and read the exponent. This is discipline 131 used as an
instrument -- flat means deterministic, 1/sqrt(n) means stochastic, in between
measures the mixture.

Second measurement, to price the alternative: a flat field has g/blur(g) == 1 by
construction, so its map floor is pure photon noise and is predictable from the
calibrated sensor model with no free parameters. Computing it says how many
flats at what exposure are needed to reach a given dust sensitivity, which turns
the standing request in captures-needed.md section 4 from an assertion into a
specification.

PRE-REGISTERED:
  Q10  the map rms is flat in n, not 1/sqrt(n). If it falls as 1/sqrt(n) this
       whole milestone is a frame-count problem and the conclusion inverts.
  Q11  the pair-difference floor, which isolates the stochastic part, IS
       1/sqrt(n)-like and is far below the map rms. The gap between the two is
       the scene term, quantified.
"""
import glob, os, json
import numpy as np
import rawpy
from scipy.ndimage import gaussian_filter

BLACK, SIG = 512.0, 24.0
FOLDER = r"D:\personal\macro\109MSDCF"
OUT = os.path.join(os.path.dirname(__file__), "..", "out")
NS = [1, 2, 4, 8, 16]
ISO, RN_E = 160.0, 4.20                     # 109MSDCF; M4 model


def ratio(path):
    with rawpy.imread(path) as r:
        g = r.raw_image_visible[0::2, 1::2].astype(np.float32) - BLACK
    return g / np.maximum(gaussian_filter(g, SIG), 1.0), float(np.median(g))


files = sorted(glob.glob(os.path.join(FOLDER, "*.ARW")))[:max(NS)]
rs, med = [], []
for f in files:
    a, m = ratio(f)
    rs.append(a)
    med.append(m)
print(f"{len(rs)} frames, median signal {np.median(med):.0f} DN")


def hp(m):
    return m - gaussian_filter(m, SIG)


print(f"\nQ10  map rms vs frame count")
print(f"{'n':>4s} {'map rms':>10s} {'x1/sqrt(n)':>12s} {'pair-diff rms':>15s}")
rows = []
for n in NS:
    m = hp(np.mean(rs[:n], axis=0) - 1.0)
    # the stochastic part alone: half-difference of two disjoint n/2 groups
    if n >= 2:
        a = hp(np.mean(rs[: n // 2], axis=0) - 1.0)
        b = hp(np.mean(rs[n // 2: n], axis=0) - 1.0)
        pd = float(((a - b) / 2.0).std())
    else:
        pd = float("nan")
    rows.append(dict(n=n, rms=float(m.std()), pair=pd))
    print(f"{n:4d} {m.std():10.5f} {rows[0]['rms']/np.sqrt(n):12.5f} {pd:15.5f}")

r1, rN = rows[0]["rms"], rows[-1]["rms"]
expo = np.log(rN / r1) / np.log(NS[-1])
print(f"\nQ10  exponent {expo:+.3f}   (0 = scene/deterministic, "
      f"-0.5 = shot noise)   {'SCENE' if expo > -0.15 else 'NOISE'}")
pe = [r for r in rows if not np.isnan(r["pair"])]
pexpo = (np.log(pe[-1]["pair"] / pe[0]["pair"])
         / np.log(pe[-1]["n"] / pe[0]["n"]))
print(f"Q11  pair-difference exponent {pexpo:+.3f}   floor {pe[-1]['pair']:.5f} "
      f"vs map rms {rN:.5f}   scene/noise {rN/pe[-1]['pair']:.1f}x")

# ---- what a flat field would buy ----------------------------------------
print(f"\nflat-field floor from the calibrated model (no free parameters)")
print(f"{'ISO':>5s} {'level DN':>9s} {'per-frame':>10s} {'n=20':>9s} "
      f"{'n=64':>9s} {'5% dust at n=20':>17s}")
flat = []
for iso in (100.0, 160.0):
    g_dn = iso / 436.8
    for S in (4000.0, 8000.0, 12000.0):
        sig = np.sqrt(g_dn * S + (RN_E * g_dn) ** 2)
        per = sig / S
        f20, f64 = per / np.sqrt(20), per / np.sqrt(64)
        flat.append(dict(iso=iso, S=S, per=float(per), n20=float(f20),
                         n64=float(f64), snr5=float(0.05 / f20)))
        print(f"{iso:5.0f} {S:9.0f} {100*per:9.3f}% {100*f20:8.3f}% "
              f"{100*f64:8.3f}% {0.05/f20:16.0f}s")

best = min(x["n20"] for x in flat)
print(f"\nsubject-stack floor {rN:.5f}   best flat floor at n=20 {best:.5f}   "
      f"improvement {rN/best:.0f}x")
with open(os.path.join(OUT, "05-floor.json"), "w") as fh:
    json.dump(dict(sweep=rows, exponent=float(expo), pair_exponent=float(pexpo),
                   flat=flat, improvement=float(rN / best)), fh, indent=1)
