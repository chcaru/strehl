"""Fixed cached-TIFF source observation. No RAW read, source score or fitting."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import struct
import sys
import time

import numpy as np
import PIL
from PIL import Image, ImageDraw
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / "outputs/raw-quality-2026-10-26"
EXPORT = BASE / "weevil-107-tiff-export/receipt.json"
WITNESSES = ROOT / "experiments/raw-quality-2026-10-26/photo-review/baseline-witnesses.json"
MAP = BASE / "weevil-107-ca-off-alignment.txt"
INDICES = tuple(range(0, 291, 10)) + (298,)
NAMES = ("upper-leg-hairs", "turquoise-scales", "thorax-texture", "elytron-seam", "blue-joint")
ICC_SHA = "238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b"
PINS = ((EXPORT, "461ecb3a8e44a82005ed6883718aa85276a74a2ebfca31fb0628809c4ba315a0"),
        (WITNESSES, "826c4ab6c620122449f6575cdd18c0f9ee9cb460f29f6d895e832325d6405888"),
        (MAP, "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225"))


def ref(path):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1 << 20):
            h.update(block)
    s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns, sha256=h.hexdigest())


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def header(path):
    with tifffile.TiffFile(path) as f:
        page = f.pages[0]
        assert len(f.pages) == 1 and page.shape == (4688, 7032, 3) and page.dtype == np.uint16
        assert int(page.compression) == 1
        icc = bytes(page.tags[34675].value)
    assert hashlib.sha256(icc).hexdigest() == ICC_SHA
    return icc


def sheets(output, name, entries, icc, size):
    """Navigation only: eight labelled complete images per page, fixed order."""
    records = []
    tw, th = size
    for first in range(0, len(entries), 8):
        page = Image.new("RGB", (4 * (tw + 8), 2 * (th + 32) + 28), (24, 24, 24))
        draw = ImageDraw.Draw(page)
        draw.text((8, 6), name + " - resized navigation only; inspect individual originals", fill="white")
        page_rows = []
        for position, (index, path) in enumerate(entries[first:first + 8]):
            x, y = (position % 4) * (tw + 8) + 4, (position // 4) * (th + 32) + 28
            draw.text((x, y), f"source {index:03d} / DSC{index + 1:05d}" + (" UNAVAILABLE" if path is None else ""), fill="white")
            if path is not None:
                with Image.open(path) as image:
                    assert image.info.get("icc_profile") == icc
                    small = image.convert("RGB")
                    small.thumbnail((tw, th), Image.Resampling.LANCZOS)
                    page.paste(small, (x, y + 20))
                    page_rows.append(dict(index=index, source=ref(path), thumbnail_dimensions=list(small.size)))
            else:
                page_rows.append(dict(index=index, unavailable=True))
        target = output / f"{name}-page-{first // 8 + 1:02d}.png"
        page.save(target, icc_profile=icc)
        records.append(dict(image=ref(target), entries=page_rows, resized=True, quality_use=False))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    start = time.monotonic()
    out = args.out.resolve()
    assert out.parent == (ROOT / "outputs/raw-quality-2026-10-27").resolve() and not out.exists()
    dependencies = [p for p, _ in PINS] + [Path(__file__), HERE / "run-bounded.py", HERE / "brief.md",
                    Path(np.__file__), Path(PIL.__file__), Path(Image.__file__), Path(tifffile.__file__)]
    before = [ref(p) for p in dependencies]
    for path, expected in PINS:
        assert ref(path)["sha256"] == expected
    export = json.loads(EXPORT.read_text())
    assert export["status"] == "299_UNALIGNED_NATIVE_RGB16_DEVELOPED" and len(export["frames"]) == 299
    witness_data = json.loads(WITNESSES.read_text())
    by_name = {row["name"]: row for row in witness_data["witnesses"]}
    witnesses = [by_name[name] for name in NAMES]
    assert len(INDICES) == 31 and all(row["rect_xywh"][2:] == [384, 384] for row in witnesses)
    transforms = {}
    for line in MAP.read_text().splitlines():
        row = line.split()
        if row and row[0].isdigit():
            index = int(row[0])
            assert row[1] == "placed" and index not in transforms
            values = [struct.unpack(">d", bytes.fromhex(x))[0] for x in row[2:6]]
            assert len(values) == 4 and all(math.isfinite(v) for v in values)
            transforms[index] = (values, row[2:6])
    assert set(transforms) == set(range(299))
    records = []
    for index in INDICES:
        frame = export["frames"][index]
        path = Path(frame["output"]).resolve()
        assert frame["ordinal"] == index
        assert path.parent == (BASE / "weevil-107-tiff-export/frames").resolve()
        assert path.name == f"DSC{index + 1:05d}.tiff"
        binding = ref(path)
        assert binding["sha256"] == frame["output_sha256"] and binding["bytes"] == frame["output_bytes"]
        records.append(dict(index=index, source=binding, original_raw_identity_metadata_only=frame["input"]))
    out.mkdir()
    whole, crops, contact = (out / name for name in ("whole", "crops", "contact-sheets"))
    for directory in (whole, crops, contact):
        directory.mkdir()
    # Complete orientation views for every fixed source precede ALL crop exports.
    for row in records:
        path = Path(row["source"]["path"])
        icc = header(path)
        rgb = tifffile.memmap(path, mode="r")
        display = np.empty(rgb.shape, dtype=np.uint8)
        for y in range(0, 4688, 128):
            display[y:y + 128] = ((rgb[y:y + 128].astype(np.uint32) + 128) // 257).astype(np.uint8)
        image = Image.fromarray(display)
        image.thumbnail((1617, 1617), Image.Resampling.LANCZOS)
        target = whole / f"source-{row['index']:03d}.png"
        image.save(target, icc_profile=icc)
        row.update(complete_source_view=ref(target), overview_dimensions=list(image.size), overview_resized=True)
        del rgb, display, image
        print(f"whole {row['index']:03d}", flush=True)
    whole_sheets = sheets(contact, "whole-sources", [(r["index"], Path(r["complete_source_view"]["path"])) for r in records], icc, (384, 256))
    save(out / "whole-views.json", dict(status="ALL_31_COMPLETE_ORIENTATION_VIEWS_EXPORTED_FIRST", records=records, contact_sheets=whole_sheets,
                                      human_inspection_claimed=False, quality_claim=False))
    for row in records:
        path = Path(row["source"]["path"])
        icc = header(path)
        rgb = tifffile.memmap(path, mode="r")
        (ar, ai, bx, by), bits = transforms[row["index"]]
        row.update(transform_f64_bits=bits, native_center=[3516., 2344.], native_translation=[2 * bx, 2 * by],
                   scale=math.hypot(ar, ai), rotation_radians=math.atan2(ai, ar), witnesses=[])
        for witness in witnesses:
            x, y, w, h = witness["rect_xywh"]
            px, py = x + 68 + 191.5, y + 46 + 191.5
            dx, dy = px - 3516., py - 2344.
            sx, sy = 3516. + ar * dx - ai * dy + 2 * bx, 2344. + ai * dx + ar * dy + 2 * by
            ox, oy = math.floor(sx - 191.5 + .5), math.floor(sy - 191.5 + .5)
            result = dict(name=witness["name"], baseline_xywh=witness["rect_xywh"], reference_active_center=[px, py],
                          mapped_source_center=[sx, sy], source_xywh=[ox, oy, 384, 384],
                          center_rounding_error=[ox + 191.5 - sx, oy + 191.5 - sy], resized=False)
            if not (0 <= ox <= 7032 - 384 and 0 <= oy <= 4688 - 384):
                result.update(status="UNAVAILABLE_OUT_OF_BOUNDS", relocated=False)
            else:
                crop = rgb[oy:oy + 384, ox:ox + 384].copy()
                stem = crops / f"source-{row['index']:03d}-{witness['name']}"
                tp, pp = stem.with_suffix(".tiff"), stem.with_suffix(".png")
                tifffile.imwrite(tp, crop, photometric="rgb", metadata=None, extratags=[(34675, "B", len(icc), icc, False)])
                small = ((crop.astype(np.uint32) + 128) // 257).astype(np.uint8)
                Image.fromarray(small).save(pp, icc_profile=icc)
                with tifffile.TiffFile(tp) as check:
                    assert np.array_equal(check.asarray(maxworkers=1), rgb[oy:oy + 384, ox:ox + 384])
                    assert bytes(check.pages[0].tags[34675].value) == icc
                with Image.open(pp) as check:
                    assert check.size == (384, 384) and check.info["icc_profile"] == icc
                    assert np.array_equal(np.asarray(check), small)
                result.update(status="EXACT_NATIVE_SUBARRAY", exact_subarray=True, rgb16=ref(tp), png=ref(pp))
            row["witnesses"].append(result)
        del rgb
        print(f"crops {row['index']:03d}", flush=True)
    crop_sheets = {}
    for name in NAMES:
        entries = []
        for row in records:
            witness = next(v for v in row["witnesses"] if v["name"] == name)
            entries.append((row["index"], Path(witness["png"]["path"]) if "png" in witness else None))
        crop_sheets[name] = sheets(contact, name, entries, icc, (192, 192))
    assert [ref(p) for p in dependencies] == before
    assert all(ref(Path(row["source"]["path"])) == row["source"] for row in records)
    save(out / "receipt.json", dict(status="COMPLETE_CACHED_SOURCE_SUPPORT_NO_VERDICT", indices=list(INDICES), witness_names=list(NAMES),
         all_complete_views_exported_before_crops=True, human_inspection_claimed=False, quality_claim=False, original_raw_reads=0,
         selected_source_tiffs_unchanged=True, dependency_bindings_unchanged=True, dependencies=before, records=records,
         whole_contact_sheets=whole_sheets, witness_contact_sheets=crop_sheets, icc_sha256=ICC_SHA,
         command=[sys.executable, *sys.orig_argv[1:]], seconds=time.monotonic() - start,
         versions=dict(numpy=np.__version__, pillow=PIL.__version__, tifffile=tifffile.__version__),
         display="Original developed RGB16/ICC; PNG=(RGB16+128)//257. Whole views and labelled contact sheets resized for navigation only; individual384 crops unresampled.",
         mapping="Reference149 active center uses crop offset(68,46); q=C+a*(p-C)+2b, C=(3516,2344). Integer-rounded source rectangles locate context; no warp, fit, CA, equal-footprint claim or source score.",
         limitation="Premerge source development differs from native postmerge development; sources are supporting observations, never an argmax oracle or optical ceiling."))
    print(f"complete: {len(records)} cached sources, {len(records) * len(NAMES)} fixed witness observations", flush=True)


if __name__ == "__main__":
    main()
