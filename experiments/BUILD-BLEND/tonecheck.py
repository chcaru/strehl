"""Read the ImageDescription a strehl render writes into its own TIFF.

image_out.rs writes the tone parameters into the file description, and ONLY
when a tone rendering was applied:

    match &dev.tone {
        Some(t) => "... Tone rendering: black .., white .. (linear, luminance
                    percentiles ../.. with white mapped to ..) ..."
        None    => "{space} {wb}"
    }

So the file itself records whether a data-dependent global transform touched
it. That is the question ORCH asked -- whether cross-arm absolute DN is
contaminated by a per-image normalisation -- and it is answerable per file,
without re-rendering anything.

Reads the TIFF header directly rather than decoding 198 MB of pixels.
"""

import struct
import sys

TAG_IMAGEDESCRIPTION = 270
TAG_WIDTH = 256
TAG_HEIGHT = 257


def read_desc(path):
    with open(path, "rb") as fh:
        head = fh.read(8)
        if head[:2] == b"II":
            end = "<"
        elif head[:2] == b"MM":
            end = ">"
        else:
            raise ValueError(f"{path}: not a TIFF (magic {head[:2]!r})")

        magic = struct.unpack(end + "H", head[2:4])[0]
        if magic == 42:
            big = False
            off = struct.unpack(end + "I", head[4:8])[0]
        elif magic == 43:
            big = True
            fh.seek(8)
            off = struct.unpack(end + "Q", fh.read(8))[0]
        else:
            raise ValueError(f"{path}: unknown TIFF magic {magic}")

        fh.seek(off)
        if big:
            n = struct.unpack(end + "Q", fh.read(8))[0]
            entry, hdr = 20, "HHQQ"
        else:
            n = struct.unpack(end + "H", fh.read(2))[0]
            entry, hdr = 12, "HHII"

        out = {}
        raw = fh.read(entry * n)
        for i in range(n):
            tag, typ, cnt, val = struct.unpack(
                end + hdr, raw[i * entry:(i + 1) * entry]
            )
            if tag in (TAG_WIDTH, TAG_HEIGHT):
                out[tag] = val
            elif tag == TAG_IMAGEDESCRIPTION:
                inline = 8 if big else 4
                if cnt <= inline:
                    b = struct.pack(end + ("Q" if big else "I"), val)[:cnt]
                else:
                    here = fh.tell()
                    fh.seek(val)
                    b = fh.read(cnt)
                    fh.seek(here)
                out[tag] = b.rstrip(b"\x00").decode("utf-8", "replace")
        return out


def main(paths):
    print("=" * 74)
    print("Does each render carry a DATA-DEPENDENT global transform?")
    print("=" * 74)
    verdicts = []
    for p in paths:
        try:
            d = read_desc(p)
        except Exception as exc:  # noqa: BLE001
            print(f"\n{p}\n  ERROR: {exc}")
            verdicts.append((p, "ERROR"))
            continue

        desc = d.get(TAG_IMAGEDESCRIPTION)
        name = p.rsplit("\\", 1)[-1]
        print(f"\n{name}   ({d.get(TAG_WIDTH)}x{d.get(TAG_HEIGHT)})")
        if desc is None:
            print("  NO ImageDescription tag at all.")
            verdicts.append((name, "NO-TAG"))
            continue

        toned = "Tone rendering:" in desc
        print(f"  description: {len(desc)} chars")
        print(f"  {desc}")
        if toned:
            seg = desc.split("Tone rendering:", 1)[1]
            print(f"  >>> TONED. per-image percentiles ->{seg[:80].strip()}")
            verdicts.append((name, "TONED"))
        else:
            print("  >>> NO TONE. No per-image percentile term in this file.")
            verdicts.append((name, "LINEAR"))

    print("\n" + "=" * 74)
    print("VERDICT")
    print("=" * 74)
    for name, v in verdicts:
        print(f"  {v:8}  {name}")

    kinds = {v for _, v in verdicts}
    print()
    if kinds == {"LINEAR"}:
        print("  All files untoned. The only global term is the raw")
        print("  normalisation by (white - black), which comes from the CAMERA")
        print("  metadata and is the SAME fixed transform for both arms of one")
        print("  capture. Cross-arm absolute DN is NOT contaminated.")
    elif "TONED" in kinds and "LINEAR" in kinds:
        print("  MIXED. Some files carry a per-image tone and some do not.")
        print("  Do not compare across that boundary.")
    elif kinds == {"TONED"}:
        print("  All files TONED. Black and white points are percentiles of")
        print("  EACH IMAGE'S OWN luminance, so each arm sets its own scale.")
        print("  Cross-arm absolute DN IS contaminated: a global shift is")
        print("  mixed into every row.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: tonecheck.py <tiff> [tiff ...]")
    main(sys.argv[1:])
