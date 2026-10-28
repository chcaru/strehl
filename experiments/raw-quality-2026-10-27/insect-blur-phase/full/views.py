"""Publish saved baseline/p1/p2 complete photographs; no reconstruction or retone.

The conversion/readback pattern is reused from the commissioned
direct-cfa-streamed-normal/full-photograph-views.py. Root owns process-terminal
qualification before invoking this saved-file helper.
"""
from pathlib import Path
import argparse
import hashlib
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
NAMES = ("baseline", "p1", "p2")
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
    parser.add_argument("--render", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    source, out = args.render.resolve(), args.out.resolve()
    workspace_outputs = (ROOT / "outputs").resolve()
    require(source.is_relative_to(workspace_outputs) and source.is_dir(), "workspace render directory required")
    require(out.is_relative_to(workspace_outputs) and not out.exists()
            and not out.is_relative_to(source) and out.parent.is_dir(), "fresh separate workspace output required")
    out.mkdir()
    try:
        import numpy as np
        import tifffile
        from PIL import Image
        import PIL

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
        receipt_path = remember(source / "receipt.json")
        scientific = read(receipt_path)
        require(scientific["status"] == "COMPLETE299_INSECT_PHASE_MAP_RENDERS"
                and scientific["all_frames_completed"] is True and scientific["frames"] == 299
                and scientific["native_decode_count"] == 299 and scientific["normal_fold_count"] == 897
                and scientific["native_dimensions"] == [WIDTH, HEIGHT]
                and scientific["crop_quad_xywh"] == [34, 23, 3448, 2298]
                and scientific["native_crop_origin"] == [68, 46] and scientific["reference"] == 149
                and scientific["resampler"] == "catmull-rom" and scientific["gather_backend"] == "cpu"
                and scientific["arithmetic_chunks"] == [75, 75, 75, 74], "complete fixed299 rendering contract differs")
        require(all(scientific[key] is True for key in (
            "baseline_identity_exact", "baseline_material_metadata_exact", "all_arm_development_identical",
            "canonical_noise_probes_preserved", "all299_original_bytes_and_metadata_unchanged", "all_bound_inputs_unchanged"))
            and scientific["extra_green_phase_probes"] == 0
            and all(scientific[key] is False for key in ("quality_claim", "photographic_admission", "physical_placement_claim")),
            "render qualification or claim flags differ")
        require([arm["name"] for arm in scientific["arms"]] == list(NAMES), "exact three-arm order required")
        require([m["name"] for m in scientific["maps"]] == list(NAMES), "map order differs")
        for entry in scientific["maps"]:
            bind(entry)
        identity_path = bind(scientific["baseline_identity"])
        identity = read(identity_path)
        require(identity["exact"] is True and identity["material_metadata_exact"] is True, "baseline null absent")
        support_path, frames_path = bind(scientific["support"]), bind(scientific["frame_receipts"])
        support, frames = read(support_path), read(frames_path)
        require(support["fixed_crop_quad_xywh"] == [34, 23, 3448, 2298] and support["post_crop_used"] is False
                and [v["name"] for v in support["arms"]] == list(NAMES)
                and all(v["all_supported"] is True and v["supported_by_source"] == [True] * 299 for v in support["arms"]),
                "fixed complete source support absent")
        require(frames["count"] == frames["decode_count"] == 299 and frames["map_order"] == list(NAMES)
                and [v["index"] for v in frames["frames"]] == list(range(299))
                and all(v["native_decode_count"] == 1 and [a["name"] for a in v["arms"]] == list(NAMES)
                        for v in frames["frames"]), "incomplete source/arm population")
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
        for arm in scientific["arms"]:
            name = arm["name"]
            require(arm["entire_output"] is True, "partial image is not a complete arm")
            master, linear, cfa = bind(arm["rgb16"]), bind(arm["linear_rgb32"]), bind(arm["cfa"])
            require(master.samefile(source / f"{name}-master.tiff")
                    and linear.samefile(source / f"{name}-linear.tiff")
                    and cfa.samefile(source / f"{name}-cfa-dn.f32le"), "arm does not point to its own saved outputs")
            arm_receipt = remember(source / f"{name}-receipt.json")
            require(read(arm_receipt) == arm, "inline/saved arm receipt differs")
            require(arm["material_metadata"] == scientific["arms"][0]["material_metadata"]
                    and arm["linear_material_metadata"] == scientific["arms"][0]["linear_material_metadata"],
                    "three-arm development metadata differs")
            with tifffile.TiffFile(linear) as tf:
                require(len(tf.pages) == 1 and tf.pages[0].shape == (HEIGHT, WIDTH, 3)
                        and tf.pages[0].dtype == np.float32, "complete float master header differs")
            require(bindings[str(cfa)]["bytes"] == WIDTH * HEIGHT * 4, "complete CFA extent differs")
            sources.append((arm, master, linear, cfa))
        require(len({str(v[1]) for v in sources}) == 3, "arm masters substituted")
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
            if name == "baseline":
                require(pixel_sha == BASE_PIXELS_SHA and arm["pixel_hashes"]["linear_rgb32"] == BASE_LINEAR_SHA,
                        "complete held baseline parity differs")
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
                          material_metadata=arm["material_metadata"], linear_material_metadata=arm["linear_material_metadata"],
                          rgb16_pixels_sha256=pixel_sha, complete_jpeg=ref(full_path), overview=ref(overview_path),
                          native_dimensions=[WIDTH, HEIGHT], witnesses=rows, all_png_pixels_and_icc_exact=True,
                          entire_output=True, display="(RGB16+128)//257; same ICC; no retone; JPEG98/subsampling0; native PNGs unresized")
            save(arm_out / "views.json", output)
            outputs.append(output)
            del pixels, rgb8, image, overview

        lines = ["# Complete phase-registration photographs", "",
                 "No quality verdict. Inspect all three complete images before the ten fixed native witnesses.", "",
                 "These images preserve the native renderer's held tone/ICC. Only overviews resize; JPEG is lossy, RGB16 masters and PNG crops remain the pixel references.", "",
                 "| Arm | Complete photograph | RGB16 full master | Float full master | Orientation |",
                 "| --- | --- | --- | --- | --- |"]
        for arm in outputs:
            lines.append("| " + arm["name"] + " | " + " | ".join((link("complete JPEG", arm["complete_jpeg"]["path"]),
                         link("RGB16", arm["rgb16"]["path"]), link("RGB32", arm["linear_rgb32"]["path"]),
                         link("overview", arm["overview"]["path"]))) + " |")
        lines.extend(["", "Retained full-workflow references: native CA-off shares the fixed crop; Helicon B4/B8 have their own alignment/scale and RGB development before fusion. Their mapped crops are correspondence aids, not placement truth.", ""])
        for old in references:
            lines.append("- " + old["name"] + ": " + link("whole photograph", old["complete_jpeg"]["path"])
                         + "; " + link("full master", old["master"]["path"]))
        lines.extend(["", "| Fixed native384 witness | baseline | p1 | p2 | held native | Helicon B4 | Helicon B8 |",
                      "| --- | --- | --- | --- | --- | --- | --- |"])
        for witness in witnesses:
            row = [witness["name"] + " " + str(witness["rect_xywh"])]
            for arm in outputs:
                crop = next(v for v in arm["witnesses"] if v["name"] == witness["name"])
                row.append(link(arm["name"], crop["png"]["path"]))
            for old in references:
                crop = next(v for v in old["witnesses"] if v["name"] == witness["name"])
                row.append(link(old["name"], crop["png"]["path"]))
            lines.append("| " + " | ".join(row) + " |")
        lines.extend(["", "Physical gauge: reference149,3516×2344 guide, native crop(68,46,6896,4596). The renderer retains legacy per-source MHC/Catmull remosaic. Phase/cycle scores are not geometric ground truth.", ""])
        index = out / "index.md"
        with index.open("x", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines))
        for old in bindings.values():
            require(ref(old["path"]) == old, "saved input bytes/metadata changed during presentation")
        report = dict(schema=1, status="COMPLETE_THREE_PHASE_MAP_VIEWS_READY_NO_VERDICT", complete=True,
                      render_receipt=bindings[str(receipt_path)], source_status=scientific["status"],
                      frames=299, arms=outputs, references=references, witness_manifest=bindings[str(PHOTO.resolve())],
                      inputs_unchanged=True, all_png_pixels_and_icc_exact=True, native_dimensions=[WIDTH, HEIGHT],
                      crop_quad_xywh=[34, 23, 3448, 2298], native_crop_origin=[68, 46], reference=149,
                      icc_sha256=ICC_SHA, index=ref(index), process_terminal_audit="root wrapper responsibility; not inferred here",
                      RAW_reads=0, reconstruction_calls=0, tone_reestimated=False, quality_claim=False,
                      photographic_admission=False, physical_placement_claim=False,
                      libraries=dict(python=sys.version, numpy=np.__version__, tifffile=tifffile.__version__, pillow=PIL.__version__),
                      elapsed_seconds=time.perf_counter() - started)
        save(out / "views.json", report)
        print(json.dumps(dict(status=report["status"], out=str(out), all_png_pixels_and_icc_exact=True), allow_nan=False), flush=True)
    except BaseException as error:
        save(out / "failure.json", dict(status="PHASE_MAP_VIEW_EXPORT_FAILED", error=repr(error), traceback=traceback.format_exc(),
                                        partial_outputs_preserved=True, quality_claim=False, photographic_admission=False))
        raise


if __name__ == "__main__":
    main()
