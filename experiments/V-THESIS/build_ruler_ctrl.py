"""Finding #2 says selection wins ~0.4 px on flat-on-ruler-cpl, all three
statistics agreeing. That subject's own field-of-view scale is 0.9707.

Build the matched control: flat-on-ruler's OWN merge arm against a synthetic
partner at flat-on-ruler's OWN scale, with ZERO blur planted. Truth = 0.000 px.
Whatever their chain reports there is what its geometry alone manufactures on
that subject. If it reports about -0.4 px on all three, finding #2 is geometry.
"""
import json, pathlib, sys
import numpy as np, tifffile, cv2

sys.path.insert(0, str(pathlib.Path("experiments/V-THESIS").resolve()))
from vplant import gauss_exact  # noqa: E402

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
SRC = "flat-on-ruler-cpl"
S = 0.9707


def build(sigma, tag):
    d = R / tag
    d.mkdir(parents=True, exist_ok=True)
    img = tifffile.imread(str(R / SRC / "merge.tif"))
    tifffile.imwrite(str(d / "merge.tif"), img)
    h, w = img.shape[:2]
    cy, cx = h / 2.0, w / 2.0
    M = np.array([[S, 0.0, cx * (1 - S)], [0.0, S, cy * (1 - S)]], dtype=np.float64)
    alt = np.empty_like(img)
    for c in range(img.shape[2]):
        ch = img[:, :, c].astype(np.float64)
        if sigma > 0:
            ch = gauss_exact(ch, sigma)
        alt[:, :, c] = np.clip(
            cv2.warpAffine(ch, M, (w, h), flags=cv2.INTER_LANCZOS4,
                           borderMode=cv2.BORDER_REPLICATE), 0, 65535).astype(np.uint16)
    tifffile.imwrite(str(d / "argmax.tif"), alt)
    (d / "merge.err").write_text(
        f"synthetic scaled control derived from {SRC}\n"
        f"  planted scene blur {sigma:.3f} px, applied before the resample\n"
        f"  field of view scaled to {S:.4f} so that EVERY frame covers every pixel\n",
        encoding="utf8")
    prov = json.loads((R / SRC / "merge.provenance.json").read_text(encoding="utf8"))
    for arm in ("merge", "argmax"):
        p = dict(prov); p["arm"] = arm; p["subject"] = tag
        (d / f"{arm}.provenance.json").write_text(json.dumps(p, indent=1), encoding="utf8")
    print(f"built {tag}: {SRC} geometry, scale {S}, planted blur {sigma:.1f} px")


build(0.0, "VCTRL-r-blur0.0")
build(0.4, "VCTRL-r-blur0.4")

print("\n=== their stated yardstick, from their own limits.json ===")
lim = json.loads((pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS") / "limits.json").read_text(encoding="utf8"))
print(json.dumps(lim, indent=1)[:2000])
