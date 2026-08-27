"""Read the master's real bit depth from the TIFF header, without PIL.

PIL opened a 188.6 MiB SHIP-V2 master and handed back mode='RGB', dtype=uint8, max=255.
For 7032 x 4688 x 3, eight bits per sample is 94.3 MiB and sixteen is 188.6 MiB. The file
size says sixteen. If that is right, PIL has been silently truncating every master I have
measured tonight, and the truncation is invisible: what comes back is a perfectly
well-formed RGB array with no error, no warning, and no flag -- the same failure shape as
every other instrument that has caught me tonight.

The file size is circumstantial. This parses IFD tag 258 (BitsPerSample), 277
(SamplesPerPixel), 259 (Compression) and 262 (PhotometricInterpretation) out of the bytes
directly, so the answer comes from the file's own declaration rather than from arithmetic
on its length or from the library under suspicion.
"""
import pathlib
import struct
import sys

TAGS = {
    256: "ImageWidth", 257: "ImageLength", 258: "BitsPerSample",
    259: "Compression", 262: "Photometric", 277: "SamplesPerPixel",
    339: "SampleFormat", 284: "PlanarConfig", 296: "ResolutionUnit",
    282: "XResolution", 283: "YResolution", 305: "Software",
}
FMT = {1: ("B", 1), 2: ("c", 1), 3: ("H", 2), 4: ("I", 4), 5: ("II", 8),
       6: ("b", 1), 7: ("B", 1), 8: ("h", 2), 9: ("i", 4), 10: ("ii", 8),
       11: ("f", 4), 12: ("d", 8)}


def read_ifd(path):
    with open(path, "rb") as fh:
        head = fh.read(8)
        bo = head[:2]
        if bo == b"II":
            e = "<"
        elif bo == b"MM":
            e = ">"
        else:
            raise SystemExit(f"not a TIFF: magic {bo!r}")
        magic, = struct.unpack(e + "H", head[2:4])
        if magic == 43:
            raise SystemExit("BigTIFF; this parser handles classic TIFF only")
        off, = struct.unpack(e + "I", head[4:8])
        fh.seek(off)
        n, = struct.unpack(e + "H", fh.read(2))
        out = {}
        for _ in range(n):
            raw = fh.read(12)
            tag, typ, cnt = struct.unpack(e + "HHI", raw[:8])
            if typ not in FMT:
                continue
            code, size = FMT[typ]
            total = size * cnt
            if total <= 4:
                blob = raw[8:8 + total]
            else:
                ptr, = struct.unpack(e + "I", raw[8:12])
                cur = fh.tell()
                fh.seek(ptr)
                blob = fh.read(total)
                fh.seek(cur)
            if typ == 2:
                val = blob.split(b"\0")[0].decode("latin-1")
            elif typ in (5, 10):
                nums = struct.unpack(e + code[0] * (2 * cnt), blob)
                val = [f"{nums[i]}/{nums[i+1]}" for i in range(0, len(nums), 2)]
            else:
                val = list(struct.unpack(e + code * cnt, blob))
                if len(val) == 1:
                    val = val[0]
            out[tag] = val
        return out


def main(paths):
    bad = []
    for p in paths:
        p = pathlib.Path(p)
        ifd = read_ifd(p)
        w = ifd.get(256)
        h = ifd.get(257)
        bps = ifd.get(258)
        spp = ifd.get(277)
        comp = ifd.get(259)
        bits = bps if isinstance(bps, int) else (bps[0] if bps else None)
        nb = bits * (spp or 1) // 8 * (w or 0) * (h or 0)
        print(f"{p.name}")
        for t in sorted(ifd):
            if t in TAGS:
                print(f"    {TAGS[t]:20s} {ifd[t]}")
        print(f"    {'-> bytes if raw':20s} {nb:,} "
              f"(file is {p.stat().st_size:,}, compression={comp})")
        if bits and bits > 8:
            bad.append((p.name, bits))
        print()
    print(f"masters inspected            : {len(paths)}")
    print(f"declaring more than 8 bits   : {len(bad)}")
    print(f"declaring 8 bits             : {len(paths) - len(bad)}")
    if bad:
        print("\nPIL returned uint8 for these. Every magnitude measured through PIL on "
              "a master is a truncation, and it truncates without saying so.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
