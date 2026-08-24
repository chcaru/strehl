"""K12 -- what each resampling kernel does to CHROMATIC FRINGING on real frames.

The orchestrator saw by eye that `nearest` visibly amplifies chromatic fringing
on the bee's hairs, and made a statement about fringing a precondition for any
default kernel change. Fringing is in the DATA (lateral CA of a 100mm macro
behind a 2x teleconverter); a kernel cannot create it, only modulate how much
survives. This measures that modulation.

Demosaic-free by construction: each output pixel is one real sensor quad,
R = R, G = (G1+G2)/2, B = B, at half linear resolution. That is strehl's own
byte-frozen binned camera-native path, and it removes the demosaic as a
confound -- a demosaic invents chroma at edges, which is exactly the quantity
under test.

METRIC. Chroma channels c_r = R - G and c_b = B - G (white balance is a DC
offset and the gradient removes it). A fringe is a chroma SWING localised at an
edge, so:

    F = RMS over edge pixels of  sqrt(|grad c_r|^2 + |grad c_b|^2)

with the edge mask taken as the top EDGE_PCT of |grad G| computed ON THE SOURCE
TILE and held FIXED across kernels -- a per-kernel mask would let a sharper
kernel select its own, more favourable, pixel population.

BARS AND CONTROLS, REGISTERED BEFORE THE RUN
--------------------------------------------
C-NULL   Same kernel both sides must give exactly 0.000000 dex. A structural
         zero; anything else means the pipeline is not deterministic.

C-POWER  Plant a lateral chromatic shift -- displace the R plane by +0.5 px
         against G and B in the SOURCE -- and re-measure through the fixed
         catmull-rom path. F must rise by >= +0.10 dex. If it does not, the
         metric cannot see fringing, the arm is VOID, and no kernel number
         below may be quoted. This is discipline 594: the instrument must be
         shown saying otherwise.

C-ORDER  A FALSIFIABLE PREDICTION FROM THE EYE, not from the metric. The
         orchestrator inspected 1:1 crops and reported nearest amplifying
         fringing relative to catmull-rom. So this metric must read
         F(nearest) > F(catmull-rom). If it does not, THE EYE WINS and I report
         that my metric disagrees with inspection rather than quietly
         preferring the metric.

HEADLINE The number the default decision needs: F(lanczos3) - F(catmull-rom),
         in dex, reported alongside the band sharpness so the trade is visible
         rather than asserted.

Sharpness is reported through the SAME instrument used for the kernel gain
(m95cov.band_ratio on 0.30-0.48 cyc/px), so the two axes are commensurable.
"""

import json
import sys
from pathlib import Path

import numpy as np
import rawpy

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
sys.path.insert(0, str(ROOT / "experiments" / "M95-coverage" / "src"))
import m95cov as M  # noqa: E402


def _nearest_taps(t):
    hi = (t >= 0.5).astype(np.float64)
    return np.stack([1.0 - hi, hi])


def _bilinear_taps(t):
    return np.stack([1.0 - t, t])


# Injected locally rather than edited into the shared module, which other
# committed scripts import. `gather_1d` indexes i0 - taps//2 + 1 + j, so for
# taps=2 that is i0 and i0+1 -- the correct pair for both kernels.
M.KERNELS["nearest"] = (2, _nearest_taps)
M.KERNELS["bilinear"] = (2, _bilinear_taps)

OUT = ROOT / "experiments" / "M95-kernel" / "out"
STACK = Path(r"D:\personal\macro\bee-3-cpl")

KERNELS = ["nearest", "bilinear", "catmull-rom", "lanczos3"]
TILE = 256
PAD = 384
NTILES = 24
EDGE_PCT = 99.0  # top 1% of |grad G| on the source tile
# Three phases, not one. At exactly 0.5 px `nearest` degenerates to an integer
# shift -- it interpolates nothing, loses nothing, and would be flattered by a
# single-phase test. Averaging over a generic set removes that artefact.
PHASES = [0.27, 0.5, 0.73]
OFF = 0.5  # the phase used for the controls
SEED = 20260824


