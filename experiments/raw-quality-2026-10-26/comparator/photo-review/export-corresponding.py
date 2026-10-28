"""Locate matching landmarks only; deliver unresampled original native pixels."""
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np
from PIL import Image
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FROZEN = ROOT / "experiments/raw-quality-2026-10-26/photo-review/baseline-witnesses.json"
BASE = ROOT / "outputs/raw-quality-2026-10-26/weevil-107-baseline"
COMP = ROOT / "outputs/raw-quality-2026-10-26/weevil-107-comparator"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    with tifffile.TiffFile(p) as f:
        pixels = f.asarray()
        icc = bytes(f.pages[0].tags[34675].value)
    assert pixels.dtype == np.uint16 and pixels.shape[2] == 3
    return pixels, icc


def locate(a, b):
    # Both images use exactly1/4 native pixel scale, not independently fit sizes.
    def reduced(x):
        small = cv2.resize(x, None, fx=.25, fy=.25, interpolation=cv2.INTER_AREA)
        return cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    aa, bb = reduced(a), reduced(b)
    sift = cv2.SIFT_create(nfeatures=5000)
    ak, ad = sift.detectAndCompute(aa, None)
    bk, bd = sift.detectAndCompute(bb, None)
    pairs = cv2.BFMatcher().knnMatch(ad, bd, k=2)
    pairs = [m for m, n in pairs if m.distance < .72*n.distance]
    ap = np.float64([ak[m.queryIdx].pt for m in pairs])*4
    bp = np.float64([bk[m.trainIdx].pt for m in pairs])*4
    cv2.setRNGSeed(719)
    matrix, inlier = cv2.estimateAffinePartial2D(ap, bp, method=cv2.RANSAC,
        ransacReprojThreshold=5, maxIters=2000, confidence=.99, refineIters=10)
    assert matrix is not None and inlier.sum() >= 30
    inlier = inlier[:, 0].astype(bool)
    residual = np.linalg.norm(ap @ matrix[:, :2].T+matrix[:, 2]-bp, axis=1)
    scale = float(np.linalg.norm(matrix[:, 0]))
    assert .95 < scale < 1.05, "locator is not a plausible whole-image similarity"
    wrong = matrix.copy()
    wrong[:, 2] += 100
    wrong_error = np.linalg.norm(ap[inlier] @ wrong[:, :2].T+wrong[:, 2]-bp[inlier], axis=1)
    assert np.median(wrong_error) > 100, "wrong-translation locator control is inert"
    return matrix, ap[inlier], bp[inlier], {
        "native_baseline_to_vendor_matrix": matrix.tolist(), "scale": scale,
        "rotation_degrees": float(np.degrees(np.arctan2(matrix[1,0], matrix[0,0]))),
        "matches": len(pairs), "inliers": int(inlier.sum()),
        "native_inlier_error_median": float(np.median(residual[inlier])),
        "native_inlier_error_p95": float(np.quantile(residual[inlier], .95)),
        "wrong_100px_xy_translation_error_median": float(np.median(wrong_error)),
        "purpose": "landmark locator only, not a quality metric or accepted pixelwise registration",
    }


def main():
    start = time.monotonic()
    cv2.setNumThreads(2)
    frozen = json.loads(FROZEN.read_text())
    a, icc = read(BASE / "stack-master.tiff")
    assert sha(BASE / "stack-master.tiff") == frozen["master"]["sha256"]
    a8 = ((a.astype(np.uint32)+128)//257).astype(np.uint8)
    receipt = {"source_manifest_sha256": sha(FROZEN), "command": "python -X faulthandler experiments/raw-quality-2026-10-26/comparator/photo-review/export-corresponding.py", "arms": {}}
    for arm in ("b", "c"):
        p = COMP / arm / "stack-master.tiff"
        b, bicc = read(p)
        assert bicc == icc
        b8 = ((b.astype(np.uint32)+128)//257).astype(np.uint8)
        matrix, ap, bp, mapping = locate(a8, b8)
        dest = HERE / arm
        dest.mkdir(exist_ok=False)
        witnesses = []
        for w in frozen["witnesses"]:
            x, y, width, height = w["rect_xywh"]
            center = np.array([x+width/2, y+height/2])
            target = matrix[:, :2] @ center + matrix[:, 2]
            # Local matched-feature median corrects locator residual only. No pixel warp.
            near = np.linalg.norm(ap-center, axis=1) < 300
            local_delta = np.zeros(2)
            if near.sum() >= 3:
                local_delta = np.median(bp[near] - (ap[near] @ matrix[:, :2].T+matrix[:, 2]), axis=0)
                assert np.linalg.norm(local_delta) < 10
                target += local_delta
            bx, by = np.rint(target-[width/2, height/2]).astype(int)
            assert bx >= 0 and by >= 0 and bx+width <= b.shape[1] and by+height <= b.shape[0]
            pixels = b[by:by+height, bx:bx+width]
            out = dest / (w["name"]+".png")
            Image.fromarray(((pixels.astype(np.uint32)+128)//257).astype(np.uint8)).save(out, icc_profile=bicc)
            tiff = dest / (w["name"]+".tiff")
            tifffile.imwrite(tiff, pixels, photometric="rgb", metadata=None, extratags=[(34675,"B",len(bicc),bicc,False)])
            with Image.open(out) as check:
                assert np.array_equal(np.asarray(check), b8[by:by+height,bx:bx+width])
                assert check.info["icc_profile"] == bicc
            with tifffile.TiffFile(tiff) as check:
                assert np.array_equal(check.asarray(), pixels)
                assert bytes(check.pages[0].tags[34675].value) == bicc
            witnesses.append({"name":w["name"], "baseline_xywh":w["rect_xywh"],
                "vendor_xywh":[int(bx),int(by),width,height], "nearby_feature_inliers":int(near.sum()),
                "local_native_translation":local_delta.tolist(), "png":str(out), "png_sha256":sha(out),
                "tiff":str(tiff), "tiff_sha256":sha(tiff), "pixels_exact":True, "icc_exact":True})
        receipt["arms"][arm] = {"master":str(p), "master_sha256":sha(p), "native_dimensions":[b.shape[1],b.shape[0]],
            "icc_sha256":hashlib.sha256(bicc).hexdigest(), "mapping":mapping, "witnesses":witnesses}
        print(arm, json.dumps(mapping), flush=True)
        del b, b8
    receipt["elapsed_seconds"] = time.monotonic()-start
    receipt["display"] = "Unresampled384-square original subarrays; RGB16 round/257 for PNG; original ICC. Similarity only locates centers; physical footprints differ by fitted scale and local depth effects."
    (HERE/"correspondence.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print("completed",receipt["elapsed_seconds"],flush=True)


if __name__ == "__main__":
    main()
