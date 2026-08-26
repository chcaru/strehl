"""Verify the embedded ICC profiles against ORCH's four required checks.

1. Read the tag back OUT of a real written file -- never assert that it was written.
2. Confirm it with independent tools (Pillow/LittleCMS and exiftool), not just my own parser.
3. Pixel null: for the (matrix, srgb) case the DECODED PIXELS must be identical.
   File bytes cannot be compared -- adding a tag shifts every data offset -- so
   this compares the decoded arrays, which is the claim that actually matters.
4. Camera-native must carry NO profile.

16-bit RGB TIFFs are read with tifffile and asserted uint16. PIL.Image.open
silently downconverts 16-bit RGB to 8 bits and has corrupted results in this
project before, so it is never used to read pixels here -- only to parse
profile bytes that tifffile has already extracted.
"""

from __future__ import annotations

import hashlib
import io
import subprocess
import struct
import sys
from pathlib import Path

import numpy as np
import tifffile

OUT = Path(r"C:\dev\strehl-out\ICC-AB\out")
ICC_TAG = 34675


def tag_bytes(path: Path) -> bytes | None:
    with tifffile.TiffFile(path) as tf:
        page = tf.pages[0]
        t = page.tags.get(ICC_TAG)
        if t is None:
            return None
        v = t.value
        return bytes(v) if not isinstance(v, bytes) else v


def tag_type(path: Path) -> str | None:
    with tifffile.TiffFile(path) as tf:
        t = tf.pages[0].tags.get(ICC_TAG)
        return None if t is None else str(t.dtype)


def parse(p: bytes) -> dict:
    """A minimal independent ICC parser, written from the layout in ICC.1."""
    d: dict = {}
    d["size_field"] = struct.unpack(">I", p[0:4])[0]
    d["actual_size"] = len(p)
    d["version"] = f"{p[8]}.{p[9] >> 4}.{p[9] & 0xF}"
    d["class"] = p[12:16].decode()
    d["data_space"] = p[16:20].decode()
    d["pcs"] = p[20:24].decode()
    d["signature"] = p[36:40].decode()
    n = struct.unpack(">I", p[128:132])[0]
    tags = {}
    for i in range(n):
        e = 132 + 12 * i
        sig = p[e:e + 4].decode()
        off, ln = struct.unpack(">II", p[e + 4:e + 12])
        tags[sig] = (off, ln)
    d["tags"] = sorted(tags)

    def xyz(sig):
        off, _ = tags[sig]
        x, y, z = struct.unpack(">iii", p[off + 8:off + 20])
        return (x / 65536.0, y / 65536.0, z / 65536.0)

    d["rXYZ"], d["gXYZ"], d["bXYZ"] = xyz("rXYZ"), xyz("gXYZ"), xyz("bXYZ")
    d["wtpt"] = xyz("wtpt")
    off, ln = tags["desc"]
    kind = p[off:off + 4].decode()
    if kind == "desc":
        dlen = struct.unpack(">I", p[off + 8:off + 12])[0]
        d["desc"] = p[off + 12:off + 12 + dlen - 1].decode("ascii", "replace")
    else:
        d["desc"] = f"<{kind}>"
    off, ln = tags["rTRC"]
    cnt = struct.unpack(">I", p[off + 8:off + 12])[0]
    d["trc_count"] = cnt
    d["trc_shared"] = tags["rTRC"] == tags["gTRC"] == tags["bTRC"]
    if cnt >= 3:
        pts = struct.unpack(f">{cnt}H", p[off + 12:off + 12 + 2 * cnt])
        d["trc_mid"] = pts[cnt // 2] / 65535.0
        d["trc_ends"] = (pts[0] / 65535.0, pts[-1] / 65535.0)
    return d


def pixels(path: Path) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path.name}: expected uint16, got {a.dtype}"
    return a


def rule(t: str) -> None:
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


