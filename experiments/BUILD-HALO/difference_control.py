"""ORCH's differencing control, with the two reference frames chosen FROM DATA.

  stack - frame(k_bg)      -> the SELECTION artifact alone.
                              The background gradient, the lighting falloff and
                              the optical veil are all common to both terms and
                              cancel.  Whatever survives, selection put there.

  frame(k_bg) - frame(k_fg) -> the VEIL alone, and its radial extent measures
                              the optical blur scale directly.

k_bg and k_fg are not guessed.  The election map records which frame each pixel
actually elects, so the far background's median election IS the
background-focused frame and the subject's median election IS the
subject-focused one.

Reported as differences in DN-equivalent (x65535) so the numbers are commensurate
with ORCH's scanline figures.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).parent))
from depth_profile import OUT, SOBEL_RADIUS, WINDOW_RADIUS, depth_mask, luma  # noqa: E402

EXE = Path(r"C:\dev\blog\death-of-software\projects\strehl\target\release\strehl.exe")
LIB = Path(r"D:\personal\macro")
SUPPORT = SOBEL_RADIUS + WINDOW_RADIUS
BANDS = [(1, 8), (8, 14), (14, 20), (20, 28), (28, 36), (36, 46), (46, 60),
         (60, 80), (80, 110), (110, 150), (150, 210), (210, 300), (300, 420)]


def ensure_frame(subject, k):
    p = OUT / f"{subject}-f{k:03d}.tif"
    if p.exists():
        return p
    env = {**dict(__import__("os").environ), "STREHL_ONLY_FRAME": str(k)}
    env.pop("STREHL_EDGE_AWARE", None)
    print(f"  rendering {subject} frame {k} ...", flush=True)
    r = subprocess.run([str(EXE), "stack", str(LIB / subject), "--out", str(p)],
                       env=env, capture_output=True)
    if r.returncode != 0 or not p.exists():
        sys.exit(f"failed to render {subject} f{k}:\n"
                 f"{r.stderr.decode('utf-8','replace')[-1500:]}")
    return p


def profile(img, d, m, label):
    print(f"\n  {label}")
    print(f"  {'band':>12} {'n':>10} {'median DN':>12} {'rel far':>10}")
    print("  " + "-" * 49)
    rows = []
    for a, b in zip([x[0] for x in BANDS], [x[1] for x in BANDS]):
        sel = (d >= a) & (d < b) & ~m
        if sel.sum() < 300:
            continue
        v = float(np.median(img[sel])) * 65535.0
        rows.append((0.5 * (a + b), v, int(sel.sum())))
    # Frames differ by a global exposure offset, so the raw difference carries a
    # large DC term that buries the local structure. Reference every band to the
    # OUTERMOST band: the DC cancels, and so does any gradient common to the two
    # terms being differenced -- which is ORCH's defect 2.
    dc = rows[-1][1]
    out = []
    for c, v, n in rows:
        a = int(c - 0.5) if False else None  # noqa
        mark = "  <-- window support" if abs(c - SUPPORT) <= 3 else ""
        print(f"  {c:>12.0f} {n:>10} {v:>12.2f} {v-dc:>+10.2f}{mark}")
        out.append((c, v - dc))
    print(f"  (referenced to the outermost band, {dc:+.2f} DN)")
    return out


def extremum(rows, label):
    if len(rows) < 3:
        return
    c = np.array([r[0] for r in rows])
    v = np.array([r[1] for r in rows])
    i = int(np.argmax(np.abs(v)))
    print(f"\n  {label}: peak |value| {v[i]:+.2f} DN at d={c[i]:.0f} px "
          f"(window support {SUPPORT})")
    # local interior extremum, excluding the first band (edge contamination)
    inner = v[1:-1]
    if len(inner):
        j = int(np.argmax(np.abs(inner))) + 1
        print(f"  interior extremum (band 2..n-1): {v[j]:+.2f} DN at d={c[j]:.0f} px"
              f"   ratio to support = {c[j]/SUPPORT:.2f}x")


def run(subject):
    emap = OUT / f"{subject}-election.tif"
    stack_p = OUT / f"{subject}-stacked.tif"
    if not emap.exists() or not stack_p.exists():
        sys.exit(f"missing election map or stacked render for {subject}")

    elect = tifffile.imread(str(emap))
    if elect.ndim == 3:
        elect = elect[..., 0]
    m, _ = depth_mask(elect)
    d = ndimage.distance_transform_edt(~m)

    valid = elect != 65535
    far = (d > 500) & ~m & valid
    k_bg = int(np.median(elect[far]))
    k_fg = int(np.median(elect[m & valid]))
    print(f"\n{'='*74}\n{subject}\n{'='*74}")
    print(f"depth mask {m.mean():.1%}")
    print(f"far background elects frame {k_bg} (median over {far.sum():,} px)")
    print(f"subject         elects frame {k_fg} (median over {(m&valid).sum():,} px)")
    if k_bg == k_fg:
        print("  !! background and subject elect the SAME frame -- the veil term")
        print("     cannot be formed and this subject cannot discriminate.")

    S = luma(stack_p)
    Bp, Fp = ensure_frame(subject, k_bg), ensure_frame(subject, k_fg)
    B, F = luma(Bp), luma(Fp)

    sel_art = profile(S - B, d, m, f"SELECTION ARTIFACT: stack - frame({k_bg})")
    extremum(sel_art, "selection artifact")

    if k_bg != k_fg:
        veil = profile(B - F, d, m, f"VEIL: frame({k_bg}) - frame({k_fg})")
        extremum(veil, "veil")

        sa = np.array([abs(v) for _, v in sel_art])
        vl = np.array([abs(v) for _, v in veil])
        print(f"\n  peak |selection artifact| : {sa.max():.2f} DN")
        print(f"  peak |veil|               : {vl.max():.2f} DN")
        print(f"  ratio veil/selection      : {vl.max()/max(sa.max(),1e-9):.2f}x")
        print("\n  ORCH's discriminator:")
        print("   - narrow ring in SELECTION + wide skirt in VEIL -> S3 right,")
        print("     target the skirt, selection cannot fix it.")
        print("   - SELECTION carries the whole halo, VEIL negligible -> S3 wrong,")
        print("     suppressing the rim IS the correct fix.")


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["lavendar-cpl", "flower-bud-with-background-fern-cpl"]):
        run(s)
