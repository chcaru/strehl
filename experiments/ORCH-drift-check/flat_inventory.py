"""Inventory the owner's flat-field campaign before briefing a milestone on it.

Rule 40: do not brief from memory. This is the search run in the same session.
Reads EXIF only; writes nothing to D:\\.
"""
import io
import os
import subprocess
import sys
from collections import Counter

ROOT = r"D:\personal\macro\flat-fields"


def exif(path):
    import exifread
    with open(path, "rb") as f:
        t = exifread.process_file(f, details=False, stop_tag="MakerNote")
    g = lambda k: str(t[k]) if k in t else "?"
    return {
        "iso": g("EXIF ISOSpeedRatings"),
        "fnum": g("EXIF FNumber"),
        "exp": g("EXIF ExposureTime"),
        "focal": g("EXIF FocalLength"),
        "lens": g("EXIF LensModel"),
        "when": g("EXIF DateTimeOriginal"),
    }


def main():
    for sub in sorted(os.listdir(ROOT)):
        d = os.path.join(ROOT, sub)
        if not os.path.isdir(d):
            continue
        files = sorted(f for f in os.listdir(d) if f.lower().endswith(".arw"))
        print(f"\n=== {sub}  ({len(files)} frames) ===")
        # sample: every Nth so a ladder shows up rather than just the head
        step = max(1, len(files) // 24)
        rows = []
        for name in files[::step]:
            try:
                e = exif(os.path.join(d, name))
            except Exception as ex:
                print(f"  {name}: EXIF FAILED {ex}")
                continue
            rows.append((name, e))
        for name, e in rows:
            print(f"  {name}  ISO {e['iso']:>6}  f/{e['fnum']:>6}  {e['exp']:>10} s  "
                  f"{e['focal']:>5} mm  {e['when']}")
        if rows:
            for k in ("iso", "fnum", "exp", "focal", "lens"):
                c = Counter(e[k] for _, e in rows)
                print(f"  distinct {k}: {dict(c)}")


if __name__ == "__main__":
    main()
