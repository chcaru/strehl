"""Present the HEAD baseline in the shape printcert4.py demands, without editing
V-GATHER's harness and without duplicating 4.9 GB.

WHY THIS SCRIPT EXISTS. `printcert.py:72` hardcodes

    SEAL_DIR = r"C:\\dev\\strehl-out\\acceptance\\SHIP-V4"

and `printcert4.py:171` hardcodes the filename suffix `--SHIP-V4.tiff`. There is
no environment override anywhere in experiments/V-GATHER -- I grepped for
`environ.get` and `getenv` across the whole directory and found none. So the
harness can only be pointed at other bytes by changing that one constant, which
is V-GATHER's line to change, not mine.

THE HAZARD, NAMED. Writing HEAD bytes into files called `--SHIP-V4.tiff` is
exactly the mislabelled-artifact failure `corpuscopy.py` opens by warning about,
and it is the failure `C:\\dev\\strehl-out\\PIN-V3\\strehl.exe` inflicted on this
campaign tonight -- a binary whose name says one commit and whose bytes are
another. Three defences, because the suffix is not negotiable:

  1. The DIRECTORY name states the commit: `HEAD-d2193a55-sealshape`. Nobody can
     reach these files without typing the real provenance.
  2. Every `.tiff.ok` sentinel carries the sha256 of the binary that ACTUALLY
     produced the bytes -- A058F737... , not SHIP-V4's 44C2F2CD... . The seal
     is the thing printcert reads, and it disagrees out loud with the filename.
  3. A README.txt in the directory says all of this in the first sentence.

WHY HARDLINKS. 26 x 189 MB is 4.9 GB and ten lanes share this disk. A hardlink
on the same volume is free and cannot drift from its source, which a copy can.
The link is to the DEF-2f858c62 arm, whose bytes were proved bit-identical to a
HEAD d2193a55 render by headcheck.py on three subjects across 296.8 M samples --
including highly-angled-ruler-mm-cpl, the one subject whose alignment REFUSES
and therefore the one most exposed to aa40cc78's +400 lines in align_cmd.rs.
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

ARM = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\arms\DEF-2f858c62")
DEST = Path(r"C:\dev\strehl-out\acceptance\HEAD-d2193a55-sealshape")
ARM_TAG = "DEF-2f858c62"
SEAL_TAG = "SHIP-V4"          # dictated by printcert4.py:171, not chosen

# sha256 of acceptance-pins\2f858c62\target\release\strehl.exe, the binary that
# rendered every byte here. Verified against the arm's own provenance files.
ARM_BINARY_SHA = ("A058F737DFE695F711DBACB077B118ED10A5B85C55"
                  "6FE888EE7F929F10397542")

README = """\
THESE ARE **HEAD d2193a55** MASTERS. THEY ARE NOT SHIP-V4.

The `--SHIP-V4.tiff` infix in every filename is a naming convention hardcoded at
printcert4.py:171 and printcert.py:72, which carry no environment override. It is
the only shape that harness will read. It says nothing about these bytes.

  bytes rendered by : acceptance-pins\\2f858c62\\target\\release\\strehl.exe
  binary sha256     : {sha}
  git commit        : 2f858c624f897c8dde140e06fe6b6cb8643454c8
  equivalent to     : HEAD d2193a55 -- proved bit-identical at default flags on
                      3 subjects / 296,808,192 samples by headcheck.py, max|d|=0,
                      including highly-angled-ruler-mm-cpl (alignment REFUSED),
                      the subject most exposed to aa40cc78's align_cmd.rs change
  flags             : --srgb --auto-exposure  (identical to the SHIP-V4 masters)
  the real SHIP-V4  : C:\\dev\\strehl-out\\acceptance\\SHIP-V4, binary sha256
                      44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490

Each .tiff.ok sentinel carries {sha16}..., the TRUE binary sha, which disagrees
with the filename on purpose. If you are reading a number produced from this
directory, it is a number about HEAD.

