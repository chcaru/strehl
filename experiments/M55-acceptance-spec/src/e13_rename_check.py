"""M55b -- verify the mid-milestone rename of five corpus directories.

The owner renamed 131/133/134/135/136MSDCF to wrapped-text-1/-2 and bee-1/-2/-3
while this milestone was running.  This file does NOT take that mapping on
trust: it re-reads EXIF from the new directories and checks that each new name
carries a fingerprint that matches exactly one old entry in the committed
out/heldout.json, which was produced before the rename.

EXIF AND COUNTS ONLY.  Five of these six stacks are HELD OUT by this spec, so
this file decodes no pixel, merges nothing and scores nothing.  Reading a file
header is not measuring a stack.
"""
import os, sys, glob, json

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
ROOT = r"D:\personal\macro"

CLAIMED = {"131MSDCF": "wrapped-text-1", "133MSDCF": "wrapped-text-2",
           "134MSDCF": "bee-1", "135MSDCF": "bee-2", "136MSDCF": "bee-3"}
TAGS = ("EXIF ISOSpeedRatings", "EXIF ExposureTime", "EXIF FNumber",
        "EXIF LensModel", "Image Model", "EXIF DateTimeOriginal")


def read_stack(name):
    fs = sorted(glob.glob(os.path.join(ROOT, name, "*.ARW")))
    if not fs:
        return None
    import exifread
    got = []
    for f in (fs[0], fs[-1]):
        with open(f, "rb") as fh:
            t = exifread.process_file(fh, details=False)
        got.append({k: str(v) for k, v in t.items() if k in TAGS})
    return dict(n=len(fs), first=got[0], last=got[1])


def fingerprint(rec):
    """Key that must be unique across the five, using only fields the
    PRE-RENAME heldout.json also carries."""
    f, l = rec["first"], rec["last"]
    return (rec["n"],
            f.get("EXIF ISOSpeedRatings"), f.get("EXIF ExposureTime"),
            l.get("EXIF ISOSpeedRatings"), l.get("EXIF ExposureTime"),
            f.get("EXIF FNumber"), f.get("EXIF LensModel"))


def main():
    print("=" * 78)
    print("M55b -- rename verification (EXIF and counts only, no pixel decoded)")
    print("=" * 78)
    old = json.load(open(os.path.join(OUT, "heldout.json"), encoding="utf-8"))
    old_fp = {k: fingerprint(v) for k, v in old.items()}
    dup_old = len(set(old_fp.values())) != len(old_fp)
    print(f"   pre-rename fingerprints unique across {len(old_fp)} stacks: {not dup_old}")

    new = {}
    for nm in sorted(set(CLAIMED.values())) + ["coffee-bean"]:
        r = read_stack(nm)
        if r is None:
            print(f"   {nm:16s} MISSING")
        new[nm] = r
    new_fp = {k: fingerprint(v) for k, v in new.items() if v}
    print(f"   post-rename fingerprints unique across {len(new_fp)} stacks: "
          f"{len(set(new_fp.values())) == len(new_fp)}")

    print(f"\n   {'new name':16s} {'ARW':>5s} {'ISO':>6s} {'exp(1)':>9s} {'exp(n)':>9s} "
          f"{'matches old':14s} {'claimed':14s} agree")
    rows, agree_all = [], True
    for nm in sorted(new_fp):
        fp = new_fp[nm]
        hits = [o for o, f in old_fp.items() if f == fp]
        hit = hits[0] if len(hits) == 1 else ("AMBIGUOUS%s" % hits if hits else "NONE")
        claim = CLAIMED.get(hit, hit if nm == "coffee-bean" else "?")
        agree = (len(hits) == 1) and (CLAIMED.get(hits[0], hits[0]) == nm)
        agree_all = agree_all and agree
        print(f"   {nm:16s} {new[nm]['n']:5d} {fp[1]:>6s} {fp[2]:>9s} {fp[4]:>9s} "
              f"{str(hit):14s} {str(claim):14s} {'YES' if agree else 'NO'}")
        rows.append(dict(new=nm, n=new[nm]["n"], iso_first=fp[1], exp_first=fp[2],
                         exp_last=fp[4], matched_old=str(hit), agrees=bool(agree),
                         datetime_first=new[nm]["first"].get("EXIF DateTimeOriginal"),
                         datetime_last=new[nm]["last"].get("EXIF DateTimeOriginal")))

    print(f"\n   -> rename mapping independently confirmed for every stack: {agree_all}")

    # Subject grouping is NEW information created by the rename.
    groups = {}
    for nm in list(CLAIMED.values()) + ["coffee-bean"]:
        groups.setdefault(nm.rsplit("-", 1)[0] if nm[-1].isdigit() else nm, []).append(nm)
    print(f"\n   distinct SUBJECTS in the held-out set: {len(groups)}")
    for g, mem in sorted(groups.items()):
        isos = [new_fp[m][1] for m in mem if m in new_fp]
        print(f"      {g:16s} {len(mem)} stack(s): {', '.join(mem):40s} ISO {isos}")
    print("   B6 was written assuming 6 stacks meant 6 scenes.  It does not.")

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "e13_rename_check.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(rows=rows, agree_all=bool(agree_all),
                       subjects={g: m for g, m in groups.items()}), fh, indent=1)
    print("\n   wrote out/e13_rename_check.json")


if __name__ == "__main__":
    main()
