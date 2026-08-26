"""Commission the WHOLE measurement chain, not just the statistics.

commission.py fools the statistics. This fools the pipeline: registration,
site selection on the mean of two arms, native-pixel tile extraction, the
geometry handicap, all of it.

The measured result is near-parity between the two arms. Near-parity is
exactly what a chain that has quietly gone inert also reports. So the chain is
fed two synthetic subjects whose answer is known before it runs:

  CTRL-identity    the "argmax" arm IS the merge arm, byte for byte.
                   Every gain must be 1.000. Anything else is the chain
                   inventing a difference out of registration slop.

  CTRL-blur0.8     the "argmax" arm is the merge arm Gaussian-blurred by 0.8
                   px. The merge arm is known-sharper by construction, so every
                   gain must be clearly ABOVE 1. If the chain cannot see a
                   0.8 px blur through its own registration and site selection,
                   it cannot see a 1.2x detail claim either, and its
                   near-parity finding would mean nothing.

  CTRL-blur1.5     the same at 1.5 px, to show the chain scales with the size
                   of the effect rather than merely having a sign.

These write into the same renders/ tree measure.py reads, under names that
begin with CTRL- so they cannot be mistaken for a subject.
"""
import json
import pathlib
import shutil
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

RENDERS = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")


def build(src_subject, name, sigma):
    s = RENDERS / src_subject
    d = RENDERS / name
    d.mkdir(parents=True, exist_ok=True)

    img = tifffile.imread(str(s / "merge.tif"))
    assert img.dtype == np.uint16
    tifffile.imwrite(str(d / "merge.tif"), img)

    if sigma <= 0:
        alt = img
    else:
        alt = np.empty_like(img)
        for c in range(img.shape[2]):
            alt[:, :, c] = np.clip(
                gaussian_filter(img[:, :, c].astype(np.float32), sigma),
                0, 65535).astype(np.uint16)
    tifffile.imwrite(str(d / "argmax.tif"), alt)

    # the control's "argmax" arm is a synthetic image, so there is no coverage
    # rescale to undo: the two arms sit on the same grid. Report FOV 1.0 so the
    # geometry handicap is a no-op and cannot mask the planted effect.
    (d / "merge.err").write_text(
        f"synthetic control derived from {src_subject}\n"
        f"  field of view scaled to 1.0000 (control: both arms share one grid)\n",
        encoding="utf8")

    prov = json.loads((s / "merge.provenance.json").read_text(encoding="utf8"))
    for arm in ("merge", "argmax"):
        p = dict(prov)
        p["arm"] = arm
        p["subject"] = name
        p["synthetic"] = f"blur sigma {sigma}" if sigma > 0 else "identity"
        (d / f"{arm}.provenance.json").write_text(json.dumps(p, indent=1), encoding="utf8")
    print(f"built {d}  (blur sigma {sigma})")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "leaf-2-cpl"
    build(src, "CTRL-identity", 0.0)
    build(src, "CTRL-blur0.8", 0.8)
    build(src, "CTRL-blur1.5", 1.5)
    print("\nnow run:  python experiments\\BUILD-THESIS\\measure.py "
          "CTRL-identity CTRL-blur0.8 CTRL-blur1.5")


if __name__ == "__main__":
    main()
