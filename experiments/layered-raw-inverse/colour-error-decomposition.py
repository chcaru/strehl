"""Read-only orthogonal scale/phase decomposition of saved camera-colour errors."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ORIGINS = ((0, 0), (1, 0), (0, 1), (1, 1))  # x,y; basis changes, not image warps


def block_projection(error, size):
    h, w, channels = error.shape
    means = error.reshape(h//size, size, w//size, size, channels).mean(axis=(1, 3))
    return np.repeat(np.repeat(means, size, axis=0), size, axis=1)


def decompose(error):
    """Finite HxWx2 error, axes divisible by4; all four common-domain phase bases."""
    error = np.asarray(error, dtype=np.float64)
    if error.ndim != 3 or error.shape[2] != 2 or min(error.shape[:2]) < 4 or any(n % 4 for n in error.shape[:2]) or not np.isfinite(error).all():
        raise ValueError("expected finite HxWx2 error with spatial dimensions divisible by4")
    signed_mean = error.mean(axis=(0, 1))
    total = np.mean(error*error, axis=(0, 1))
    phases = []
    for x, y in ORIGINS:
        rolled = np.roll(error, shift=(-y, -x), axis=(0, 1))
        p2, p4 = block_projection(rolled, 2), block_projection(rolled, 4)
        within = np.mean((rolled-p2)**2, axis=(0, 1))
        between = np.mean((p2-p4)**2, axis=(0, 1))
        common = np.mean(p4**2, axis=(0, 1))
        common_ac = np.mean((p4-signed_mean)**2, axis=(0, 1))
        residual = within+between+common-total
        dc_residual = common_ac+signed_mean**2-common
        tolerance = 1e-11*np.maximum(1, total)
        if np.any(np.abs(residual) > tolerance) or np.any(np.abs(dc_residual) > tolerance):
            raise AssertionError("orthogonal projection energy did not conserve total")
        phases.append(dict(origin_xy=[x, y], within2_mean_square=within.tolist(),
            between2_4_mean_square=between.tolist(), common4_mean_square=common.tolist(),
            common4_ac_mean_square=common_ac.tolist(), dc_mean_square=(signed_mean**2).tolist(),
            parseval_error=residual.tolist(), common_dc_split_error=dc_residual.tolist()))
    return dict(shape=list(error.shape), coordinates=["R-G error", "B-G error"],
        signed_mean=signed_mean.tolist(), total_mean_square=total.tolist(),
        chroma_rmse=float(np.sqrt(np.mean(total))), phases=phases)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source, out = HERE/"screen-1"/"output", args.out.resolve()
    arms = {"visibility": HERE/"visibility-1"/"output", "shot": HERE/"shot-prior-1"/"output",
            "cauchy": HERE/"cauchy-1"/"output"}
    files = [source/case/"truth-rgb-f32.npy" for case in ("flat", "layered")]
    files += [root/case/"fixed-alpha"/"reconstruction.npz" for root in arms.values() for case in ("flat", "layered")]
    before = {str(p): sha(p) for p in files}
    records = []
    for case in ("flat", "layered"):
        truth_path = source/case/"truth-rgb-f32.npy"
        truth = np.load(truth_path, allow_pickle=False)
        if truth.dtype != np.float32 or truth.shape != (96, 96, 3) or not np.isfinite(truth).all():
            raise ValueError("unexpected frozen truth array")
        for arm, root in arms.items():
            path = root/case/"fixed-alpha"/"reconstruction.npz"
            with np.load(path, allow_pickle=False) as data:
                image = data["pinhole_rgb"].copy()
            if image.dtype != np.float32 or image.shape != truth.shape or not np.isfinite(image).all():
                raise ValueError("unexpected saved pinhole array")
            # Exactly the retained scalar score's arithmetic and supported domain.
            delta = image[16:80, 16:80].astype(np.float64)-truth[16:80, 16:80].astype(np.float64)
            error = np.stack((delta[..., 0]-delta[..., 1], delta[..., 2]-delta[..., 1]), axis=-1)
            records.append(dict(case=case, arm=arm, decomposition=decompose(error), source_path=str(path),
                source_sha256=before[str(path)], truth_path=str(truth_path), truth_sha256=before[str(truth_path)]))
    after = {str(p): sha(p) for p in files}
    if before != after:
        raise AssertionError("saved inputs changed")
    out.mkdir(parents=True, exist_ok=False)
    result = dict(status="COLOUR_ERROR_DECOMPOSITION_COMPLETE", support_native_xywh=[16, 16, 64, 64],
        records=records, source_bindings_before=before, source_bindings_after=after,
        sources_unchanged=True, real_photo_admission=False,
        phase_convention="origin[x,y] rolls supported error by[-y,-x]; circular boundary pairs are artificial",
        interpretation="Exact common-domain energy partition, not independent samples or a CFA-null cause test.")
    save(out/"result.json", result)
    print("COLOUR_ERROR_DECOMPOSITION", json.dumps(dict(status=result["status"], records=len(records))), flush=True)


if __name__ == "__main__":
    main()