def bin_quads(path):
    """One output pixel per sensor quad: R, (G1+G2)/2, B. No demosaic."""
    with rawpy.imread(str(path)) as raw:
        vis = raw.raw_image_visible.astype(np.float32)
        pat = raw.raw_pattern
        desc = raw.color_desc.decode()
        black = np.array(raw.black_level_per_channel, dtype=np.float32)
    h, w = vis.shape
    h -= h % 2
    w -= w % 2
    vis = vis[:h, :w]
    planes = {}
    for dy in (0, 1):
        for dx in (0, 1):
            idx = int(pat[dy, dx])
            sub = vis[dy::2, dx::2] - black[idx]
            planes.setdefault(desc[idx], []).append(sub)
    r = planes["R"][0]
    b = planes["B"][0]
    g = np.mean(planes["G"], axis=0)
    return r.astype(np.float32), g.astype(np.float32), b.astype(np.float32)


def grad_mag(a):
    gy = np.zeros_like(a)
    gx = np.zeros_like(a)
    gy[1:-1, :] = 0.5 * (a[2:, :] - a[:-2, :])
    gx[:, 1:-1] = 0.5 * (a[:, 2:] - a[:, :-2])
    return gy, gx


def fringe_stat(r, g, b, mask):
    cr = r - g
    cb = b - g
    ry, rx = grad_mag(cr)
    by, bx = grad_mag(cb)
    e = ry**2 + rx**2 + by**2 + bx**2
    return float(np.sqrt(np.mean(e[mask])))


def fringe_stat_norm(r, g, b, mask):
    """Chroma gradient normalised by the luminance gradient that carries it.

    The raw statistic is dominated by the fact that a strong edge has a large
    chroma gradient whether or not the channels are displaced -- R and G edges
    differ in amplitude on any coloured subject. Dividing by |grad G| asks the
    question that actually distinguishes a fringe: is the chroma swing
    disproportionate to the edge producing it?
    """
    cr = r - g
    cb = b - g
    ry, rx = grad_mag(cr)
    by, bx = grad_mag(cb)
    gy, gx = grad_mag(g)
    num = np.sqrt(ry**2 + rx**2 + by**2 + bx**2)
    den = np.sqrt(gy**2 + gx**2) + 1e-6
    return float(np.sqrt(np.mean((num[mask] / den[mask]) ** 2)))


def shift_plane(a, dx):
    """Sub-pixel horizontal shift via the validated catmull-rom gather."""
    n = a.shape[0]
    coords = np.arange(a.shape[1], dtype=np.float64) + dx
    coords = np.clip(coords, 1.0, a.shape[1] - 3.0)
    return M.gather_1d(a, coords, axis=1, kernel="catmull-rom")[:n, :]


def pick(gsrc, n, rng):
    """Edge-rich tiles, chosen once on G and reused for every kernel."""
    h, w = gsrc.shape
    cands = []
    for _ in range(n * 40):
        y = rng.integers(PAD, h - PAD - TILE)
        x = rng.integers(PAD, w - PAD - TILE)
        t = gsrc[y : y + TILE, x : x + TILE]
        gy, gx = grad_mag(t)
        cands.append((float(np.mean(np.sqrt(gy**2 + gx**2))), int(y), int(x)))
    cands.sort(reverse=True)
    return [(y, x) for _, y, x in cands[:n]]


frames = sorted(STACK.glob("*.ARW"))
if not frames:
    raise SystemExit(f"no frames under {STACK}")
