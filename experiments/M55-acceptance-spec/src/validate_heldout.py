"""M55b -- validate the SUBSTRATE of the held-out set, and nothing else.

The six stacks named in spec_v1.HELD_OUT must never be scored by the author of
the spec: a held-out set the spec's author has measured is not held out.  This
file therefore reads EXIF and frame counts ONLY.  It does not decode a pixel,
does not merge, and does not evaluate any metric.
"""
import os, sys, glob, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spec_v1 as S

ROOT = r"D:\personal\macro"


def main():
    import exifread
    out = {}
    print("=" * 78)
    print("M55b -- held-out substrate validation (EXIF and counts only)")
    print("=" * 78)
    print(f"   {'stack':14s} {'ARW':>5s} {'ISO':>7s} {'exposure':>10s} {'f':>7s}  {'lens':30s}")
    ok = True
    for s in S.HELD_OUT:
        fs = sorted(glob.glob(os.path.join(ROOT, s, "*.ARW")))
        if not fs:
            print(f"   {s:14s}  MISSING")
            ok = False
            continue
        tags = {}
        for f in (fs[0], fs[-1]):
            with open(f, "rb") as fh:
                t = exifread.process_file(fh, details=False)
            tags[f] = {k: str(v) for k, v in t.items()
                       if k in ("EXIF ISOSpeedRatings", "EXIF ExposureTime",
                                "EXIF FNumber", "EXIF LensModel", "Image Model")}
        a = tags[fs[0]]
        enough = len(fs) >= S.B6_FRAMES
        ok = ok and enough
        print(f"   {s:14s} {len(fs):5d} {a.get('EXIF ISOSpeedRatings','?'):>7s} "
              f"{a.get('EXIF ExposureTime','?'):>10s} {a.get('EXIF FNumber','?'):>7s}  "
              f"{a.get('EXIF LensModel','?')[:30]:30s}"
              f"{'' if enough else '   <-- FEWER THAN 64 FRAMES'}")
        out[s] = dict(n=len(fs), first=a, last=tags[fs[-1]], enough=bool(enough))
    print(f"\n   ROIs, by rule, identical for every stack: {S.roi_rule()}")
    print(f"   frames used per stack: first {S.B6_FRAMES}; split: {S.B6_SPLIT}")
    print(f"   -> substrate {'VALID' if ok else 'NOT VALID'}")
    print("   No pixel of any held-out stack was decoded by this file.")
    with open(os.path.join(os.path.dirname(HERE), "out", "heldout.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
