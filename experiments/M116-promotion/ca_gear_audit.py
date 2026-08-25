"""M116-promotion -- which of the owner's stacks were shot on the CA profile's
optical path?

`optics.rs` at the pinned SHA carries exactly one profile,
`a7c2-fe100gm-2xtc-x4cpl`, and its docstring says it "was measured through a
2x teleconverter" on one complete path. The product parses no camera identity
at all, so it will happily apply that profile to a stack shot on different
glass. Confirming the path from the files' own EXIF is therefore a
precondition of the arm, not a nicety.

Reads only. `D:\` is read-only and nothing here writes to it.

Run: python ca_gear_audit.py
"""

import json
import subprocess
import sys
from pathlib import Path

LIB = Path(r"D:\personal\macro")
OUT = Path(r"C:\dev\strehl-out\M116\ca")

# What the profile key asserts about the path, in EXIF terms.
WANT_BODY = "ILCE-7CM2"        # A7C II
WANT_LENS_SUBSTR = "100"       # FE 100 GM, seen through a 2x TC
TAGS = ["-Model", "-LensModel", "-LensID", "-FocalLength",
        "-FNumber", "-ExposureTime", "-ISO", "-DateTimeOriginal"]


def first_raw(d: Path):
    for ext in ("*.ARW", "*.arw"):
        for p in sorted(d.glob(ext)):
            return p
    return None


def exif(p: Path) -> dict:
    r = subprocess.run(["exiftool", "-j", "-n", *TAGS, str(p)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return {}
    try:
        return json.loads(r.stdout)[0]
    except Exception:
        return {}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for d in sorted(LIB.iterdir()):
        if not d.is_dir():
            continue
        p = first_raw(d)
        if p is None:
            rows.append({"subject": d.name, "frames": 0, "note": "no ARW"})
            continue
        n = len(list(d.glob("*.ARW"))) + len(list(d.glob("*.arw")))
        e = exif(p)
        body = str(e.get("Model", ""))
        lens = str(e.get("LensModel") or e.get("LensID") or "")
        fl = e.get("FocalLength")
        ok_body = body == WANT_BODY
        ok_lens = WANT_LENS_SUBSTR in lens or (
            isinstance(fl, (int, float)) and abs(float(fl) - 200.0) < 1.0)
        rows.append({
            "subject": d.name, "frames": n, "sample": p.name,
            "body": body, "lens": lens, "focal_mm": fl,
            "f": e.get("FNumber"), "iso": e.get("ISO"),
            "shot": e.get("DateTimeOriginal"),
            "body_ok": ok_body, "lens_ok": ok_lens,
            "profile_applicable": bool(ok_body and ok_lens),
        })

    (OUT / "gear-audit.json").write_text(json.dumps(rows, indent=2),
                                         encoding="utf-8")
    w = max(len(r["subject"]) for r in rows)
    print(f"{'subject':<{w}}  {'n':>4}  {'body':<12} {'lens':<28} "
          f"{'fl':>6}  applicable")
    for r in rows:
        if r.get("frames", 0) == 0:
            print(f"{r['subject']:<{w}}  {'-':>4}  {r.get('note','')}")
            continue
        fl = r["focal_mm"]
        fls = f"{fl:.0f}" if isinstance(fl, (int, float)) else "?"
        mark = "YES" if r["profile_applicable"] else "no"
        print(f"{r['subject']:<{w}}  {r['frames']:>4}  {r['body']:<12} "
              f"{r['lens'][:28]:<28} {fls:>6}  {mark}")

    ok = [r["subject"] for r in rows if r.get("profile_applicable")]
    print(f"\n{len(ok)} subject(s) confirmed on the profile's optical path:")
    for s in ok:
        print(f"  {s}")
    print(f"\nwrote {OUT / 'gear-audit.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
