"""E-series: commission edge_slope, the primary sharpness metric."""
import numpy as np, tri, os, sys
from scipy import ndimage
rng = np.random.default_rng(23)
fail = []

# Real content, so the control is exercised on the textures it will judge.
src = os.path.join(tri.OUT, "tiles", "119MSDCF.DETAIL.npz")
assert os.path.exists(src), f"ANCHOR MISSING: {src} -- cannot commission on real content"
base = np.load(src)["merge"].astype(np.float32)
print(f"content: 119MSDCF DETAIL merge tile {base.shape}, "
      f"mean {base.mean():.1f} DN, existing noise {tri.pixel_noise(base):.2f} DN")

# E1 NULL: a file against itself must return exactly the identity.
r = tri.edge_slope(base) / tri.edge_slope(base.copy())
print(f"E1 null (self vs self)            ratio = {r:.6f}  (must be exactly 1.0)")
if r != 1.0: fail.append("E1")

# E2 NOISE IMMUNITY: the merge/frame noise gap is the confound.  Adding noise
#    must NOT change the statistic.
e0 = tri.edge_slope(base)
print(f"E2 base edge slope = {e0:.2f} DN/px")
worst = 1.0
for sd in (10.0, 20.0, 40.0, 80.0, 160.0):
    e = tri.edge_slope(base + rng.normal(0, sd, base.shape).astype(np.float32))
    print(f"   +noise sd={sd:6.1f} DN -> {e:9.2f} DN/px   ratio {e/e0:.4f}")
    worst = max(worst, e / e0, e0 / e)
print(f"E2 worst deviation across a 16x noise range = {(worst-1)*100:.2f}%")
if worst > 1.15: fail.append(f"E2 {worst:.3f}")

# E3 POSITIVE CONTROL: plant a known blur; the instrument must recover it, and
#    the recovered magnitude must FALL MONOTONICALLY with sigma.
prev = 1.0
for sg in (0.4, 0.6, 0.8, 1.2):
    b = ndimage.gaussian_filter(base, sg)
    rr = tri.edge_slope(b) / e0
    print(f"E3 planted blur sigma={sg:.1f} px -> recovered ratio {rr:.4f}")
    if rr >= prev: fail.append(f"E3 not monotone at {sg}")
    prev = rr
# E3b ROUND TRIP: the calibration must RECOVER a planted blur in pixels.  This
#     is the control that matters -- a compressed ratio is harmless if it
#     inverts correctly, and fatal if it does not.
print()
for sg in (0.3, 0.5, 0.8, 1.2, 1.8):
    b = ndimage.gaussian_filter(base, sg)
    rr = tri.edge_slope(b) / e0
    rec = tri.blur_equiv(base, rr)
    err = abs(rec - sg)
    print(f"E3b planted {sg:.2f} px -> ratio {rr:.4f} -> recovered {rec:.3f} px"
          f"   (error {err:+.3f} px)")
    if err > 0.15: fail.append(f"E3b sigma={sg} recovered {rec:.2f}")

# E4 TEETH: without the median the same test is corrupted by noise -- proof
#    the defence is load-bearing and E2 is not passing trivially.
def raw_slope(t):
    gy, gx = np.gradient(t.astype(np.float64))
    return float(np.percentile(np.hypot(gy, gx), 99.5))
# E4 TEETH, stated correctly.  The p99.5 gradient looks at the top 0.5% of
# edges, which sit far above any plausible noise, so it is INHERENTLY noise
# robust and the median filter is not what saves it.  The teeth therefore
# belong to the metric being REPLACED: the control must show that the old
# instrument fails on this exact data and the new one does not, otherwise
# switching metrics is unjustified.
lo = os.path.join(tri.OUT, "tiles", "119MSDCF.SOURCE-BEST.npz")
assert os.path.exists(lo), f"ANCHOR MISSING: {lo}"
z = np.load(lo); mg, fr = z["merge"].astype(np.float32), z["frame"].astype(np.float32)
kb = float(z["ka"])
band_m = tri.band_amp(mg, kb)["high"]; band_f = tri.band_amp(fr, kb)["high"]
edge_m = tri.edge_slope(mg); edge_f = tri.edge_slope(fr)
nm, nf = tri.pixel_noise(mg), tri.pixel_noise(fr)
print(f"E4 real pair 119MSDCF SOURCE-BEST  (merge noise {nm:.1f} DN, "
      f"frame noise {nf:.1f} DN, ratio {nf/nm:.2f}x)")
print(f"   OLD band-amplitude metric : merge {band_m:8.2f} / frame {band_f:8.2f} DN"
      f"  -> {band_m/band_f:.3f}   (reads as a 'merge defect')")
print(f"   NEW edge-slope metric     : merge {edge_m:8.2f} / frame {edge_f:8.2f} DN/px"
      f"  -> {edge_m/edge_f:.3f}   (merge matches the frame)")
if band_m / band_f > 0.75: fail.append("E4 old metric did not fail; teeth absent")
if edge_m / edge_f < 0.90: fail.append("E4 new metric did not rescue the pair")
print(f"   the two metrics disagree by {(edge_m/edge_f)/(band_m/band_f):.2f}x on "
      f"the SAME pixels; the crop adjudicates in favour of the edge metric")
# E5 the gather self-calibration must transfer to this statistic.
costs = []
for ph in tri.GATHER_PHASES:
    g = tri.catmull_rom_shift(base, ph, ph, (8, 8, 496, 496))
    costs.append(tri.edge_slope(g) / tri.edge_slope(base[8:504, 8:504]))
print(f"E5 gather cost on edge slope = {np.mean(costs):.4f} "
      f"(per phase {', '.join(f'{c:.4f}' for c in costs)})")
if not (0.70 <= np.mean(costs) <= 1.00): fail.append("E5 cost out of range")

print("\nE " + ("FAIL " + "; ".join(fail) if fail else "PASS"))
sys.exit(1 if fail else 0)