The .tiff files are HARDLINKS to {arm}.
Deleting them does not free space until the arm is deleted too.
"""


def main():
    tiffs = sorted(ARM.glob(f"*--{ARM_TAG}.tiff"))
    if not tiffs:
        raise SystemExit(f"no masters at {ARM}")
    DEST.mkdir(parents=True, exist_ok=True)

    linked = copied = 0
    for t in tiffs:
        subject = t.name[: -len(f"--{ARM_TAG}.tiff")]
        dst = DEST / f"{subject}--{SEAL_TAG}.tiff"
        if not dst.exists():
            # mklink /H is a hardlink: no bytes, no drift, same volume only.
            r = subprocess.run(["cmd", "/c", "mklink", "/H", str(dst), str(t)],
                               capture_output=True, text=True)
            if r.returncode != 0 or not dst.exists():
                raise SystemExit(f"hardlink failed for {subject}: "
                                 f"{(r.stderr or r.stdout).strip()}")
            linked += 1
        # The seal printcert.py:166 globs. It carries the binary sha, so the
        # seal contradicts the filename rather than corroborating it.
        (DEST / f"{subject}--{SEAL_TAG}.tiff.ok").write_text(
            ARM_BINARY_SHA + "\n", encoding="ascii")
        src_prov = ARM / f"{t.name}.provenance.txt"
        if src_prov.exists():
            (DEST / f"{subject}--{SEAL_TAG}.tiff.provenance.txt").write_text(
                src_prov.read_text(encoding="utf-8", errors="replace"),
                encoding="utf-8")
            copied += 1

    (DEST / "README.txt").write_text(
        README.format(sha=ARM_BINARY_SHA, sha16=ARM_BINARY_SHA[:16], arm=ARM),
        encoding="utf-8")

    n_tiff = len(list(DEST.glob(f"*--{SEAL_TAG}.tiff")))
    n_ok = len(list(DEST.glob(f"*--{SEAL_TAG}.tiff.ok")))
    n_prov = len(list(DEST.glob(f"*--{SEAL_TAG}.tiff.provenance.txt")))
    print(f"dest        : {DEST}")
    print(f"hardlinked  : {linked} new ({n_tiff} masters present)")
    print(f"seals       : {n_ok}")
    print(f"provenance  : {n_prov} ({copied} written this run)")

    # Cross-check the shape against the real seal dir the harness reads today,
    # because a mirror that is missing a file makes an axis examine fewer
    # subjects and report the shortfall as silence.
    real = Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
    want = sorted(p.name for p in real.glob(f"*--{SEAL_TAG}.tiff"))
    got = sorted(p.name for p in DEST.glob(f"*--{SEAL_TAG}.tiff"))
    missing = set(want) - set(got)
    extra = set(got) - set(want)
    print(f"\nshape vs real SEAL_DIR: want {len(want)}, got {len(got)}, "
          f"missing {len(missing)}, extra {len(extra)}")
    if missing or extra:
        print(f"  missing: {sorted(missing)}")
        print(f"  extra  : {sorted(extra)}")
        return 1

    # Prove the link really points at the arm's bytes, not at a stale copy.
    probe = got[0]
    a = (DEST / probe).stat()
    b = (ARM / probe.replace(f"--{SEAL_TAG}.tiff", f"--{ARM_TAG}.tiff")).stat()
    same_file = (a.st_size == b.st_size)
    h = hashlib.sha256((DEST / probe).read_bytes()[:1 << 20]).hexdigest()[:16]
    h2 = hashlib.sha256(
        (ARM / probe.replace(f"--{SEAL_TAG}.tiff",
                             f"--{ARM_TAG}.tiff")).read_bytes()[:1 << 20]
    ).hexdigest()[:16]
    print(f"link probe  : {probe}  size-match={same_file}  "
          f"first-MB sha {h} vs arm {h2}  {'OK' if h == h2 else 'MISMATCH'}")
    if h != h2:
        return 1

    print(f"\nREADY. V-GATHER need change exactly one line to score HEAD:")
    print(f"  printcert.py:72   SEAL_DIR = r\"{DEST}\"")
    print(f"Nothing else in the harness moves; the suffix and layout already match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