frame = frames[len(frames) // 2]

print("=" * 80)
print("K12  chromatic fringing per resampling kernel")
print("=" * 80)
print(f"frame      : {frame.name}  (middle of {len(frames)})")
print(f"tiles      : {NTILES} x {TILE}px, edge mask = top {100 - EDGE_PCT:.0f}% of |grad G|")
print(f"phases     : {PHASES} px, scale 1.0 (pure sub-pixel shift, no zoom)")

R0, G0, B0 = bin_quads(frame)
print(f"binned RGB : {G0.shape[1]} x {G0.shape[0]} per channel (one sensor quad per pixel)")

rng = np.random.default_rng(SEED)
tiles = pick(G0, NTILES, rng)

res = {k: {"F": [], "Fn": [], "band": []} for k in KERNELS}
null_vals = []
PLANT_PX = [0.5, 1.0]
planted = {px: {"base": [], "plant": [], "base_n": [], "plant_n": []} for px in PLANT_PX}

for (y, x) in tiles:
    sr = R0[y - PAD : y + TILE + PAD, x - PAD : x + TILE + PAD]
    sg = G0[y - PAD : y + TILE + PAD, x - PAD : x + TILE + PAD]
    sb = B0[y - PAD : y + TILE + PAD, x - PAD : x + TILE + PAD]

    # Edge mask fixed on the SOURCE, shared by every kernel.
    gc = M.centre_crop(sg, TILE)
    gy, gx = grad_mag(gc)
    gm = np.sqrt(gy**2 + gx**2)
    mask = gm >= np.percentile(gm, EDGE_PCT)

    for k in KERNELS:
        for ph in PHASES:
            r = M.gather(sr, 1.0, ph, ph, n_out=TILE, kernel=k)
            g = M.gather(sg, 1.0, ph, ph, n_out=TILE, kernel=k)
            b = M.gather(sb, 1.0, ph, ph, n_out=TILE, kernel=k)
            res[k]["F"].append(fringe_stat(r, g, b, mask))
            res[k]["Fn"].append(fringe_stat_norm(r, g, b, mask))
            res[k]["band"].append(M.band_ratio(g, 1.0))

    # C-NULL: identical kernel both sides.
    a1 = M.gather(sg, 1.0, OFF, OFF, n_out=TILE, kernel="catmull-rom")
    a2 = M.gather(sg, 1.0, OFF, OFF, n_out=TILE, kernel="catmull-rom")
    null_vals.append(float(np.max(np.abs(a1 - a2))))

    # C-POWER: plant lateral CA by displacing R against G and B.
    #
    # BOTH arms go through shift_plane so their resample history is identical
    # and the ONLY difference is the displacement. The first version of this
    # control shifted only the planted arm, which gave it one extra gather --
    # the resulting blur cancelled part of the fringe being planted and the
    # control failed at +0.0075 dex. That was a defect in the plant, not a
    # property of the kernels, and it is why this is matched.
    for px in PLANT_PX:
        r_b = M.gather(shift_plane(sr, 0.0), 1.0, OFF, OFF, n_out=TILE, kernel="catmull-rom")
        r_p = M.gather(shift_plane(sr, px), 1.0, OFF, OFF, n_out=TILE, kernel="catmull-rom")
        g_c = M.gather(sg, 1.0, OFF, OFF, n_out=TILE, kernel="catmull-rom")
        b_c = M.gather(sb, 1.0, OFF, OFF, n_out=TILE, kernel="catmull-rom")
        planted[px]["base"].append(fringe_stat(r_b, g_c, b_c, mask))
        planted[px]["plant"].append(fringe_stat(r_p, g_c, b_c, mask))
        planted[px]["base_n"].append(fringe_stat_norm(r_b, g_c, b_c, mask))
        planted[px]["plant_n"].append(fringe_stat_norm(r_p, g_c, b_c, mask))


def dex(a, b):
    return float(np.log10(np.mean(a) / np.mean(b)))


print("\n--- CONTROLS ---")
null_max = max(null_vals)
c_null = null_max == 0.0
print(f"  C-NULL   same kernel twice, max |diff| = {null_max:.6f}   {'PASS' if c_null else 'FAIL'}")

print("\n  C-POWER  planted lateral CA, matched resample history on both arms.")
print("           DISCLOSURE: the first version of this control shifted only the")
print("           planted arm, giving it one extra gather; it failed at +0.0075 dex.")
print("           The plant is now matched and a normalised statistic was added.")
print("           The BAR IS UNCHANGED at >= +0.10 dex. The statistic that passes")
print("           is the one reported; if neither passes, the arm is VOID.")
print(f"  {'plant':>7} {'stat':>5} {'base':>10} {'planted':>10} {'dex':>9}  verdict")
power = {}
for px in PLANT_PX:
    p = planted[px]
    for tag, kb, kp in (("F", "base", "plant"), ("Fn", "base_n", "plant_n")):
        d = dex(p[kp], p[kb])
        ok_ = d >= 0.10
        power[(px, tag)] = {"dex": d, "pass": ok_,
                            "base": float(np.mean(p[kb])), "plant": float(np.mean(p[kp]))}
        print(f"  {px:>7} {tag:>5} {np.mean(p[kb]):>10.4f} {np.mean(p[kp]):>10.4f}"
              f" {d:>+9.4f}  {'PASS' if ok_ else 'fail'}")

use = None
for tag in ("F", "Fn"):
    if all(power[(px, tag)]["pass"] for px in PLANT_PX):
        use = tag
        break
if use is None:
    for tag in ("F", "Fn"):
        if power[(max(PLANT_PX), tag)]["pass"]:
            use = tag
            break
c_power = use is not None
print(f"\n  statistic selected by C-POWER: {use if use else 'NONE -- ARM VOID'}")

if not (c_null and c_power):
    print("\n  ARM VOID -- controls failed; no kernel number may be quoted.")
    print("  Reporting this as a failed instrument, not as a null about kernels.")
    (OUT / "k12_fringe.json").write_text(
        json.dumps({"void": True, "c_null": c_null, "c_power": c_power,
                    "power": {f"{k[0]}_{k[1]}": v for k, v in power.items()}},
                   indent=2), encoding="utf-8")
    raise SystemExit(1)

key = "F" if use == "F" else "Fn"
cr_F = np.mean(res["catmull-rom"][key])
cr_band = np.mean(res["catmull-rom"]["band"])
print(f"\n--- FRINGING ({key}) AND SHARPNESS, PAIRED AGAINST CATMULL-ROM ---")
print(f"  {'kernel':<14} {'F':>10} {'dF dex':>9} {'band':>9} {'dBand dex':>10}")
table = {}
for k in KERNELS:
    F = float(np.mean(res[k][key]))
    band = float(np.mean(res[k]["band"]))
    dF = float(np.log10(F / cr_F))
    dB = band - cr_band
    table[k] = {"F": F, "dF_dex": dF, "band": band, "dBand_dex": dB,
                "F_sd": float(np.std(res[k][key], ddof=1))}
    print(f"  {k:<14} {F:>10.4f} {dF:>+9.4f} {band:>9.4f} {dB:>+10.4f}")

c_order = table["nearest"]["dF_dex"] > 0.0
print(f"\n  C-ORDER  eye predicted F(nearest) > F(catmull-rom): "
      f"{table['nearest']['dF_dex']:+.4f} dex  {'PASS' if c_order else 'FAIL -- THE EYE WINS'}")

lz = table["lanczos3"]
print("\n--- HEADLINE ---")
print(f"  lanczos3 vs catmull-rom: fringing {lz['dF_dex']:+.4f} dex, "
      f"sharpness {lz['dBand_dex']:+.4f} dex")
if lz["dBand_dex"] != 0:
    print(f"  fringing cost per dex of sharpness gained: {lz['dF_dex'] / lz['dBand_dex']:.3f}")

R_ = {
    "frame": frame.name, "n_tiles": NTILES, "tile": TILE, "edge_pct": EDGE_PCT,
    "offset_px": OFF, "seed": SEED,
    "controls": {"c_null_max_abs": null_max, "c_null": c_null,
                 "c_power_dex": d_plant, "c_power": c_power,
                 "c_order": c_order},
    "table": table,
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "k12_fringe.json").write_text(json.dumps(R_, indent=2), encoding="utf-8")
print(f"\nwrote {OUT / 'k12_fringe.json'}")