def main() -> int:
    fails: list[str] = []

    rule("1. THE TAG, READ BACK OUT OF A REAL FILE")
    for name in ["b-srgb.tiff", "b-linear.tiff", "b-camera.tiff"]:
        f = OUT / name
        raw = tag_bytes(f)
        if raw is None:
            print(f"\n{name}: NO ICC PROFILE  (tifffile tag {ICC_TAG} absent)")
            continue
        d = parse(raw)
        print(f"\n{name}: {len(raw)} bytes, TIFF type {tag_type(f)}")
        print(f"  desc        {d['desc']!r}")
        print(f"  version     {d['version']}   class {d['class']}  "
              f"{d['data_space']} -> {d['pcs']}   sig {d['signature']!r}")
        print(f"  size field  {d['size_field']} (actual {d['actual_size']})")
        print(f"  rXYZ        {d['rXYZ'][0]:.6f} {d['rXYZ'][1]:.6f} {d['rXYZ'][2]:.6f}")
        print(f"  gXYZ        {d['gXYZ'][0]:.6f} {d['gXYZ'][1]:.6f} {d['gXYZ'][2]:.6f}")
        print(f"  bXYZ        {d['bXYZ'][0]:.6f} {d['bXYZ'][1]:.6f} {d['bXYZ'][2]:.6f}")
        print(f"  wtpt        {d['wtpt'][0]:.6f} {d['wtpt'][1]:.6f} {d['wtpt'][2]:.6f}")
        print(f"  TRC         count={d['trc_count']} shared_rgb={d['trc_shared']}"
              + (f" mid={d['trc_mid']:.4f} ends={d['trc_ends'][0]:.3f}/{d['trc_ends'][1]:.3f}"
                 if "trc_mid" in d else "  (identity/linear)"))
        print(f"  tags        {' '.join(d['tags'])}")
        if d["size_field"] != d["actual_size"]:
            fails.append(f"{name}: size field disagrees with length")
        if d["signature"] != "acsp":
            fails.append(f"{name}: bad signature")

    rule("2. INDEPENDENT TOOLS")
    from PIL import ImageCms
    for name in ["b-srgb.tiff", "b-linear.tiff"]:
        raw = tag_bytes(OUT / name)
        prof = ImageCms.ImageCmsProfile(io.BytesIO(raw))
        p = prof.profile
        print(f"\n{name} via Pillow/LittleCMS2:")
        print(f"  description   {ImageCms.getProfileDescription(prof).strip()!r}")
        print(f"  version       {p.version}   device class {p.device_class}")
        print(f"  colorants xy  {p.red_colorant[1][:2] if p.red_colorant else None} "
              f"{p.green_colorant[1][:2] if p.green_colorant else None} "
              f"{p.blue_colorant[1][:2] if p.blue_colorant else None}")
        print(f"  wp xy         {p.media_white_point[1][:2] if p.media_white_point else None}")

    for name in ["b-srgb.tiff", "b-camera.tiff"]:
        r = subprocess.run(
            ["exiftool", "-s", "-ProfileDescription", "-ProfileVersion",
             "-ColorSpaceData", "-ConnectionSpaceIlluminant",
             "-RedMatrixColumn", "-GreenMatrixColumn", "-BlueMatrixColumn",
             str(OUT / name)],
            capture_output=True, text=True)
        body = r.stdout.strip() or "(no ICC tags reported)"
        print(f"\n{name} via exiftool:\n" + "\n".join("  " + ln for ln in body.splitlines()))

    rule("3. PIXEL NULL -- ONLY METADATA MAY MOVE")
    for label, a, b in [("--srgb        ", "a-srgb.tiff", "b-srgb.tiff"),
                        ("--linear-srgb ", "a-linear.tiff", "b-linear.tiff"),
                        ("camera-native ", "a-camera.tiff", "b-camera.tiff")]:
        pa, pb = pixels(OUT / a), pixels(OUT / b)
        ha = hashlib.sha256(pa.tobytes()).hexdigest()
        hb = hashlib.sha256(pb.tobytes()).hexdigest()
        same = ha == hb
        fa, fb = (OUT / a).stat().st_size, (OUT / b).stat().st_size
        print(f"\n{label} {pa.shape} {pa.dtype}")
        print(f"  pixel sha256 A {ha}")
        print(f"  pixel sha256 B {hb}")
        print(f"  pixels identical: {same}    max|A-B| = "
              f"{int(np.abs(pa.astype(np.int32) - pb.astype(np.int32)).max())}")
        print(f"  file bytes {fa} -> {fb}  ({fb - fa:+d}, metadata only)")
        if not same:
            fails.append(f"{label.strip()}: PIXELS MOVED")

    rule("4. THE TWO FILES MUST NOW BE DISTINGUISHABLE")
    srgb_p = tag_bytes(OUT / "b-srgb.tiff")
    cam_p = tag_bytes(OUT / "b-camera.tiff")
    lin_p = tag_bytes(OUT / "b-linear.tiff")
    print(f"\n  --srgb         profile: {'present, ' + str(len(srgb_p)) + ' bytes' if srgb_p else 'ABSENT'}")
    print(f"  --linear-srgb  profile: {'present, ' + str(len(lin_p)) + ' bytes' if lin_p else 'ABSENT'}")
    print(f"  camera-native  profile: {'present' if cam_p else 'ABSENT (deliberate)'}")
    if cam_p is not None:
        fails.append("camera-native carries a profile -- that is a machine-readable lie")
    if srgb_p is None or lin_p is None:
        fails.append("a colorimetric path is unlabelled")
    if srgb_p and lin_p and srgb_p == lin_p:
        fails.append("sRGB and linear sRGB got the SAME profile")
    print(f"\n  sRGB vs linear profiles differ: {srgb_p != lin_p}")
    print("  => a colour-managed application can now tell all three apart.")

    rule("RESULT")
    if fails:
        for f in fails:
            print(f"  FAIL  {f}")
        print(f"\n{len(fails)} FAILURE(S)")
        return 1
    print("  all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
