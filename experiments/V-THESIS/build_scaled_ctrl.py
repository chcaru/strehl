"""The whole-chain control BUILD-THESIS did not run: a planted blur ACROSS the rescale.

Their CTRL-identity / CTRL-blur0.8 / CTRL-blur1.5 all carry
    "field of view scaled to 1.0000 (control: both arms share one grid)"
so the chain was commissioned with the registration confound switched OFF. The
confound that threatens the headline is precisely a 7-10% rescale between arms,
and no control ever exercised it.

This builds three synthetic subjects where BOTH the scale AND the blur are known:

    argmax_syn = warp(gauss_exact(merge, sigma), scale s about the centre)

so a feature at merge pixel p sits at s*p + c(1-s) in the synthetic arm -- the
same sense as the real arms, where `stack` crops the field to s and upsamples
back. Blur is applied BEFORE the resample, so sigma is a scene blur expressed in
merge pixels, which is what the headline reports.

  VCTRL-s-blur0.0   truth 0.000 px  <- ANY non-zero reading here is registration
                                       error being scored as detail
  VCTRL-s-blur0.4   truth 0.400 px  <- about the size of the reported effect
  VCTRL-s-blur0.8   truth 0.800 px  <- their own control's size, now across scale

Only NEW directories are created. No existing BUILD-THESIS file is touched.
"""
import json, pathlib, shutil, sys
import numpy as np, tifffile, cv2

sys.path.insert(0, str(pathlib.Path("experiments/V-THESIS").resolve()))
from vplant import gauss_exact  # noqa: E402

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
SRC = "leaf-2-cpl"          # their control's source subject
S = 0.9342                  # its logged field-of-view scale
PLANTS = [0.0, 0.4, 0.8]


def build(sigma):
    name = f"VCTRL-s-blur{sigma:.1f}"
    d = R / name
    d.mkdir(parents=True, exist_ok=True)
    img = tifffile.imread(str(R / SRC / "merge.tif"))
    assert img.dtype == np.uint16
    tifffile.imwrite(str(d / "merge.tif"), img)

    h, w = img.shape[:2]
    cy, cx = h / 2.0, w / 2.0
    M = np.array([[S, 0.0, cx * (1 - S)], [0.0, S, cy * (1 - S)]], dtype=np.float64)
    alt = np.empty_like(img)
    for c in range(img.shape[2]):
        ch = img[:, :, c].astype(np.float64)
        if sigma > 0:
            ch = gauss_exact(ch, sigma)
        wp = cv2.warpAffine(ch, M, (w, h), flags=cv2.INTER_LANCZOS4,
                            borderMode=cv2.BORDER_REPLICATE)
        alt[:, :, c] = np.clip(wp, 0, 65535).astype(np.uint16)
    tifffile.imwrite(str(d / "argmax.tif"), alt)

    (d / "merge.err").write_text(
        f"synthetic scaled control derived from {SRC}\n"
        f"  planted scene blur {sigma:.3f} px, applied before the resample\n"
        f"  field of view scaled to {S:.4f} so that EVERY frame covers every pixel\n",
        encoding="utf8")
    prov = json.loads((R / SRC / "merge.provenance.json").read_text(encoding="utf8"))
    for arm in ("merge", "argmax"):
        p = dict(prov); p["arm"] = arm; p["subject"] = name
        p["synthetic"] = f"blur {sigma} px THEN scale {S}"
        (d / f"{arm}.provenance.json").write_text(json.dumps(p, indent=1), encoding="utf8")
    print(f"built {name}: planted blur {sigma:.1f} px across a {(1-S)*100:.1f}% rescale")


for s in PLANTS:
    build(s)
print("\nnow run their chain on these three names")
