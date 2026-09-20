"""A separate fixed in-focus consumer of saved latent outputs; no fitting."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
MODEL_SHA = "5710146ffcf463de85e317050bc81357922965d6006c7b4cf311f4d80d8ee512"
SIGMA = float(np.float32(.7))
RADIUS = 3
spec = importlib.util.spec_from_file_location("in_focus_frozen_model", HERE/"model.py")
model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)


def apply_in_focus(image):
    """One original f32 CUDA PSF, full HWC input, signed finite values allowed."""
    image = np.asarray(image)
    if image.dtype != np.float32 or image.ndim != 3 or image.shape[2] != 3 or min(image.shape[:2]) < 7 or not np.isfinite(image).all():
        raise ValueError("expected finite f32 HxWx3 with spatial dimensions at least7")
    with torch.no_grad():
        output = model._blur(torch.as_tensor(np.array(image, copy=True), device="cuda"), SIGMA)
        result = output.cpu().numpy().copy()
    if result.dtype != np.float32 or result.shape != image.shape or not np.isfinite(result).all():
        raise FloatingPointError("invalid in-focus output")
    return result


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_sha(array):
    return hashlib.sha256(np.asarray(array, dtype="<f4").tobytes(order="C")).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if sha(HERE/"model.py") != MODEL_SHA:
        raise AssertionError("frozen model changed")
    screen = HERE/"screen-1"/"output"
    roots = {"visibility": HERE/"visibility-1"/"output", "shot": HERE/"shot-prior-1"/"output",
             "cauchy": HERE/"cauchy-1"/"output", "matrix": HERE/"matrix-cauchy-1"/"output"}
    sources = []
    for case in ("flat", "layered"):
        sources.append(dict(case=case, arm="truth", path=screen/case/"truth-rgb-f32.npy", filtered=True))
        for arm, root in roots.items():
            sources.append(dict(case=case, arm=arm, path=root/case/"fixed-alpha"/"reconstruction.npz",
                                filtered=True, receipt=root/case/"fixed-alpha"/"receipt.json"))
        sources.append(dict(case=case, arm="far-only", path=screen/case/"far-only"/"reconstruction.npz",
                            filtered=True, receipt=screen/case/"far-only"/"receipt.json"))
        sources += [dict(case=case, arm=label, path=screen/case/name, filtered=False)
                    for label, name in (("mean-observed", "mean-rgb-f32.npy"),
                                        ("donor-observed", "oracle-bound-rgb-f32.npy"))]
    files = {HERE/"model.py"} | {s["path"] for s in sources} | {s["receipt"] for s in sources if "receipt" in s}
    before = {str(p): sha(p) for p in sorted(files)}
    out.mkdir(parents=True, exist_ok=False)
    artifacts = []
    for entry in sources:
        path = entry["path"]
        if "receipt" in entry:
            receipt = json.loads(entry["receipt"].read_text(encoding="utf-8"))
            cfg = receipt["config"]
            if (cfg["width"], cfg["height"]) != (96, 96) or cfg["psf_sigma"] != SIGMA:
                raise AssertionError("saved latent does not use the fixed extent/PSF")
            with np.load(path, allow_pickle=False) as data:
                # This field was composed by FitResult before any common output PSF.
                image = data["pinhole_rgb"].copy()
        else:
            image = np.load(path, allow_pickle=False)
        if image.dtype != np.float32 or image.shape != (96, 96, 3) or not np.isfinite(image).all():
            raise ValueError("unexpected saved native image")
        input_array_hash = array_sha(image)
        folder = out/entry["case"]
        folder.mkdir(exist_ok=True)
        destination = folder/f'{entry["arm"]}-rgb-f32.npy'
        if entry["filtered"]:
            delivered = apply_in_focus(image)
            np.save(destination, delivered, allow_pickle=False)
        else:
            delivered = image
            shutil.copyfile(path, destination)
            if sha(destination) != before[str(path)]:
                raise AssertionError("observed comparator was changed")
        if array_sha(image) != input_array_hash:
            raise AssertionError("read-only filtering changed input array")
        artifacts.append(dict(case=entry["case"], arm=entry["arm"], source_path=str(path),
            source_sha256=before[str(path)], source_array_sha256=input_array_hash,
            path=str(destination), sha256=sha(destination), array_sha256=array_sha(delivered),
            shape=list(delivered.shape), dtype=str(delivered.dtype), psf_applications=int(entry["filtered"]),
            source_kind="latent-pinhole" if entry["filtered"] else "already-observed-developed",
            source_receipt_sha256=before.get(str(entry.get("receipt")))))
    # Record exactly the normalized f32 CUDA coefficients used by frozen _blur.
    x = torch.arange(-RADIUS, RADIUS+1, dtype=torch.float32, device="cuda")
    kernel = torch.exp(-.5*(x/SIGMA)**2)
    kernel = (kernel/kernel.sum()).cpu().numpy()
    after = {str(p): sha(p) for p in sorted(files)}
    if before != after:
        raise AssertionError("immutable source files changed")
    result = dict(status="IN_FOCUS_CONSUMER_COMPLETE", target="common-PSF of composed pinhole RGB",
        full_native_shape=[96, 96, 3], scoring_support_native_xywh=[16, 16, 64, 64],
        psf=dict(nominal_sigma=.7, supplied_f32_sigma=SIGMA, radius=RADIUS,
                 kernel_1d_f32=kernel.tolist(), kernel_sha256=array_sha(kernel),
                 implementation="frozen model._blur; separable x then y; zero padding; CUDAf32; TF32 disabled"),
        artifacts=artifacts, source_bindings_before=before, source_bindings_after=after,
        sources_unchanged=True, original_pinhole_admission_unchanged=True, real_photo_admission=False,
        observed_comparator_scope="No additional PSF or donor reselection; original donor choices targeted pinhole truth.")
    (out/"result.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print("IN_FOCUS_CONSUMER", json.dumps(dict(status=result["status"], artifacts=len(artifacts))), flush=True)


if __name__ == "__main__":
    main()
