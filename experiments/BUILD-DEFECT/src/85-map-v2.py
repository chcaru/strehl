"""Upgrade the shipping defect map from format v1 to v2, payload untouched.

WHY THIS SCRIPT EXISTS AT ALL, WHICH IS ALSO THE FINDING.

`crates/strehl-core/src/defect_map.rs` bumped the sidecar format to VERSION 2
and made the loader REFUSE a v1 map. The only canonical map on disk,
`out/defect-map-ILCE-7CM2-photo.txt`, was written by 16-photo-map.py as v1.
So at HEAD the sensor defect correction could not be switched on AT ALL: any
attempt died with

    Error: loading the defect map ...defect-map-ILCE-7CM2-photo.txt
    Caused by:
        unsupported defect map version 1 (this build understands 2)

in 1.0 s, before a single frame was read. That is the correction the project
believes is built, wired, tested and merely switched off. It is switched off
and it was also unreachable. Nothing detected this because nothing had ever
run the two together: the unit tests build their maps inline at the current
VERSION (see the `{MAGIC} {VERSION}` fixtures in defect_map.rs), so they moved
with the bump and could not notice that the artifact on disk had not.

The general form, which is worth more than the instance: A TEST THAT
CONSTRUCTS ITS OWN INPUT AT THE CURRENT VERSION CANNOT DETECT THAT THE SHIPPING
INPUT IS AT AN OLDER ONE. The fixture and the code move together; the artifact
does not move with them. Only loading the real file finds it, and only a
preflight that runs before the render finds it in time to matter.

WHY UPGRADE RATHER THAN RE-DERIVE.

The honest first choice is to re-run 16-photo-map.py, which now emits v2. It
cannot run: it reads `out/15-stacks.npz`, the pooled residual over 12 subject
stacks, and that cache was deleted during the disk reclamation. Re-deriving it
means re-decoding 96 raw frames.

That is not the only reason, and not the main one. Re-deriving would rebuild
the map's CONTENTS -- component growth, the 400-draw local null, the p-values --
and every number in BUILD-DEFECT.md section 16 is quoted against the file that
exists. A regenerated map that differed in any digit would silently invalidate
that section, and a regenerated map that agreed would have proved nothing this
script does not prove more directly. What is actually needed is a header key,
so this script changes a header key and PROVES it changed nothing else:

  * every non-header line must be byte-identical, in order, to the v1 file;
  * the `hot N` and `dust N` counts must be unchanged and must still equal the
    number of `h ` and `d ` records that follow them;
  * the output must differ from the input in EXACTLY the lines this script
    means to add or replace, enumerated below and asserted by count.

If any of those fails the script writes nothing and exits non-zero. An upgrade
that half-applied would be worse than no upgrade, because the file would still
load.

THE COORDINATE SPACE IS THE WHOLE POINT OF v2, SO IT IS NOT GUESSED.

v2 exists because v1 did not record which raw array its coordinates index, and
a map applied at the wrong origin is displaced by the optical-black border with
no downstream symptom. defect_map.rs records what that cost once already: a
script read `raw_image` where the map had been measured on `raw_image_visible`,
and this sensor's dust came back as **+54.8%** -- a dark mote read as a bright
spot, caught only because the sign was absurd.

So `active` here is not the usual answer being assumed. It is read off the
provenance of the array these coordinates index:

  1. 16-photo-map.py builds the map from `out/15-stacks.npz`.
  2. 15-corner-commissioned.py line 182 writes that array with
     `q = quad_mean(raw.raw_image_visible, black)`.
  3. `raw_image_visible` IS the active area. CoordSpace::Active is documented
     as "what `rawpy.raw_image_visible` returns".
  4. Independently, the map's own `covered 7028 4688` is rawpy's visible width,
     not rawler's 7032-column buffer.

This script re-checks (4) mechanically and refuses if `covered` is not the
visible width, so the claim is not merely repeated in a comment.

That is evidence, not proof, and the difference matters. The measurement that
DISCRIMINATES is in 86-coords-control.py: render the same subject under
`coords active` and `coords full` and read the binary's own per-site verdicts.
If the two are indistinguishable, this script's choice is unfalsified rather
than confirmed, and the report must say so.

Usage:
    python experiments/BUILD-DEFECT/src/85-map-v2.py [--check]

`--check` verifies the file on disk is a well-formed v2 map and writes nothing.
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
MAP = OUT / "defect-map-ILCE-7CM2-photo.txt"

# The visible (active) width rawpy reports for this body. `covered` must equal
# this for the `coords active` claim to be self-consistent; see (4) above.
VISIBLE_W = 7028

# The provenance lines this upgrade ADDS to the map. Kept here as data so the
# diff assertion below can be stated as an exact count rather than a hand wave.
COORDS_COMMENT = [
    "# coords: ACTIVE -- these quads index rawpy's raw_image_visible, the",
    "# coords: array 15-corner-commissioned.py line 182 actually decoded",
    "# coords: (`quad_mean(raw.raw_image_visible, black)`). Not inferred from",
    "# coords: convention: a v1 map omitted this key, and applying a map at",
    "# coords: the wrong origin read this sensor's dust as +54.8% -- a dark",
    "# coords: mote as a bright spot -- caught only because the sign was",
    "# coords: absurd. `covered` being 7028 and not 7032 agrees independently.",
]


def log(m: str) -> None:
    print(m, flush=True)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_counts(lines: list[str]) -> dict[str, int]:
    """Declared vs actual record counts, as a partition that must agree.

    Returned as four numbers, not two, because "declared 618 and found 618" and
    "declared 0 and found 0" are different facts and a single equality test
    reports them identically.
    """
    got = {"hot_declared": 0, "hot_records": 0, "dust_declared": 0, "dust_records": 0}
    for ln in lines:
        if ln.startswith("hot "):
            got["hot_declared"] = int(ln.split()[1])
        elif ln.startswith("dust "):
            got["dust_declared"] = int(ln.split()[1])
        elif ln.startswith("h "):
            got["hot_records"] += 1
        elif ln.startswith("d "):
            got["dust_records"] += 1
    return got


def check(path: Path) -> int:
    """Verify the map on disk is loadable-shaped v2. Writes nothing."""
    lines = path.read_text(encoding="utf-8").splitlines()
    fails = []
    if not lines or lines[0] != "strehl-defect-map 2":
        fails.append(f"first line is {lines[0]!r}, expected 'strehl-defect-map 2'")
    coords = [ln for ln in lines if ln.startswith("coords ")]
    if len(coords) != 1:
        fails.append(f"{len(coords)} 'coords' key(s), expected exactly 1")
    elif coords[0] != "coords active":
        fails.append(f"coords is {coords[0]!r}, expected 'coords active'")
    covered = [ln for ln in lines if ln.startswith("covered ")]
    if len(covered) != 1 or int(covered[0].split()[1]) != VISIBLE_W:
        fails.append(f"covered is {covered!r}, expected width {VISIBLE_W}")
    c = parse_counts(lines)
    if c["hot_declared"] != c["hot_records"]:
        fails.append(f"hot declares {c['hot_declared']} but carries {c['hot_records']}")
    if c["dust_declared"] != c["dust_records"]:
        fails.append(f"dust declares {c['dust_declared']} but carries {c['dust_records']}")
    if lines[-1] != "end":
        fails.append(f"last line is {lines[-1]!r}, expected 'end'")

    log(f"--check {path.name}")
    log(f"  sha256        : {sha256(path)}")
    log(f"  lines         : {len(lines)}")
    log(f"  hot           : declared {c['hot_declared']}, records {c['hot_records']}")
    log(f"  dust          : declared {c['dust_declared']}, records {c['dust_records']}")
    log(f"  coords        : {coords[0] if len(coords) == 1 else '(MISSING/DUPLICATE)'}")
    for f in fails:
        log(f"  FAIL: {f}")
    log(f"  {len(fails)} failure(s) -> {'GREEN' if not fails else 'RED'}")
    return 1 if fails else 0


def main() -> int:
    if not MAP.exists():
        log(f"REFUSING: {MAP} does not exist")
        return 2
    if "--check" in sys.argv:
        return check(MAP)

    src = MAP.read_text(encoding="utf-8")
    lines = src.splitlines()

    if lines[0] == "strehl-defect-map 2":
        log("already v2; nothing to do (run --check to verify it)")
        return check(MAP)
    if lines[0] != "strehl-defect-map 1":
        log(f"REFUSING: first line is {lines[0]!r}, which is neither v1 nor v2")
        return 2
    if any(ln.startswith("coords ") for ln in lines):
        log("REFUSING: a v1 map already carries a 'coords' key; this is not the file this script was written for")
        return 2

    before = parse_counts(lines)

    # The one structural claim this script makes about the source, checked
    # rather than assumed: `covered` must be the visible width, or the
    # `coords active` conclusion does not follow and must not be written.
    covered = [ln for ln in lines if ln.startswith("covered ")]
    if len(covered) != 1 or int(covered[0].split()[1]) != VISIBLE_W:
        log(f"REFUSING: covered is {covered!r}; expected exactly one line of width {VISIBLE_W}.")
        log("  The 'coords active' claim rests partly on covered being rawpy's visible")
        log("  width. If it is not, the coordinate space is in doubt and guessing it is")
        log("  the +54.8% error this format version exists to prevent.")
        return 2

    # Build v2: bump the magic, insert `coords` after `covered`, and append the
    # provenance comment after the last `# geometry:` line so the header reads
    # in the order a human would expect.
    out: list[str] = []
    for ln in lines:
        if ln == "strehl-defect-map 1":
            out.append("strehl-defect-map 2")
            continue
        out.append(ln)
        if ln.startswith("covered "):
            out.append("coords active")
    last_geom = max(i for i, ln in enumerate(out) if ln.startswith("# geometry:"))
    out[last_geom + 1 : last_geom + 1] = COORDS_COMMENT

    # PROVE THE PAYLOAD IS UNTOUCHED.
    #
    # Header lines are the ones this script is allowed to move. Everything else
    # -- the `h`/`d` records and the counts that declare them -- must survive in
    # the same order, byte for byte. Comparing the filtered sequences catches a
    # dropped, duplicated or reordered record, which a count alone would not.
    def payload(ls: list[str]) -> list[str]:
        return [ln for ln in ls if ln.startswith(("h ", "d ", "hot ", "dust ")) or ln == "end"]

    p_before, p_after = payload(lines), payload(out)
    if p_before != p_after:
        n = sum(1 for a, b in zip(p_before, p_after) if a != b)
        log(f"REFUSING: payload changed -- {len(p_before)} -> {len(p_after)} lines, {n} differing")
        return 2

    after = parse_counts(out)
    if before != after:
        log(f"REFUSING: counts changed {before} -> {after}")
        return 2

    # The diff must be exactly what was intended: 1 line replaced (the magic),
    # 1 + len(COORDS_COMMENT) lines added, 0 removed.
    added = len(out) - len(lines)
    want_added = 1 + len(COORDS_COMMENT)
    if added != want_added:
        log(f"REFUSING: added {added} lines, expected exactly {want_added}")
        return 2

    bak = OUT / f"defect-map-ILCE-7CM2-photo.v1-superseded-{time.strftime('%Y%m%dT%H%M%S')}.txt"
    shutil.copy2(MAP, bak)
    MAP.write_text("\n".join(out) + "\n", encoding="utf-8")

    log(f"upgraded {MAP.name}: v1 -> v2")
    log(f"  v1 kept at   : {bak.name}  (sha256 {sha256(bak)})")
    log(f"  lines        : {len(lines)} -> {len(out)}  (+{added}: 1 coords key + {len(COORDS_COMMENT)} provenance)")
    log(f"  payload      : {len(p_before)} records, byte-identical, order preserved")
    log(f"  hot          : declared {after['hot_declared']}, records {after['hot_records']}")
    log(f"  dust         : declared {after['dust_declared']}, records {after['dust_records']}")
    log(f"  new sha256   : {sha256(MAP)}")
    return check(MAP)


if __name__ == "__main__":
    raise SystemExit(main())
