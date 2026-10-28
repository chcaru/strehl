"""Saved complete original-CFA photograph presentation; no reconstruction/retone."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PHOTO = ROOT / "experiments/raw-quality-2026-10-26/photo-review/baseline-witnesses.json"
COMPARISON = HERE.parent / "weevil-fine-comparator/photo-review"
MAPPED = COMPARISON / "mapped-witnesses.json"
PREVIOUS = COMPARISON / "crop-export-receipt.json"
HELD_DEVELOPMENT = ROOT / "outputs/raw-quality-2026-10-27/direct-cfa-streamed-delivery-controls-2/output/held-development.json"
PINS = {
    PHOTO: "826c4ab6c620122449f6575cdd18c0f9ee9cb460f29f6d895e832325d6405888",
    MAPPED: "2b886b0006414b7219196deefb87ab8d805336df51d21df65127868bec7f59fa",
    PREVIOUS: "485e6fc2b76971ce8de81273261ae27d558526bb644d847d21451339d6b2134d",
}
WIDTH, HEIGHT = 6896, 4596
ICC_SHA = "238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ref(path):
    p = Path(path).resolve()
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(4 << 20), b""):
            h.update(block)
    st = p.stat()
    return dict(path=str(p), sha256=h.hexdigest(), bytes=st.st_size, mtime_ns=st.st_mtime_ns)


def bind(value):
    actual = ref(value["path"])
    require(actual["sha256"] == value["sha256"] and actual["bytes"] == value["bytes"],
            "saved artifact differs: " + value["path"])
    return Path(actual["path"])


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pixels_hash(array):
    view = memoryview(array).cast("B")
    h = hashlib.sha256()
    for start in range(0, len(view), 4 << 20):
        h.update(view[start:start + (4 << 20)])
    return h.hexdigest()


def link(label, path):
    p = str(Path(path).resolve())
    if p.startswith("\\\\?\\UNC\\"):
        p = "\\\\" + p[8:]
    elif p.startswith("\\\\?\\"):
        p = p[4:]
    return "[" + label + "](<" + Path(p).as_posix() + ">)"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    source_receipt = args.input_receipt.resolve()
    source = source_receipt.parent
    out = args.out.resolve()
    require(source.is_relative_to((ROOT / "outputs").resolve()), "workspace saved input required")
    require(out.is_relative_to((ROOT / "outputs").resolve()) and not out.exists()
            and not out.is_relative_to(source), "fresh separate workspace output required")
    out.mkdir(parents=True)
    try:
        complete_path = source.parent / "completion.json"
        process_path = source.parent / "process.json"
        complete, process, scientific = read(complete_path), read(process_path), read(source_receipt)
        require(complete["complete_photograph"] and complete["source_bindings_unchanged"]
                and complete["photographic_improvement_claimed"] is False, "root completion absent")
        require(process["exit_code"] == 0 and process.get("error") is None
                and not process.get("cleanup_errors") and process["direct_exit_observed"]
                and process["pipe_eof_observed"] and process["job_accounting"]["active_processes"] == 0,
                "full source job did not terminate cleanly")
        require(scientific["status"] == "COMPLETE_DIRECT_CFA_FULL_PHOTOGRAPH" and scientific["complete"]
                and scientific["source_count"] == 299 and scientific["all_sources_consumed"]
                and scientific["native_dimensions"] == [WIDTH, HEIGHT]
                and scientific["delivery_xywh"] == [68, 46, WIDTH, HEIGHT]
                and scientific["entire_output"] and scientific["quality_claim"] is False
                and scientific["photographic_admission"] is False and scientific["admission"] is False,
                "complete299 original-CFA photograph contract differs")
        require(scientific["final_status_not_overridden_for_render"]
                and scientific["old_generated_flat_failure_retained"]
                and scientific["cache_bytes_and_metadata_unchanged"]
                and scientific["source_bindings_unchanged"]
                and scientific["final_demosaic_calls"] == scientific["final_remosaic_calls"] == 0,
                "diagnostic/numerical status or native preservation differs")
        require(complete["numerical_convergence"] == scientific["numeric_converged"],
                "root/scientific numerical status differs")
        master = bind(scientific["rgb16"])
        native_path = bind(scientific["native_development"])
        delivery_path = bind(scientific["delivery"])
        camera_path = bind(scientific["camera_rgb"])
        require(master.samefile(source / "native/rgb16-master.tiff")
                and native_path.samefile(source / "native/receipt.json"),
                "candidate must be its own native full output")
        for p in (source_receipt, master, native_path, delivery_path, camera_path):
            matches = [v for v in complete["reports"] if Path(v["path"]).samefile(p)]
            require(len(matches) == 1, "artifact missing or duplicated in successful root inventory")
            bind(matches[0])
        native, delivery = read(native_path), read(delivery_path)
        require(native["status"] == "COMPLETE_DIRECT_RGB_NATIVE_DEVELOPMENT" and native["complete"]
                and native["pixel_readback_exact"] and native["native_dimensions"] == [WIDTH, HEIGHT]
                and native["demosaic_calls"] == native["remosaic_calls"] == 0
                and native["tone_measured_from_output"] is False
                and native["retained_input_bytes_and_metadata_unchanged"], "native master contract differs")
        require(bind(native["rgb16"]).samefile(master)
                and bind(native["signed_camera_rgb_master"]).samefile(camera_path),
                "native/camera bindings disagree")
        require(delivery["status"] == "COMPLETE_REFERENCE_CELL_CAMERA_RGB" and delivery["complete"]
                and delivery["shape"] == [HEIGHT, WIDTH, 3] and delivery["dtype"] == "<f4"
                and delivery["units"] == "black-subtracted-camera-DN"
                and delivery["delivery_xywh"] == [68, 46, WIDTH, HEIGHT]
                and delivery["demosaic_calls"] == delivery["remosaic_calls"] == 0
                and bind(delivery["camera_rgb"]).samefile(camera_path), "final RGB integration contract differs")
        require(native["development"] == read(HELD_DEVELOPMENT), "pinned native display changed")
        inputs = [Path(__file__), HERE / "full-photograph-view-protocol.md", PHOTO, MAPPED, PREVIOUS,
                  HELD_DEVELOPMENT, source_receipt, complete_path, process_path, master,
                  native_path, delivery_path, camera_path]
        for path, expected in PINS.items():
            require(ref(path)["sha256"] == expected, "frozen witness/reference manifest changed")
        frozen, mapped, prior = read(PHOTO), read(MAPPED), read(PREVIOUS)
        require(len(frozen["witnesses"]) == 10 and frozen["complete_rgb16_dimensions"] == [WIDTH, HEIGHT]
                and prior["status"] == "ALL30_NATIVE_CROPS_READY_NO_VERDICT" and prior["inputs_unchanged"],
                "fixed witness population/reference export differs")
        references = []
        for name in ("native-ca-off", "b4"):
            arm = mapped["arms"][name]
            prior_master, prior_jpeg = bind(arm["master"]), bind(arm["complete_jpeg"])
            require(not master.samefile(prior_master), "candidate substituted by reference master")
            inputs.extend((prior_master, prior_jpeg))
            witnesses = [v for v in prior["outputs"] if v["arm"] == name]
            require(len(witnesses) == 10, "reference witness population differs")
            for witness in witnesses:
                inputs.append(bind(witness["png"]))
                require(witness["pixels_exact"] and witness["icc_exact"], "reference crop not exact")
            references.append(dict(name=name, master=ref(prior_master), complete_jpeg=ref(prior_jpeg),
                native_dimensions=arm["dimensions"], mapping=arm["mapping"], witnesses=witnesses,
                processing="existing saved result; neither rerendered nor retuned"))
        before = [ref(p) for p in inputs]
        save(out / "input-bindings.json", before)
        import numpy as np
        import tifffile
        from PIL import Image
        with tifffile.TiffFile(master) as tf:
            require(len(tf.pages) == 1, "one complete master page required")
            page = tf.pages[0]
            require(page.shape == (HEIGHT, WIDTH, 3) and page.dtype == np.uint16,
                    "complete RGB16 master dimensions/type differ")
            icc = bytes(page.tags[34675].value)
            description = page.description
            pixels = np.ascontiguousarray(page.asarray(), dtype="<u2")
        require(hashlib.sha256(icc).hexdigest() == native["icc_sha256"] == ICC_SHA,
                "candidate/native/reference ICC differs")
        require(description == native["image_description"], "native description changed")
        pixel_sha = pixels_hash(pixels)
        require(pixel_sha == native["rgb16_pixels_sha256"], "full RGB16 pixel readback differs")
        rgb8 = np.empty(pixels.shape, dtype=np.uint8)
        for y in range(0, HEIGHT, 128):
            rgb8[y:y+128] = ((pixels[y:y+128].astype(np.uint32) + 128) // 257).astype(np.uint8)
        full = Image.fromarray(rgb8, "RGB")
        full_path = out / "complete-stack.jpg"
        full.save(full_path, quality=95, subsampling=0, icc_profile=icc, dpi=(300, 300))
        with Image.open(full_path) as check:
            require(check.size == (WIDTH, HEIGHT) and check.info.get("icc_profile") == icc,
                    "complete JPEG geometry/ICC differs")
        overview = full.copy()
        overview.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        overview_path = out / "overview.jpg"
        overview.save(overview_path, quality=94, subsampling=0, icc_profile=icc)
        rows = []
        for witness in frozen["witnesses"]:
            name = witness["name"]
            x, y, w, h = witness["rect_xywh"]
            require(w == h == 384 and 0 <= x <= WIDTH-w and 0 <= y <= HEIGHT-h, "frozen crop outside master")
            png = out / (name + ".png")
            expected = np.ascontiguousarray(rgb8[y:y+h, x:x+w])
            Image.fromarray(expected, "RGB").save(png, icc_profile=icc)
            with Image.open(png) as check:
                require(check.size == (384, 384) and check.info.get("icc_profile") == icc
                        and np.array_equal(np.asarray(check), expected), "native PNG crop readback differs")
            rows.append(dict(name=name, rect_xywh=[x, y, w, h], role=witness["role"],
                gauge="delivered reference149 native coordinates; original reference origin(68,46)",
                resized=False, png=ref(png), png_pixels_exact=True,
                rgb16_source_pixels_sha256=pixels_hash(np.ascontiguousarray(pixels[y:y+h, x:x+w])),
                references=[next(v for v in arm["witnesses"] if v["name"] == name) for arm in references]))
        after = [ref(p) for p in inputs]
        require(before == after, "saved inputs or scripts changed during presentation")
        result = dict(schema=1, status="COMPLETE_ORIGINAL_CFA_PHOTOGRAPH_VIEWS_READY_NO_VERDICT", complete=True,
            quality_claim=False, photographic_admission=False, RAW_reads=0, reconstruction_executed=False,
            source_receipt=ref(source_receipt), full_job_completion=ref(complete_path),
            source_count=299, native_dimensions=[WIDTH, HEIGHT], delivery_xywh=[68, 46, WIDTH, HEIGHT],
            solver_status=scientific["solver_status"], numeric_converged=scientific["numeric_converged"],
            iterations=scientific["iterations"], old_generated_flat_failure_retained=True,
            full_master=ref(master), signed_camera_master=ref(camera_path),
            complete_jpeg=ref(full_path), overview=ref(overview_path),
            rgb16_pixel_readback_exact=True, rgb16_pixels_sha256=pixel_sha, icc_sha256=ICC_SHA,
            display="existing native RGB16 -> uint8(value+128)//257; no retone/exposure/color transform; full JPEG is lossy",
            overview_usage="resized orientation only; all ten PNGs retain exact native384 pixels",
            witnesses=rows, references=references, mapped_reference_manifest=ref(MAPPED),
            comparison_limit=mapped["comparison_limit"], locator_limit=mapped["locator_limit"],
            input_bindings_unchanged=True, command=sys.argv, seconds=time.perf_counter()-started)
        save(out / "receipt.json", result)
        lines = ["# Complete original-CFA photograph — independent review pending", "",
            "Inspect the complete candidate and both reference compositions before the fixed native witnesses. Numerical status is retained; no quality claim.", "",
            link("Complete candidate JPEG", full_path) + " · " + link("Full-resolution RGB16 master", master)
            + " · " + link("Signed camera-DN master", camera_path), "",
            "Solver: `" + scientific["solver_status"] + "`; numerical convergence: `"
            + str(scientific["numeric_converged"]).lower() + "`. Prior flat/noise failure remains.", ""]
        for arm in references:
            lines.append(link(arm["name"] + " complete JPEG", arm["complete_jpeg"]["path"])
                         + " · " + link("full-resolution master", arm["master"]["path"]))
        lines.extend(["", mapped["comparison_limit"] + " " + mapped["locator_limit"], "",
                      "| Fixed witness | Candidate | Native CA-off | Helicon B4 |", "| --- | --- | --- | --- |"])
        for row in rows:
            lines.append("| " + row["name"] + " | " + link("native384", row["png"]["path"]) + " | "
                         + " | ".join(link("native384", r["png"]["path"]) for r in row["references"]) + " |")
        (out / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    except BaseException as error:
        save(out / "failure.json", dict(status="INCOMPLETE_PHOTOGRAPH_VIEWS", complete=False,
            quality_claim=False, error=str(error), traceback=traceback.format_exc()))
        raise


if __name__ == "__main__":
    main()
