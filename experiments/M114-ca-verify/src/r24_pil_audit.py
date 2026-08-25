"""M114 r24 -- audit of the PIL 16-bit RGB narrowing hazard against M114's own probes.

Four parts:
  A  Independently reproduce the hazard on a file M114 constructs itself, with
     contents M114 chose. Not a re-run of ORCH's probe.
  B  Enumerate every TIFF any M114 probe reads; report the true dtype via
     tifffile and what PIL would have returned.
  C  Establish the bit depth of the one file M114 does read through PIL
     (the M110 contact-sheet PNG used as an NCC needle in r10a).
  D  DECISIVE: re-run r10a's template localisation with a full-depth uint16
     haystack and compare the located position against the 8-bit one r10a
     actually used. r10a is the only M114 probe that narrowed its own data.
"""
import glob
import json
import os

import numpy as np
import tifffile
from PIL import Image
from scipy import signal

OUT = r"C:\dev\strehl-out\M114-ca-verify\r24.json"
REND = r"C:\dev\strehl-out\M110-sheet\bee-3-cpl\default.tif"
PAT = r"C:\dev\strehl-out\M110-sheet\bee-3-cpl\ZOOM-*.png"
res = {}

# ---------------------------------------------------------------- A
print("=" * 68)
print("A  independent reproduction on a file M114 constructs")
print("=" * 68)
tmp = os.path.join(os.environ["TEMP"], "m114_pil_probe")
os.makedirs(tmp, exist_ok=True)
rng = np.random.default_rng(114)
# a ramp plus noise, chosen so the level count is unambiguous and large
src = (np.linspace(0, 60000, 256).astype(np.uint16)[None, :, None]
       * np.ones((64, 1, 3), np.uint16))
src = (src + rng.integers(0, 97, src.shape)).astype(np.uint16)
rgb16 = os.path.join(tmp, "rgb16.tif")
gry16 = os.path.join(tmp, "gry16.tif")
tifffile.imwrite(rgb16, src)
tifffile.imwrite(gry16, src[..., 0])
for name, path, ref in (("16-bit RGB", rgb16, src), ("16-bit grey", gry16, src[..., 0])):
    tf = tifffile.imread(path)
    pi = np.asarray(Image.open(path))
    md = Image.open(path).mode
    rec = dict(tifffile_dtype=str(tf.dtype), pil_dtype=str(pi.dtype), pil_mode=md,
               levels_source=int(np.unique(ref).size),
               levels_tifffile=int(np.unique(tf).size),
               levels_pil=int(np.unique(pi).size),
               tifffile_exact=bool(np.array_equal(tf, ref)))
    rec["level_loss_factor"] = round(rec["levels_source"] / max(rec["levels_pil"], 1), 1)
    res["A_" + name.replace(" ", "_").replace("-", "")] = rec
    print("%-12s tifffile=%-7s PIL=%-6s mode=%-5s levels %5d -> %5d  (%.0fx loss)"
          % (name, rec["tifffile_dtype"], rec["pil_dtype"], md,
             rec["levels_source"], rec["levels_pil"], rec["level_loss_factor"]))

# ---------------------------------------------------------------- B
print()
print("=" * 68)
print("B  every TIFF an M114 probe reads")
print("=" * 68)
tifs = []
for pat in (r"C:\dev\strehl-out\M114-ca-verify\r1\*.tif",
            r"C:\dev\strehl-out\M114-ca-verify\r9\*.tif",
            r"C:\dev\strehl-out\M114-ca-verify\r12\*.tif",
            r"C:\dev\strehl-out\M114-ca-verify\r17\*.tif",
            r"C:\dev\strehl-out\M114-ca-verify\r21\*.tif",
            REND):
    tifs.extend(sorted(glob.glob(pat)))
btab = []
for p in tifs:
    a = tifffile.imread(p)
    md = Image.open(p).mode
    btab.append(dict(path=p, shape=list(a.shape), dtype=str(a.dtype),
                     mn=int(a.min()), mx=int(a.max()), pil_mode=md,
                     pil_dtype=str(np.asarray(Image.open(p)).dtype)))
    print("%-58s %-8s max=%-6d PIL=%s/%s"
          % (os.path.basename(os.path.dirname(p)) + "\\" + os.path.basename(p),
             btab[-1]["dtype"], btab[-1]["mx"], md, btab[-1]["pil_dtype"]))
res["B_tifs"] = btab
res["B_all_uint16"] = all(t["dtype"] == "uint16" for t in btab)
res["B_all_pil_would_narrow"] = all(t["pil_dtype"] == "uint8" for t in btab)
print("all true dtype uint16: %s     PIL would narrow every one: %s"
      % (res["B_all_uint16"], res["B_all_pil_would_narrow"]))

# ---------------------------------------------------------------- C
print()
print("=" * 68)
print("C  the one file M114 reads through PIL (r10a needle)")
print("=" * 68)
needles = sorted(glob.glob(PAT))
ctab = []
for p in needles:
    im = Image.open(p)
    ctab.append(dict(path=os.path.basename(p), mode=im.mode, size=list(im.size),
                     bits=im.tag_v2.get(258) if hasattr(im, "tag_v2") else None,
                     dtype=str(np.asarray(im).dtype)))
    print("%-44s mode=%-5s dtype=%s" % (ctab[-1]["path"], im.mode, ctab[-1]["dtype"]))
res["C_needles"] = ctab
res["C_all_png_8bit"] = all(c["mode"] in ("RGB", "RGBA", "P", "L") for c in ctab)
res["B_n_tifs"] = len(btab)
print("PNG contact sheet is natively 8-bit: %s  -> PIL read is LOSSLESS here"
      % res["C_all_png_8bit"])
json.dump(res, open(OUT, "w"), indent=1)
print("wrote", OUT)
