import io, re, sys
p = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-BANDFLOOR\bandmetrics.py"
s = io.open(p, encoding="utf-8").read()

old_plant = '''def plant_mottle(g, amp, seed=3):
    """Synthetic mid-scale mottle: band-limited noise at the convicted scale."""
    rng = np.random.default_rng(seed)
    n = rng.normal(0.0, 1.0, g.shape).astype(np.float32)
    n = smooth(n, 24) - smooth(n, 96)
    n /= max(float(n.std()), 1e-9)
    return (g + amp * float(np.mean(g)) * n).astype(np.float32)'''

new_plant = '''def band_noise(shape, bands, seed=3):
    """White noise projected onto exactly `bands` of the SAME ladder the
    instrument reads. SYNTHESIS fact 1814: a plant sized in one band's units
    arrives at a tenth of its intended strength in another, so the plant is
    built with the analyser's own filters rather than a hand-picked pair of
    radii."""
    rng = np.random.default_rng(seed)
    n = rng.normal(0.0, 1.0, shape).astype(np.float32)
    acc = np.zeros(shape, np.float32)
    prev = smooth(n, RADII[0])
    for i, r in enumerate(RADII[1:]):
        nxt = smooth(n, r)
        if i in bands:
            acc += prev - nxt
        prev = nxt
    return acc


def plant_mottle(g, q, cm, seed=3):
    """Add mottle whose coarse-band contrast on FLAT tiles is `q` times the
    contrast already there. Sized from the image, not typed."""
    y0, x0, ty, tx = tile_grid(g.shape)
    cl = tile_rms(cm.astype(np.float32), ty, tx, y0, x0)
    pr, lv = band_profile(g, y0, x0, ty, tx)
    t = group(pr, lv, FINE)[cl == 0]
    lo_c = np.percentile(t, 33.333)
    flat = (cl == 0) & (group(pr, lv, FINE) <= lo_c)
    c_flat = float(np.median(group(pr, lv, COARSE)[flat]))
    lvl = float(np.median(lv[flat]))
    n = band_noise(g.shape, COARSE, seed)
    n /= max(float(n.std()), 1e-9)
    amp = q * c_flat * lvl
    print("      [plant sized from the image: flat coarse contrast %.5f, "
          "level %.0f DN -> amplitude %.2f DN rms]" % (c_flat, lvl, amp))
    return (g + amp * n).astype(np.float32)'''

assert old_plant in s
s = s.replace(old_plant, new_plant)

old_arms = '''        ("DEFECT   mottle planted at 0.4%% of mean", plant_mottle(g, 0.004),
         {"BLOTCH": +1}),'''
new_arms = '''        ("DEFECT   mottle 50% of the flat coarse contrast",
         plant_mottle(g, 0.50, cm), {"BLOTCH": +1}),
        ("DEFECT   mottle 15% of the flat coarse contrast",
         plant_mottle(g, 0.15, cm, seed=9), {"BLOTCH": +1}),'''
assert old_arms in s
s = s.replace(old_arms, new_arms)
io.open(p, "w", encoding="utf-8").write(s)
print("patched")
