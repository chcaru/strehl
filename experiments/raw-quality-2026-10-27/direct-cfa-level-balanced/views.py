"""Publish fixed complete intermediate photographs; no reconstruction or retone."""
from pathlib import Path
import hashlib
import importlib.util
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HELPER = HERE.parent / "direct-cfa-streamed-normal/full-photograph-views.py"
HELPER_SHA = "0945f6b10d44dfeff32cb05b64dea83fade925f50e0129f09a5c4d9ab060f8a0"
REJECTED = ROOT / "outputs/raw-quality-2026-10-27/direct-cfa-streamed-full-views-2/output/receipt.json"
REJECTED_SHA = "8c8f3bb2e278317c05e1f65e22dae76e861e377ebe5d111b2ac651e03287056b"
HELD_SHA = "26a441851ee4344c78d86ef1f8eeb39002acea01ba93b34319c60992e2a9c7c0"


def _helpers():
    if hashlib.sha256(HELPER.read_bytes()).hexdigest() != HELPER_SHA:
        raise ValueError("commissioned presentation helper changed")
    spec = importlib.util.spec_from_file_location("level_balanced_saved_view_helpers", HELPER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def source_dependencies():
    """Files the root wrapper should bind; reads no pixels or model code."""
    h = _helpers()
    return [Path(__file__), HELPER, h.PHOTO, h.MAPPED, h.PREVIOUS,
            h.HELD_DEVELOPMENT, REJECTED]


def publish_checkpoint(*, checkpoint_dir: Path, iteration: int, native_receipt: Path,
                       held_development_receipt: Path) -> dict:
    """Write views immediately after fixed native delivery at iterations 1, 2, 4.

    A checkpoint is not a completed job or a numerical acceptance. The caller
    owns source-consumption and solver receipts; this helper validates saved
    delivery/development and exact presentation only. Exceptions retain partial
    outputs and propagate to the root-owned job without replacing a photograph.
    """
    h = _helpers()
    started = time.perf_counter()
    checkpoint = Path(checkpoint_dir).resolve()
    native_path = Path(native_receipt).resolve()
    held_path = Path(held_development_receipt).resolve()
    h.require(type(iteration) is int and iteration in (1, 2, 4), "fixed checkpoint schedule differs")
    h.require(checkpoint.is_relative_to((ROOT / "outputs").resolve())
              and checkpoint.name == f"iteration-{iteration:02d}", "workspace checkpoint layout differs")
    h.require(native_path.samefile(checkpoint / "native/receipt.json"), "native receipt is not this checkpoint")
    h.require(held_path.samefile(h.HELD_DEVELOPMENT) and h.ref(held_path)["sha256"] == HELD_SHA,
              "held development changed")
    out = checkpoint / "views"
    h.require(not out.exists(), "fresh checkpoint views required")
    out.mkdir()
    try:
        native = h.read(native_path)
        h.require(native["status"] == "COMPLETE_DIRECT_RGB_NATIVE_DEVELOPMENT" and native["complete"]
                  and native["entire_output"] and native["pixel_readback_exact"]
                  and native["native_dimensions"] == [h.WIDTH, h.HEIGHT]
                  and native["demosaic_calls"] == native["remosaic_calls"] == 0
                  and native["tone_measured_from_output"] is False
                  and native["quality_claim"] is False and native["photographic_admission"] is False
                  and native["retained_input_bytes_and_metadata_unchanged"], "native delivery contract differs")
        h.require(native["development"] == h.read(held_path), "fixed development differs")
        master = h.bind(native["rgb16"])
        camera = h.bind(native["signed_camera_rgb_master"])
        delivery_path = h.bind(native["delivery_receipt"])
        h.require(master.samefile(checkpoint / "native/rgb16-master.tiff")
                  and camera.samefile(checkpoint / "delivery/camera-rgb-dn.f32le")
                  and delivery_path.samefile(checkpoint / "delivery/receipt.json"),
                  "candidate is not its own checkpoint output")
        delivery = h.read(delivery_path)
        h.require(delivery["status"] == "COMPLETE_REFERENCE_CELL_CAMERA_RGB" and delivery["complete"]
                  and delivery["shape"] == [h.HEIGHT, h.WIDTH, 3] and delivery["dtype"] == "<f4"
                  and delivery["units"] == "black-subtracted-camera-DN"
                  and delivery["delivery_xywh"] == [68, 46, h.WIDTH, h.HEIGHT]
                  and delivery["demosaic_calls"] == delivery["remosaic_calls"] == 0
                  and h.bind(delivery["camera_rgb"]).samefile(camera), "reference-cell delivery differs")
        for path, expected in h.PINS.items():
            h.require(h.ref(path)["sha256"] == expected, "frozen witness/reference manifest changed")
        h.require(h.ref(REJECTED)["sha256"] == REJECTED_SHA, "rejected reference receipt changed")
        frozen, mapped, prior, rejected = h.read(h.PHOTO), h.read(h.MAPPED), h.read(h.PREVIOUS), h.read(REJECTED)
        h.require(len(frozen["witnesses"]) == 10 and frozen["complete_rgb16_dimensions"] == [h.WIDTH, h.HEIGHT]
                  and prior["status"] == "ALL30_NATIVE_CROPS_READY_NO_VERDICT" and prior["inputs_unchanged"],
                  "fixed witness/reference population differs")
        inputs = source_dependencies() + [native_path, held_path, master, camera, delivery_path]
        references = []
        for name in ("native-ca-off", "b4", "b8"):
            arm = mapped["arms"][name]
            old_master, old_jpeg = h.bind(arm["master"]), h.bind(arm["complete_jpeg"])
            h.require(not master.samefile(old_master), "candidate substituted by reference")
            inputs.extend((old_master, old_jpeg))
            witnesses = [v for v in prior["outputs"] if v["arm"] == name]
            h.require(len(witnesses) == 10, "reference witness population differs")
            for witness in witnesses:
                inputs.append(h.bind(witness["png"]))
                h.require(witness["pixels_exact"] and witness["icc_exact"], "reference crop not exact")
            references.append(dict(name=name, master=h.ref(old_master), complete_jpeg=h.ref(old_jpeg),
                                   native_dimensions=arm["dimensions"], mapping=arm["mapping"], witnesses=witnesses))
        h.require(rejected["status"] == "COMPLETE_ORIGINAL_CFA_PHOTOGRAPH_VIEWS_READY_NO_VERDICT"
                  and rejected["complete"] and len(rejected["witnesses"]) == 10,
                  "rejected complete reference differs")
        old_master, old_jpeg = h.bind(rejected["full_master"]), h.bind(rejected["complete_jpeg"])
        h.require(not master.samefile(old_master), "candidate substituted by rejected reference")
        inputs.extend((old_master, old_jpeg))
        rejected_witnesses = []
        for expected, witness in zip(frozen["witnesses"], rejected["witnesses"]):
            h.require(witness["name"] == expected["name"] and witness["rect_xywh"] == expected["rect_xywh"]
                      and witness["png_pixels_exact"] and not witness["resized"], "rejected witness differs")
            inputs.append(h.bind(witness["png"]))
            rejected_witnesses.append(dict(name=witness["name"], xywh=witness["rect_xywh"], png=witness["png"]))
        references.append(dict(name="rejected-original-cfa-64", master=h.ref(old_master), complete_jpeg=h.ref(old_jpeg),
                               native_dimensions=[h.WIDTH, h.HEIGHT], mapping="same reference149/crop(68,46)",
                               witnesses=rejected_witnesses, photographic_verdict="rejected blockwise image"))
        inputs = list(dict.fromkeys(inputs))
        before = [h.ref(p) for p in inputs]
        h.save(out / "input-bindings.json", before)

        import numpy as np
        import tifffile
        from PIL import Image
        with tifffile.TiffFile(master) as tf:
            h.require(len(tf.pages) == 1, "one complete master page required")
            page = tf.pages[0]
            h.require(page.shape == (h.HEIGHT, h.WIDTH, 3) and page.dtype == np.uint16, "RGB16 master shape/type differs")
            icc = bytes(page.tags[34675].value)
            h.require(page.description == native["image_description"], "native description changed")
            pixels = np.ascontiguousarray(page.asarray(), dtype="<u2")
        h.require(hashlib.sha256(icc).hexdigest() == native["icc_sha256"] == h.ICC_SHA, "ICC differs")
        pixel_sha = h.pixels_hash(pixels)
        h.require(pixel_sha == native["rgb16_pixels_sha256"], "complete master pixel readback differs")
        rgb8 = np.empty(pixels.shape, dtype=np.uint8)
        for y in range(0, h.HEIGHT, 128):
            rgb8[y:y+128] = ((pixels[y:y+128].astype(np.uint32) + 128) // 257).astype(np.uint8)
        full = Image.fromarray(rgb8, "RGB")
        full_path = out / "complete-stack.jpg"
        full.save(full_path, quality=95, subsampling=0, icc_profile=icc, dpi=(300, 300))
        with Image.open(full_path) as check:
            h.require(check.size == (h.WIDTH, h.HEIGHT) and check.info.get("icc_profile") == icc, "full JPEG geometry/ICC differs")
        overview = full.copy()
        overview.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        overview_path = out / "overview.jpg"
        overview.save(overview_path, quality=94, subsampling=0, icc_profile=icc)
        rows = []
        for witness in frozen["witnesses"]:
            name = witness["name"]
            x, y, w, height = witness["rect_xywh"]
            h.require(w == height == 384 and 0 <= x <= h.WIDTH-w and 0 <= y <= h.HEIGHT-height, "frozen crop outside master")
            png = out / (name + ".png")
            expected = np.ascontiguousarray(rgb8[y:y+height, x:x+w])
            Image.fromarray(expected, "RGB").save(png, icc_profile=icc)
            with Image.open(png) as check:
                h.require(check.size == (384, 384) and check.info.get("icc_profile") == icc
                          and np.array_equal(np.asarray(check), expected), "native PNG readback differs")
            rows.append(dict(name=name, rect_xywh=[x, y, w, height], resized=False, png=h.ref(png),
                             png_pixels_exact=True, role=witness["role"],
                             rgb16_source_pixels_sha256=h.pixels_hash(np.ascontiguousarray(pixels[y:y+height, x:x+w])),
                             references=[next(v for v in arm["witnesses"] if v["name"] == name) for arm in references]))
        after = [h.ref(p) for p in inputs]
        h.require(before == after, "saved source or references changed during presentation")
        result = dict(schema=1, status="COMPLETE_LEVEL_BALANCED_CHECKPOINT_VIEWS", complete=True,
                      iteration=iteration, intermediate_checkpoint=True, full_job_completion_asserted=False,
                      numerical_acceptance_assessed=False, quality_claim=False, photographic_admission=False,
                      RAW_reads=0, reconstruction_executed=False, source_count_verified_by_exporter=False,
                      native_dimensions=[h.WIDTH, h.HEIGHT], delivery_xywh=[68, 46, h.WIDTH, h.HEIGHT],
                      native_receipt=h.ref(native_path), delivery_receipt=h.ref(delivery_path), held_development=h.ref(held_path),
                      full_master=h.ref(master), signed_camera_master=h.ref(camera), complete_jpeg=h.ref(full_path),
                      overview=h.ref(overview_path), rgb16_pixel_readback_exact=True, rgb16_pixels_sha256=pixel_sha,
                      icc_sha256=h.ICC_SHA, display="RGB16 -> (value+128)//257; no retone; JPEG lossy",
                      overview_usage="orientation only; all witness PNGs exact native384", witnesses=rows,
                      references=references, mapped_reference_manifest=h.ref(h.MAPPED),
                      comparison_limit=mapped["comparison_limit"], locator_limit=mapped["locator_limit"],
                      input_bindings_unchanged=True, seconds=time.perf_counter()-started)
        lines = [f"# Complete level-balanced checkpoint {iteration}: review pending", "",
                 "Intermediate finite image; no true numerical-convergence or complete-job assertion. Prior failures remain.", "",
                 h.link("Complete candidate JPEG", full_path) + " · " + h.link("Full-resolution RGB16 master", master)
                 + " · " + h.link("Signed camera-DN master", camera), ""]
        for arm in references:
            lines.append(h.link(arm["name"] + " complete JPEG", arm["complete_jpeg"]["path"])
                         + " · " + h.link("full-resolution master", arm["master"]["path"]))
        lines.extend(["", mapped["comparison_limit"] + " " + mapped["locator_limit"], "",
                      "View every complete image before all ten fixed witnesses. No quality verdict is supplied.", "",
                      "| Witness | Candidate | Native CA-off | Helicon B4 | Helicon B8 | Rejected inverse64 |",
                      "| --- | --- | --- | --- | --- | --- |"])
        for row in rows:
            lines.append("| " + row["name"] + " | " + h.link("native384", row["png"]["path"]) + " | "
                         + " | ".join(h.link("native384", ref["png"]["path"]) for ref in row["references"]) + " |")
        index = out / "index.md"
        with index.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(lines) + "\n")
        result["index"] = h.ref(index)
        h.save(out / "receipt.json", result)
        return result
    except BaseException as error:
        h.save(out / "failure.json", dict(status="INCOMPLETE_CHECKPOINT_VIEWS", complete=False,
                                         iteration=iteration, quality_claim=False, error=str(error),
                                         traceback=traceback.format_exc()))
        raise
