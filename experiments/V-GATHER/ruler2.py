"""Why does RU1 not reproduce BUILD-SHARP's 30.44 um on the shipping tree?
Candidate: M99 photometric normalisation, which is ON BY DEFAULT 'since V-TONE'
and did not exist at BUILD-SHARP's pin. One render, --photometric off."""
import os, subprocess, sys, time
from pathlib import Path
import numpy as np
REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
sys.path.insert(0, str(REPO / "experiments" / "M88b-merge-sharpness" / "src"))
sys.path.insert(0, str(REPO / "experiments" / "M88-optical-ceiling" / "src"))
import m88blib as M
EXE = r"C:\dev\strehl-out\V-GATHER\strehl-pinned.exe"
OUT = Path(r"C:\dev\strehl-out\V-GATHER\esf")
RU1 = (1952, 1632, 96, 96); AXIS = "vertical"
tif = OUT / "highly-angled-ruler-mm-cpl--cr-plane-photoff.tif"
if not tif.exists():
    env = dict(os.environ)
    env.update(STREHL_ALIGN="1", STREHL_FULLRES_GATHER="0", STREHL_FIX_CA="off",
               STREHL_CACHE_DIR=str(OUT / "warpcache-catmull-rom"))
    env.pop("STREHL_WARPMAP", None)
    t0 = time.perf_counter()
    r = subprocess.run([EXE, "stack", r"D:\personal\macro\highly-angled-ruler-mm-cpl",
                        "--out", str(tif), "--gate", "0", "--resampler", "catmull-rom",
                        "--photometric", "off"], env=env, capture_output=True, text=True)
    print(f"render rc={r.returncode} {time.perf_counter()-t0:.1f}s")
    if r.returncode != 0: print((r.stdout+r.stderr)[-700:]); raise SystemExit(1)
base = M.read_merge_plane(OUT / "highly-angled-ruler-mm-cpl--cr-plane.tif", "G")
off  = M.read_merge_plane(tif, "G")
print(f"photometric on vs off, arrays identical: {np.array_equal(base, off)}")
for lab, arr in (("photometric ON  (shipping default)", base),
                 ("photometric OFF (BUILD-SHARP-era)", off)):
    d = M.measure_roi(arr, RU1, AXIS) if hasattr(M, "measure_roi") else None
    if d is None or d.get("error"):
        d = M.paired_delta_registered(arr, arr, RU1, AXIS)
        print(f"  {lab:36s} rise = {d['rise_off_um']:8.3f} um  contrast {d['contrast_off']:8.0f}")
    else:
        print(f"  {lab:36s} rise = {d.get('rise_um', float('nan')):8.3f} um")
print("\n  BUILD-SHARP stored: b-g0-cr RU1 = 30.334 um, b-g4-cr RU1 = 30.441 um")
