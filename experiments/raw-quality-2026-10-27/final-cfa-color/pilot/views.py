"""Publish three saved-CFA MHC/completion pairs; no reconstruction or retone.

The conversion/readback pattern is reused from the commissioned
direct-cfa-streamed-normal/full-photograph-views.py. Root owns process-terminal
qualification before invoking this saved-file helper.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PHOTO = ROOT / "experiments/raw-quality-2026-10-26/photo-review/baseline-witnesses.json"
COMPARISON = ROOT / "experiments/raw-quality-2026-10-27/weevil-fine-comparator/photo-review"
MAPPED = COMPARISON / "mapped-witnesses.json"
PREVIOUS = COMPARISON / "crop-export-receipt.json"
PINS = {
    PHOTO: "826c4ab6c620122449f6575cdd18c0f9ee9cb460f29f6d895e832325d6405888",
    MAPPED: "2b886b0006414b7219196deefb87ab8d805336df51d21df65127868bec7f59fa",
    PREVIOUS: "485e6fc2b76971ce8de81273261ae27d558526bb644d847d21451339d6b2134d",
}
WIDTH, HEIGHT = 6896, 4596
NAMES = ("held-mhc", "held-color", "candidate-mhc", "candidate-color", "uniform-mhc", "uniform-color")
ICC_SHA = "238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b"
BASE_PIXELS_SHA = "f98cb4d9bc281eb9f28f4e618878607d7e7317eeb7ac20b349f35dfee81c280c"
BASE_LINEAR_SHA = "ee2b711bc36e48b9913531e1c615bd265ad06fd395a74f6224ca94392e32be09"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ref(path):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 << 20), b""):
            h.update(block)
    st = path.stat()
    return dict(path=str(path), sha256=h.hexdigest(), bytes=st.st_size, mtime_ns=st.st_mtime_ns)


def read(path):
    path = Path(path)
    require(path.stat().st_size <= 4 << 20, "JSON receipt exceeds4MiB")
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    data = json.dumps(value, indent=2, allow_nan=False) + "\n"
    require(len(data.encode("utf-8")) <= 4 << 20, "JSON output exceeds4MiB; no truncation")
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        f.write(data)


def pixels_hash(array):
    view = memoryview(array).cast("B")
    h = hashlib.sha256()
    for start in range(0, len(view), 4 << 20):
        h.update(view[start:start + (4 << 20)])
    return h.hexdigest()


def link(label, path):
    value = str(Path(path).resolve())
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return "[" + label + "](<" + Path(value).as_posix() + ">)"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--held-receipt", type=Path, required=True, help="full-shape cost saved-field receipt on the exact held baseline CFA")
    parser.add_argument("--candidate-receipt", type=Path, required=True, help="saved-field driver receipt")
    parser.add_argument("--uniform-receipt", type=Path, required=True, help="saved-field driver receipt")
    parser.add_argument("--null-receipt", type=Path, required=True, help="normalized-camera writer held MHC null")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    out = args.out.resolve()
    workspace_outputs = (ROOT / "outputs").resolve()
    require(out.is_relative_to(workspace_outputs) and not out.exists() and out.parent.is_dir(),
            "fresh separate workspace output required")
    out.mkdir()
    try:
        import numpy as np
        import tifffile
        from PIL import Image
        import PIL
        helper_path = HERE / "saved-field.py"
        spec = importlib.util.spec_from_file_location("saved_field_view_validation", helper_path)
        helper = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = helper
        spec.loader.exec_module(helper)
        bindings = {}
        def remember(path):
            item = ref(path)
            bindings.setdefault(item["path"], item)
            require(bindings[item["path"]] == item, "input changed during preflight")
            return Path(item["path"])
        def bind(value):
            path = remember(value["path"])
            actual = bindings[str(path)]
            require(actual["sha256"] == value["sha256"] and actual["bytes"] == value["bytes"],
                    "bound artifact differs: " + str(path))
            return path
        remember(__file__)
        remember(helper_path)
        null_path = remember(args.null_receipt)
        null = helper.verify_null(null_path, None)
        null_source = read(bind(null["source_receipt"]))
        bind(null["input_camera_rgb"])
        for value in null["parity"]["references"].values():
            bind(value)
        for key in ("cfa", "input_cfa", "camera_rgb", "rgb16", "linear_rgb32", "configuration", "executable", "development_receipt"):
            bind(null_source[key])
        all_native = [dict(name="null", receipt=bindings[str(null_path)], data=null)]
        drivers = []
        for label, path in (("held", args.held_receipt), ("candidate", args.candidate_receipt), ("uniform", args.uniform_receipt)):
            path = remember(path)
            require(path.is_relative_to(workspace_outputs) and not out.is_relative_to(path.parent),
                    "retained driver receipt must be separate from new views")
            driver = read(path)
            require(driver["schema"] == 1 and driver["status"] == "COMPLETE_SAVED_FINAL_CFA_COLOR"
                    and driver["complete"] is True and driver["inputs_unchanged"] is True
                    and driver["entire_output"] is True and driver["development_unchanged"] is True
                    and driver["pre_restore_null_pass"] is True
                    and driver["native_dimensions"] == [WIDTH, HEIGHT] and driver["active_origin_xy"] == [68, 46]
                    and driver["final_completion_stages"] == 1 and driver["writer_completion_stages"] == driver["RAW_reads"] == 0
                    and driver["quality_claim"] is False and driver["photographic_admission"] is False,
                    "complete unchanged saved-field comparison required")
            require(bind(driver["null_reference"]).samefile(null_path), "different commissioned null")
            require(read(bind(driver["pre_restore_null"]))["mechanical_pass"] is True,
                    "full-field pre-restoration mechanics did not pass")
            for key in ("input_bindings", "cfa", "normalized_cfa", "camera_rgb"):
                bind(driver[key])
            mhc_path = bind(driver["mhc_reference"])
            native_path = bind(driver["native"])
            require(native_path.samefile(path.parent / "native/receipt.json"), "driver does not bind own native output")
            mhc = helper.verify_mhc(mhc_path)
            bind(mhc["input_cfa"])
            if label == "held":
                require(mhc_path.samefile(bind(null["source_receipt"]))
                        and mhc["cfa"]["sha256"] == helper.HELD_CFA
                        and mhc["camera_rgb"]["sha256"] == helper.HELD_CAMERA
                        and mhc["pixel_hashes"]["rgb16"] == BASE_PIXELS_SHA
                        and mhc["pixel_hashes"]["linear_rgb32"] == BASE_LINEAR_SHA,
                        "held cost arm must consume the exact held baseline CFA and actual MHC field")
            native = helper.verify_native(read(native_path), WIDTH, HEIGHT, (68, 46))
            completion_path = bind(driver["completion"])
            require(completion_path.samefile(path.parent / "completion.json"), "completion receipt is not own output")
            completion = read(completion_path)
            evidence = completion["evidence"]
            require(completion["status"] == "COMPLETE_FINAL_CFA_COLOR_OPERATOR_FIELD" and completion["complete"] is True
                    and completion["signed_input_unchanged"] is True and completion["final_completion_stages"] == 1
                    and completion["source_demosaic_calls"] == completion["remosaic_calls"] == completion["RAW_reads"] == 0
                    and completion["quality_claim"] is False and completion["photographic_admission"] is False,
                    "completion field/path flags differ")
            require(evidence["status"] == "COMPLETE_FINAL_CFA_SPECTRAL_COMPLETION" and evidence["complete"] is True
                    and evidence["height"] == HEIGHT and evidence["width"] == WIDTH
                    and evidence["physical_origin_xy"] == [68, 46] and evidence["diagnostic_foil"] is None
                    and evidence["final_color_completion_calls"] == 1
                    and evidence["MHC_calls"] == evidence["source_demosaic_calls"] == evidence["remosaic_calls"] == evidence["RAW_reads"] == 0
                    and evidence["known_sites_restored_bit_exact"] is True
                    and evidence["camera_layout"] == "HWC" and evidence["camera_units"] == "normalized-camera-RGB",
                    "actual final completion scope differs")
            require(bind(completion["source_mhc_receipt"]).samefile(mhc_path)
                    and bind(native["source_receipt"]).samefile(completion_path), "upstream native chain differs")
            for key in ("cfa", "normalized_cfa", "camera_rgb", "development_receipt", "operator_source"):
                bind(completion[key])
            require(driver["cfa"]["sha256"] == completion["cfa"]["sha256"] == mhc["cfa"]["sha256"]
                    and driver["normalized_cfa"]["sha256"] == completion["normalized_cfa"]["sha256"]
                    and driver["camera_rgb"]["sha256"] == completion["camera_rgb"]["sha256"] == native["input_camera_rgb"]["sha256"]
                    and driver["camera_rgb"]["bytes"] == WIDTH * HEIGHT * 12
                    and driver["normalized_cfa"]["bytes"] == driver["cfa"]["bytes"] == WIDTH * HEIGHT * 4,
                    "paired CFA/camera field identity differs")
            require(native["executable"]["sha256"] == null["executable"]["sha256"], "color writer differs from exact null")
            for suffix, record, rp, description in (
                ("mhc", mhc, mhc_path, "one actual ordinary core MHC final completion"),
                ("color", native, native_path, "one independent-color spectral final completion; zero writer completion")):
                require(record["native_dimensions"] == [WIDTH, HEIGHT] and record["active_origin_xy"] == [68, 46],
                        "paired field gauge differs")
                require(record["development"] == null["development"]
                        and record["development_receipt"]["sha256"] == null["development_receipt"]["sha256"]
                        and record["material_metadata"] == null["material_metadata"]
                        and record["linear_material_metadata"] == null["linear_material_metadata"],
                        "same held paired development/materials required")
                record = dict(record, cfa=driver["cfa"], completion_description=description)
                all_native.append(dict(name=label + "-" + suffix, receipt=bindings[str(rp)], data=record))
            drivers.append(dict(name=label, receipt=bindings[str(path)], data=driver))
        require([v["name"] for v in all_native[1:]] == list(NAMES), "six-arm population differs")
        for item in all_native:
            arm = item["data"]
            for key in ("configuration", "executable", "development_receipt", "camera_rgb", "rgb16", "linear_rgb32"):
                bind(arm[key])
            for source_binding in arm["development"]["source_bindings"]:
                bind(source_binding)
            own = Path(item["receipt"]["path"]).parent
            for key, filename in (("rgb16", "rgb16-master.tiff"), ("linear_rgb32", "linear-master.tiff"),
                                  ("camera_rgb", "camera-rgb-normalized.f32le")):
                require(bind(arm[key]).samefile(own / filename), "native receipt does not bind own output")
        for path, expected in PINS.items():
            remember(path)
            require(bindings[str(path.resolve())]["sha256"] == expected, "frozen witness/reference manifest changed")
        frozen, mapped, previous = read(PHOTO), read(MAPPED), read(PREVIOUS)
        witnesses = frozen["witnesses"]
        require(len(witnesses) == 10 and len({v["name"] for v in witnesses}) == 10
                and frozen["complete_rgb16_dimensions"] == [WIDTH, HEIGHT]
                and frozen["source_crop_quad_xywh"] == [34, 23, 3448, 2298]
                and frozen["icc_sha256"] == ICC_SHA, "fixed witness population/gauge differs")
        require(previous["status"] == "ALL30_NATIVE_CROPS_READY_NO_VERDICT" and previous["inputs_unchanged"] is True,
                "retained comparison population differs")
        references = []
        for name in ("native-ca-off", "b4", "b8"):
            old = mapped["arms"][name]
            master, jpeg = bind(old["master"]), bind(old["complete_jpeg"])
            crops = [v for v in previous["outputs"] if v["arm"] == name]
            require(len(crops) == 10 and {v["name"] for v in crops} == {v["name"] for v in witnesses}, "old witness population differs")
            for crop in crops:
                bind(crop["png"])
                require(crop["pixels_exact"] is True and crop["icc_exact"] is True, "retained native crop not exact")
            references.append(dict(name=name, master=bindings[str(master)], complete_jpeg=bindings[str(jpeg)],
                                   native_dimensions=old["dimensions"], mapping=old["mapping"], witnesses=crops))
        sources = []
        for item in all_native[1:]:
            arm = dict(item["data"], name=item["name"])
            master, linear, cfa = bind(arm["rgb16"]), bind(arm["linear_rgb32"]), bind(arm["cfa"])
            with tifffile.TiffFile(linear) as tf:
                require(len(tf.pages) == 1 and tf.pages[0].shape == (HEIGHT, WIDTH, 3)
                        and tf.pages[0].dtype == np.float32, "complete float master header differs")
            sources.append((arm, master, linear, cfa))
        require(len({str(v[1]) for v in sources}) == 6, "arm masters substituted")
        save(out / "input-bindings.json", list(bindings.values()))

        outputs = []
        for arm, master, linear, cfa in sources:
            name = arm["name"]
            arm_out = out / name
            arm_out.mkdir()
            with tifffile.TiffFile(master) as tf:
                require(len(tf.pages) == 1, "single complete RGB16 page required")
                page = tf.pages[0]
                require(page.shape == (HEIGHT, WIDTH, 3) and page.dtype == np.uint16, "RGB16 header differs")
                icc = bytes(page.tags[34675].value)
                description = page.description
                pixels = np.ascontiguousarray(page.asarray(), dtype="<u2")
            require(hashlib.sha256(icc).hexdigest() == arm["material_metadata"]["icc_sha256"] == ICC_SHA
                    and description == arm["material_metadata"]["description"], "RGB16 material metadata differs")
            pixel_sha = pixels_hash(pixels)
            require(pixel_sha == arm["pixel_hashes"]["rgb16"], "full RGB16 pixel hash differs")
            rgb8 = np.empty(pixels.shape, dtype=np.uint8)
            for y in range(0, HEIGHT, 128):
                rgb8[y:y + 128] = ((pixels[y:y + 128].astype(np.uint32) + 128) // 257).astype(np.uint8)
            image = Image.fromarray(rgb8, "RGB")
            full_path = arm_out / "complete-stack.jpg"
            image.save(full_path, quality=98, subsampling=0, icc_profile=icc)
            with Image.open(full_path) as check:
                require(check.size == (WIDTH, HEIGHT) and check.mode == "RGB" and check.info.get("icc_profile") == icc,
                        "complete JPEG geometry/ICC differs")
                check.load()
            overview = image.copy()
            overview.thumbnail((1617, 1617), Image.Resampling.LANCZOS)
            overview_path = arm_out / "overview.jpg"
            overview.save(overview_path, quality=98, subsampling=0, icc_profile=icc)
            with Image.open(overview_path) as check:
                require(check.size == overview.size and check.info.get("icc_profile") == icc, "overview readback differs")
                check.load()
            rows = []
            for witness in witnesses:
                x, y, w, h = witness["rect_xywh"]
                require(w == h == 384 and 0 <= x <= WIDTH - w and 0 <= y <= HEIGHT - h, "fixed384 crop outside image")
                patch16 = np.ascontiguousarray(pixels[y:y + h, x:x + w])
                expected = ((patch16.astype(np.uint32) + 128) // 257).astype(np.uint8)
                png = arm_out / (witness["name"] + ".png")
                Image.fromarray(rgb8[y:y + h, x:x + w], "RGB").save(png, icc_profile=icc)
                with Image.open(png) as check:
                    require(check.size == (384, 384) and check.mode == "RGB" and check.info.get("icc_profile") == icc
                            and np.array_equal(np.asarray(check), expected), "native PNG pixel/ICC readback differs")
                rows.append(dict(name=witness["name"], rect_xywh=[x, y, w, h], png=ref(png), resized=False,
                                 png_pixels_exact=True, icc_exact=True, role=witness["role"],
                                 source_rgb16_pixels_sha256=pixels_hash(patch16), png_pixels_sha256=pixels_hash(expected)))
            output = dict(name=name, rgb16=bindings[str(master)], linear_rgb32=bindings[str(linear)], cfa=bindings[str(cfa)],
                          camera_rgb=arm["camera_rgb"], camera_rgb_semantics=arm["camera_rgb_semantics"],
                          completion_description=arm["completion_description"],
                          material_metadata=arm["material_metadata"], linear_material_metadata=arm["linear_material_metadata"],
                          rgb16_pixels_sha256=pixel_sha, complete_jpeg=ref(full_path), overview=ref(overview_path),
                          native_dimensions=[WIDTH, HEIGHT], witnesses=rows, all_png_pixels_and_icc_exact=True,
                          entire_output=True, display="(RGB16+128)//257; same ICC; no retone; JPEG98/subsampling0; native PNGs unresized")
            save(arm_out / "views.json", output)
            outputs.append(output)
            del pixels, rgb8, image, overview

        lines = ["# Saved final-CFA completion comparison", "",
                 "No photographic verdict. Inspect all six complete images before the ten fixed native witnesses. Each MHC/color pair consumes the exact same saved final CFA. The held pair isolates final color completion on the current native baseline; candidate/uniform pairs also carry their distinct upstream fusion. Source-population and process qualification belong to the root producing job; this helper validates saved final-development outputs only.", "",
                 "All displays use unchanged held development/ICC. Overviews resize for orientation only; JPEG is lossy, RGB16 masters and exact PNG crops are the pixel references.", "",
                 "| Arm | Complete photograph | RGB16 full master | Float full master | Camera RGB | Signed CFA | Orientation |",
                 "| --- | --- | --- | --- | --- | --- | --- |"]
        for arm in outputs:
            lines.append("| " + arm["name"] + " | " + " | ".join((link("complete JPEG", arm["complete_jpeg"]["path"]),
                         link("RGB16", arm["rgb16"]["path"]), link("RGB32", arm["linear_rgb32"]["path"]),
                         link("actual camera RGB", arm["camera_rgb"]["path"]), link("signed CFA", arm["cfa"]["path"]),
                         link("overview", arm["overview"]["path"]))) + " |")
        lines.extend(["", "Retained full-workflow references: native CA-off shares the fixed crop. Helicon B4/B8 have their own alignment/scale and RGB development before fusion; mapped crops are correspondence aids, not placement truth.", ""])
        for old in references:
            lines.append("- " + old["name"] + ": " + link("whole photograph", old["complete_jpeg"]["path"])
                         + "; " + link("full master", old["master"]["path"]))
        lines.extend(["", "| Fixed native384 witness | held MHC | held spectral color | candidate MHC | candidate spectral color | uniform MHC | uniform spectral color | held native | Helicon B4 | Helicon B8 |",
                      "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"])
        for witness in witnesses:
            row = [witness["name"] + " " + str(witness["rect_xywh"])]
            for arm in outputs:
                crop = next(v for v in arm["witnesses"] if v["name"] == witness["name"])
                row.append(link(arm["name"], crop["png"]["path"]))
            for old in references:
                crop = next(v for v in old["witnesses"] if v["name"] == witness["name"])
                row.append(link(old["name"], crop["png"]["path"]))
            lines.append("| " + " | ".join(row) + " |")
        lines.extend(["", "Physical gauge: reference149,3516x2344 guide, native crop(68,46,6896,4596). Each MHC arm uses one actual final core MHC stage. Its paired color arm uses one independent-color spectral completion and no writer completion. Both consume the same actual known-site WB/range normalization and held matrix/highlight/tone. Signed CFA and genuine normalized camera fields are retained; no inverse-developed camera field is used.", "",
                      "Held MHC normalized-camera writer exact replay: " + link("null native receipt", all_native[0]["receipt"]["path"]), ""])
        index = out / "index.md"
        with index.open("x", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines))
        for old in bindings.values():
            require(ref(old["path"]) == old, "saved input bytes/metadata changed during presentation")
        report = dict(schema=1, status="COMPLETE_FINAL_CFA_COLOR_VIEWS_READY_NO_VERDICT", complete=True,
                      native_receipts=[dict(name=v["name"], receipt=v["receipt"]) for v in all_native],
                      saved_field_receipts=[dict(name=v["name"],receipt=v["receipt"]) for v in drivers],
                      arms=outputs, references=references, witness_manifest=bindings[str(PHOTO.resolve())],
                      inputs_unchanged=True, all_png_pixels_and_icc_exact=True, native_dimensions=[WIDTH, HEIGHT],
                      arm_count=6, exact_native_witness_count=60, held_baseline_color_intervention=True,
                      native_crop_origin=[68, 46], reference=149, held_normalized_camera_replay_exact=True,
                      icc_sha256=ICC_SHA, index=ref(index), process_terminal_audit="root wrapper responsibility; not inferred here",
                      source_population_audit="root producing job responsibility; no source-count claim from a delivered image",
                      RAW_reads=0, reconstruction_calls=0, tone_reestimated=False, quality_claim=False,
                      photographic_admission=False, physical_placement_claim=False,
                      libraries=dict(python=sys.version, numpy=np.__version__, tifffile=tifffile.__version__, pillow=PIL.__version__),
                      elapsed_seconds=time.perf_counter() - started)
        save(out / "views.json", report)
        print(json.dumps(dict(status=report["status"], out=str(out), all_png_pixels_and_icc_exact=True), allow_nan=False), flush=True)
    except BaseException as error:
        save(out / "failure.json", dict(status="FINAL_CFA_COLOR_VIEW_EXPORT_FAILED", error=repr(error), traceback=traceback.format_exc(),
                                        partial_outputs_preserved=True, quality_claim=False, photographic_admission=False))
        raise


if __name__ == "__main__":
    main()
