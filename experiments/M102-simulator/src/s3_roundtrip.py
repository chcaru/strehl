"""M102 S3 -- score the round-trip against planted truth.

Runs the SHIPPED selector (`strehl argmax-baseline --index-map`) on a
generated stack and scores its per-pixel frame index against the index the
generator planted, on the pre-registered masks.

Geometry: this arm is run with breathing disabled and STREHL_ALIGN=0, so the
output grid is the latent grid binned 2x with no crop and no fitted
transform. Nothing here solves for a registration, so nothing here can absorb
a geometric defect -- which is what makes D2 a real plant.

Usage:
  python src/s3_roundtrip.py <stackdir> <tag>
"""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m102lib as M  # noqa: E402

STREHL = r"C:\dev\strehl-out\M100\vt2-target\release\strehl.exe"

# Pre-registered bars, PREREGISTRATION.md section 1.
BAR_R1 = 1.0     # median |index error|, frames
BAR_R2 = 0.90    # fraction within +/- 2 frames
BAR_R3 = 1.0     # |median signed error|, frames


def read_gray_tif(path):
    import struct
    with open(path, "rb") as fh:
        b = fh.read()
    assert b[:2] == b"II", "expected little-endian TIFF"
    off = struct.unpack_from("<I", b, 4)[0]
    n = struct.unpack_from("<H", b, off)[0]
    tags = {}
    for i in range(n):
        e = off + 2 + 12 * i
        tag, typ, cnt = struct.unpack_from("<HHI", b, e)
        tags[tag] = (typ, cnt, e + 8)
    def val(tag):
        typ, cnt, p = tags[tag]
        sz = {1: 1, 3: 2, 4: 4}[typ]
        if sz * cnt > 4:
            p = struct.unpack_from("<I", b, p)[0]
        f = {1: "B", 3: "H", 4: "I"}[typ]
        return list(struct.unpack_from("<" + f * cnt, b, p))
    w, h = val(256)[0], val(257)[0]
    bits = val(258)[0]
    assert bits == 16, bits
    so, sc = val(273), val(279)
    a = np.concatenate([
        np.frombuffer(b, dtype="<u2", count=c // 2, offset=o)
        for o, c in zip(so, sc)])
    return a[:w * h].reshape(h, w)


def bin2(a, how="median"):
    h, w = a.shape
    q = a[:h // 2 * 2, :w // 2 * 2].reshape(h // 2, 2, w // 2, 2)
    if how == "median":
        return np.median(q, axis=(1, 3))
    return q.any(axis=(1, 3))


def score(stackdir, tag, outdir=None):
    outdir = outdir or M.OUT
    os.makedirs(outdir, exist_ok=True)
    meta = json.load(open(os.path.join(stackdir, "truth.json")))
    z = np.load(os.path.join(stackdir, "truth.npz"))

    idx_path = os.path.join(M.WORK, f"{tag}_idx.tif")
    env = dict(os.environ, STREHL_ALIGN="0", PYTHONIOENCODING="utf-8")
    r = subprocess.run(
        [STREHL, "argmax-baseline", "--out", os.path.join(M.WORK,
         f"{tag}_amax.tif"), "--index-map", idx_path, stackdir],
        capture_output=True, text=True, env=env, timeout=3600)
    assert r.returncode == 0, r.stderr[-1500:]

    rec = read_gray_tif(idx_path).astype(float)
    truth = bin2(z["truth"])
    assert rec.shape == truth.shape, (rec.shape, truth.shape)

    res = {"tag": tag, "plant": meta["plant"], "seed": meta["seed"],
           "breathing": meta.get("breathing", True),
           "extra_tag": meta["extra_tag"], "shape": list(rec.shape)}
    err = rec - truth
    for name in ("textured", "smooth", "occ", "plane", "fg"):
        m = bin2(z[f"mask_{name}"], "any")
        if m.sum() < 50:
            continue
        e = err[m]
        res[name] = {
            "n": int(m.sum()),
            "median_abs": float(np.median(np.abs(e))),
            "median_signed": float(np.median(e)),
            "frac_within_2": float(np.mean(np.abs(e) <= 2.0)),
            "p90_abs": float(np.percentile(np.abs(e), 90)),
        }
    t = res["textured"]
    res["bars"] = {
        "R1_median_abs_le_1": bool(t["median_abs"] <= BAR_R1),
        "R2_frac_within2_ge_0.90": bool(t["frac_within_2"] >= BAR_R2),
        "R3_abs_median_signed_le_1": bool(abs(t["median_signed"]) <= BAR_R3),
    }
    res["bars"]["ALL_GREEN"] = all(res["bars"].values())
    res["index_map_sha"] = __import__("hashlib").sha256(
        rec.astype("<u2").tobytes()).hexdigest()[:16]
    with open(os.path.join(outdir, f"s3_{tag}.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    return res


def main():
    stackdir, tag = sys.argv[1], sys.argv[2]
    res = score(stackdir, tag)
    t = res["textured"]
    print(f"[{tag}] plant={res['plant']} breathing={res['breathing']} "
          f"tag={res['extra_tag']} sha={res['index_map_sha']}")
    print(f"  textured n={t['n']}  median|e|={t['median_abs']:.4f}  "
          f"median e={t['median_signed']:+.4f}  "
          f"within2={t['frac_within_2']:.4f}  p90={t['p90_abs']:.3f}")
    for k in ("smooth", "occ"):
        if k in res:
            d = res[k]
            print(f"  {k:9s} n={d['n']:6d}  median|e|={d['median_abs']:.4f}"
                  f"  median e={d['median_signed']:+.4f}"
                  f"  within2={d['frac_within_2']:.4f}")
    for k, v in res["bars"].items():
        print(f"  {'GREEN' if v else 'RED  '}  {k}")


if __name__ == "__main__":
    main()
