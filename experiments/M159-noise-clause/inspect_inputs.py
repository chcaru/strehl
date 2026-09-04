from pathlib import Path
import struct

import tifffile


PATHS = [
    Path(r"C:\dev\macro\out\coffee-bean\stack.tif"),
    Path(r"C:\dev\strehl-out\DELIVER-V6\masters\coffee-bean.tiff"),
    Path(r"C:\dev\macro\out\stack_test2_rec2020.tif"),
    Path(r"D:\edited\macro\test2\20260507-DSC00001.tif"),
    Path(r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif"),
    Path(r"C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff"),
]


def describe_icc(icc: bytes) -> list[str]:
    rows = [f"profile_size={struct.unpack('>I', icc[0:4])[0]}"]
    count = struct.unpack(">I", icc[128:132])[0]
    rows.append(f"tag_count={count}")
    for index in range(count):
        offset = 132 + 12 * index
        signature, body_offset, body_size = struct.unpack(
            ">4sII", icc[offset : offset + 12]
        )
        if signature not in (b"desc", b"rTRC", b"gTRC", b"bTRC"):
            continue
        body = icc[body_offset : body_offset + body_size]
        kind = body[:4]
        label = signature.decode("ascii")
        if kind == b"mluc":
            text_length = struct.unpack(">I", body[20:24])[0]
            text_offset = struct.unpack(">I", body[24:28])[0]
            text = body[text_offset : text_offset + text_length].decode(
                "utf-16-be", "replace"
            )
            rows.append(f"{label}=mluc:{text}")
        elif kind == b"desc":
            text_length = struct.unpack(">I", body[8:12])[0]
            text = body[12 : 12 + max(0, text_length - 1)].decode(
                "latin1", "replace"
            )
            rows.append(f"{label}=desc:{text}")
        elif kind == b"curv":
            curve_count = struct.unpack(">I", body[8:12])[0]
            if curve_count == 0:
                rows.append(f"{label}=identity")
            elif curve_count == 1:
                gamma = struct.unpack(">H", body[12:14])[0] / 256.0
                rows.append(f"{label}=gamma:{gamma:.6f}")
            else:
                rows.append(f"{label}=curve:{curve_count}")
        elif kind == b"para":
            function_type = struct.unpack(">H", body[8:10])[0]
            rows.append(f"{label}=parametric:{function_type}")
        else:
            rows.append(f"{label}={kind!r}")
    return rows


def main() -> None:
    for path in PATHS:
        print(f"\nPATH: {path}")
        print(f"EXISTS: {path.exists()}")
        if not path.exists():
            continue
        print(f"BYTES: {path.stat().st_size}")
        with tifffile.TiffFile(path) as tif:
            page = tif.pages[0]
            print(f"SHAPE: {page.shape}")
            print(f"DTYPE: {page.dtype}")
            for name in (
                "ImageDescription",
                "Software",
                "DateTime",
                "InterColorProfile",
                "XResolution",
                "YResolution",
                "ResolutionUnit",
            ):
                tag = page.tags.get(name)
                if tag is None:
                    print(f"{name}: <absent>")
                    continue
                value = tag.value
                if isinstance(value, bytes):
                    print(f"{name}: <{len(value)} bytes>")
                    if name == "InterColorProfile":
                        for row in describe_icc(value):
                            print(f"  {row}")
                else:
                    print(f"{name}: {value}")


if __name__ == "__main__":
    main()
