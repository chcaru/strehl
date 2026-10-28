"""Bounded cached native-developed TIFF observation; never read original RAWs."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import struct
import sys
import time

import numpy as np
from PIL import Image
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = ROOT / "outputs/raw-quality-2026-10-26"
EXPORT = BASE / "weevil-107-tiff-export/receipt.json"
WITNESSES = ROOT / "experiments/raw-quality-2026-10-26/photo-review/baseline-witnesses.json"
MAP = BASE / "weevil-107-ca-off-alignment.txt"
ICC_SHA = "238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b"
OVERVIEWS = (0, 74, 149, 224, 298)
NAMES = ("turquoise-scales", "thorax-texture", "upper-leg-hairs")


def ref(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 << 20):
            h.update(block)
    s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns, sha256=h.hexdigest())


def save(path, data):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("overviews", "crops"))
    args = parser.parse_args()
    start = time.monotonic()
    export = json.loads(EXPORT.read_text())
    assert ref(EXPORT)["sha256"] == "461ecb3a8e44a82005ed6883718aa85276a74a2ebfca31fb0628809c4ba315a0"
    assert export["status"] == "299_UNALIGNED_NATIVE_RGB16_DEVELOPED" and len(export["frames"]) == 299
    assert ref(WITNESSES)["sha256"] == "826c4ab6c620122449f6575cdd18c0f9ee9cb460f29f6d895e832325d6405888"
    assert ref(MAP)["sha256"] == "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225"
    witnesses = [r for r in json.loads(WITNESSES.read_text())["witnesses"] if r["name"] in NAMES]
    indices = OVERVIEWS
    inputs = [EXPORT, WITNESSES, MAP, Path(__file__).resolve()]
    if args.stage == "crops":
        nominees = HERE / "nominees.json"
        nomination = json.loads(nominees.read_text())
        assert nomination["all_five_complete_views_seen"] and nomination["before_source_crop_view"]
        indices = nomination["source_indices"]
        assert 1 <= len(indices) <= 2 and len(set(indices)) == len(indices) and all(i in OVERVIEWS for i in indices)
        inputs.append(nominees)
    output = HERE / args.stage
    output.mkdir()
    before = [ref(p) for p in inputs]
    transforms = {}
    for line in MAP.read_text().splitlines():
        row = line.split()
        if row and row[0].isdigit():
            assert row[1] == "placed"
            values = [struct.unpack(">d", bytes.fromhex(x))[0] for x in row[2:6]]
            transforms[int(row[0])] = (values, row[2:6])
    records = []
    for index in indices:
        frame = export["frames"][index]
        assert frame["ordinal"] == index
        path = Path(frame["output"])
        assert path.parent == BASE / "weevil-107-tiff-export/frames"
        assert path.name == f"DSC{index+1:05d}.tiff"
        bound = ref(path)
        assert bound["sha256"] == frame["output_sha256"] and bound["bytes"] == frame["output_bytes"]
        with tifffile.TiffFile(path) as f:
            page = f.pages[0]
            assert len(f.pages) == 1 and page.shape == (4688, 7032, 3) and page.dtype == np.uint16
            icc = bytes(page.tags[34675].value)
        assert hashlib.sha256(icc).hexdigest() == ICC_SHA
        rgb = tifffile.memmap(path, mode="r")
        result = dict(index=index, source=bound, original_raw_identity_metadata_only=frame["input"])
        if args.stage == "overviews":
            display = np.empty(rgb.shape, dtype=np.uint8)
            for y in range(0, 4688, 128):
                display[y:y+128] = ((rgb[y:y+128].astype(np.uint32)+128)//257).astype(np.uint8)
            image = Image.fromarray(display)
            image.thumbnail((1617, 1617), Image.Resampling.LANCZOS)
            target = output / f"source-{index:03d}.png"
            image.save(target, icc_profile=icc)
            result.update(complete_source_view=ref(target), overview_dimensions=list(image.size), resized=True)
            del display, image
        else:
            (ar, ai, bx, by), bits = transforms[index]
            result.update(transform_f64_bits=bits, native_center=[3516.0, 2344.0],
                          native_translation=[2*bx, 2*by], scale=math.hypot(ar, ai),
                          rotation_radians=math.atan2(ai, ar), witnesses=[])
            for witness in witnesses:
                x, y, w, h = witness["rect_xywh"]
                assert w == h == 384
                px, py = x+68+191.5, y+46+191.5
                dx, dy = px-3516.0, py-2344.0
                sx, sy = 3516.0+ar*dx-ai*dy+2*bx, 2344.0+ai*dx+ar*dy+2*by
                ox, oy = math.floor(sx-191.5+0.5), math.floor(sy-191.5+0.5)
                assert 0 <= ox <= 7032-384 and 0 <= oy <= 4688-384
                crop = rgb[oy:oy+384, ox:ox+384].copy()
                stem = output / f"source-{index:03d}-{witness['name']}"
                tiff, png = stem.with_suffix(".tiff"), stem.with_suffix(".png")
                tifffile.imwrite(tiff, crop, photometric="rgb", metadata=None,
                                 extratags=[(34675,"B",len(icc),icc,False)])
                small = ((crop.astype(np.uint32)+128)//257).astype(np.uint8)
                Image.fromarray(small).save(png, icc_profile=icc)
                with tifffile.TiffFile(tiff) as check:
                    assert np.array_equal(check.asarray(), rgb[oy:oy+384, ox:ox+384])
                    assert bytes(check.pages[0].tags[34675].value) == icc
                with Image.open(png) as check:
                    assert check.size == (384,384) and check.info["icc_profile"] == icc
                    assert np.array_equal(np.asarray(check), small)
                result["witnesses"].append(dict(name=witness["name"], baseline_xywh=witness["rect_xywh"],
                    reference_active_center=[px,py], mapped_source_center=[sx,sy], source_xywh=[ox,oy,384,384],
                    center_rounding_error=[ox+191.5-sx,oy+191.5-sy], resized=False,
                    exact_subarray=True, rgb16=ref(tiff), png=ref(png)))
        del rgb
        assert ref(path) == bound
        records.append(result)
    assert [ref(p) for p in inputs] == before
    save(output / "receipt.json", dict(status=args.stage.upper()+"_READY_NO_VERDICT", quality_claim=False,
        command=[sys.executable,*sys.orig_argv[1:]], inputs=before, source_tiffs_unchanged=True,
        original_raw_reads=0, records=records, seconds=time.monotonic()-start,
        display="Unmodified developed RGB16 and original ICC; PNG (value+128)//257. Complete overviews only are resized.",
        mapping="Reference149 native pixel center plus(68,46); q=C+a*(p-C)+2b, C=(3516,2344); round crop origin. Map locates context only. No source pixel warp, CA, fit, scale normalization or equal-footprint metric."))
    print(f"{args.stage}: {len(records)} bound cached sources; {time.monotonic()-start:.3f}s")


if __name__ == "__main__":
    main()
