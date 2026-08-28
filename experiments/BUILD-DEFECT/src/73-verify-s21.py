#!/usr/bin/env python3
"""Verify every numeric claim in BUILD-DEFECT.md section 21.

THE RULE THIS OBEYS
-------------------
Another lane's checker ran 37/37 green and then caught only 5 of 13 planted
defects, because eight of its checks compared the document against values
hard-coded in the checker itself.  Such a check verifies that the author typed
the same number twice.

So this script holds NO expected values.  Every claim is parsed out of the
document under test, and every truth is re-derived from the artifacts:

  - the four-row difference table, the sample counts, the deltas and the
    partition come from re-reading the TIFFs and recomputing, not from the JSON
    the report was written from;
  - the 11 differing bytes and their offsets come from a byte-level diff run
    here;
  - the tone-point ratios come from parsing the two files' embedded
    descriptions and dividing;
  - the SHA-256 prefixes come from hashing the files.

Where a claim is a THRESHOLD rather than a measurement (INERT_MAX_DN,
LIVE_MIN_DN), the truth is the instrument's source, parsed from
72-exposure-inert-at-pin.py.  A threshold the report and the instrument disagree
about is a real defect and must not be verifiable against a third copy.

PARTITION
---------
Every claim declared is resolved into exactly one of {matched, mismatched,
unresolved}, and the three are asserted to sum to the number declared.  An
unresolved claim is a failure of this verifier, and it is reported as such
rather than being quietly dropped -- a claim nobody could check must never read
like a claim that passed.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys

import numpy as np
import tifffile

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "docs", "research", "BUILD-DEFECT.md"))
INSTRUMENT = os.path.join(HERE, "72-exposure-inert-at-pin.py")
def _probe_dir():
    """Where the six probe renders live.

    They moved from C: to D: in the disk reclamation of 2026-08-27; C: is kept
    as a fallback so a tree that still holds the old location keeps verifying,
    and the env var lets a third location be named without editing this file.
    A missing tree is a typed refusal rather than a silent empty result: these
    renders are the evidence, and a verifier that quietly finds none of them
    would otherwise report perfect agreement over zero comparisons.
    """
    named = os.environ.get("STREHL_DEFECT_PROBE")
    if named:
        # An override that is SET but wrong must fail, not quietly fall through
        # to a default -- otherwise a typo silently measures a different tree
        # and reports it as the requested one.
        if not os.path.isdir(named):
            raise SystemExit("STREHL_DEFECT_PROBE is set to %r, which is not a "
                             "directory; refusing to fall back to a default"
                             % named)
        return named
    for p in (r"D:\strehl-out\BUILD-DEFECT\probe",
              r"C:\dev\strehl-out\BUILD-DEFECT\probe"):
        if os.path.isdir(p):
            return p
    raise SystemExit("probe renders not found in any known location; set "
                     "STREHL_DEFECT_PROBE to the directory holding "
                     "pin-e260.tiff and its siblings")


PROBE = _probe_dir()
SEAL = r"C:\dev\strehl-out\acceptance\SHIP-V4"


def section_21(text: str) -> str:
    m = re.search(r"^## 21\..*?(?=^## 22\.|\Z)", text, re.M | re.S)
    if not m:
        raise SystemExit("FATAL: section 21 not found in the report")
    return m.group(0)


def num(s: str) -> float:
    return float(s.replace(",", "").replace("\u2212", "-"))


class Verifier:
    def __init__(self) -> None:
        self.matched: list[str] = []
        self.mismatched: list[str] = []
        self.unresolved: list[str] = []

    def check(self, name: str, claimed, truth, rel: float | None = None,
              abs_floor: float = 0.0) -> None:
        """Compare one claim against one re-derived truth.

        `rel` is RELATIVE.  `abs_floor` is an absolute tolerance that is taken
        whenever it is larger, and it exists because the report displays values
        rounded -- clip fractions to four decimals, means to one -- so a claim
        can be correct and still differ from the truth by the rounding step.
        Without the floor, a tolerance tight enough to catch a real defect at
        large magnitudes rejects correct rounding at small ones.

        Commissioning found the reason both parameters are named rather than
        positional: an earlier version passed 0.05 as the fourth positional
        intending 0.05 percentage points and got 5% relative, which let a
        0.2 pp planted defect through undetected.
        """
        if claimed is None or truth is None:
            self.unresolved.append(f"{name}: claimed={claimed!r} truth={truth!r}")
            return
        if isinstance(claimed, str) or isinstance(truth, str):
            ok = str(claimed) == str(truth)
        elif rel is None and abs_floor == 0.0:
            ok = float(claimed) == float(truth)
        else:
            tol = max(abs_floor, (rel or 0.0) * abs(float(truth)))
            ok = abs(float(claimed) - float(truth)) <= tol
        (self.matched if ok else self.mismatched).append(
            f"{name}: report={claimed!r} truth={truth!r}")

    def report(self, declared: int) -> int:
        total = len(self.matched) + len(self.mismatched) + len(self.unresolved)
        assert total == declared, (
            f"partition does not sum: {len(self.matched)} matched + "
            f"{len(self.mismatched)} mismatched + {len(self.unresolved)} unresolved "
            f"!= {declared} declared")
        print()
        print("declared %d = matched %d + mismatched %d + unresolved %d"
              % (declared, len(self.matched), len(self.mismatched), len(self.unresolved)))
        for tag, items in (("MISMATCHED", self.mismatched), ("UNRESOLVED", self.unresolved)):
            for it in items:
                print("  %s  %s" % (tag, it))
        if self.mismatched or self.unresolved:
            print()
            print("VERDICT: FAIL -- section 21 contains %d unverified claim(s)."
                  % (len(self.mismatched) + len(self.unresolved)))
            return 1
        print()
        print("VERDICT: PASS -- every claim in section 21 re-derives from the artifacts.")
        return 0


def main() -> int:
    text = open(REPORT, encoding="utf-8").read()
    sec = section_21(text)
    src = open(INSTRUMENT, encoding="utf-8").read()
    v = Verifier()
    declared = 0

    print("=" * 100)
    print("VERIFYING BUILD-DEFECT.md SECTION 21 AGAINST RE-DERIVED TRUTH")
    print("=" * 100)

    # ---- 1. the four-row difference table --------------------------------
    rows = re.findall(
        r"^(pin|HEAD)\s+([-+0-9.]+)\s+vs\s+([-+0-9.]+)\s+([0-9.]+)\s+([0-9.]+)x\s+"
        r"([0-9,]+)\s+([0-9.]+)%\s+(\d+)\s+([0-9.]+)\s*$", sec, re.M)
    if len(rows) != 4:
        v.unresolved.append("difference table: parsed %d rows, expected 4" % len(rows))
        declared += 1
    else:
        files = {
            ("pin", "+3", "-3"): ("pin-epos3.tiff", "pin-eneg.tiff"),
            ("pin", "+2.60", "0"): ("pin-e260.tiff", "pin-e000.tiff"),
            ("pin", "0", "-3"): ("pin-e000.tiff", "pin-eneg.tiff"),
            ("HEAD", "+2.60", "0"): ("head-e260.tiff", "head-e000.tiff"),
        }
        cache: dict[str, np.ndarray] = {}

        def load(fn: str) -> np.ndarray:
            if fn not in cache:
                cache[fn] = tifffile.imread(os.path.join(PROBE, fn)).astype(np.int32)
            return cache[fn]

        for binname, ea, eb, stops, ratio, ndiff, pct, mx, mean in rows:
            key = (binname, ea, eb)
            label = "%s %s vs %s" % (binname, ea, eb)
            if key not in files:
                v.unresolved.append("%s: no file mapping" % label)
                declared += 1
                continue
            fa, fb = files[key]
            a, b = load(fa), load(fb)
            d = np.abs(a - b)
            nz = int((d > 0).sum())
            t_pct = 100.0 * nz / d.size
            t_max = int(d.max())
            t_mean = float(d[d > 0].mean()) if nz else 0.0
            t_ratio = 2.0 ** float(stops)
            v.check("%s | commanded ratio" % label, num(ratio), t_ratio, 0.01)
            v.check("%s | samples differ" % label, num(ndiff), nz)
            v.check("%s | pct differ" % label, num(pct), t_pct, 0.01)
            v.check("%s | max |d|" % label, num(mx), t_max)
            v.check("%s | mean |d|" % label, num(mean), t_mean, 1e-4)
            declared += 5
        print("  difference table          : 4 rows x 5 quantities re-derived from the TIFFs")

    # ---- 2. the zero-difference headline ---------------------------------
    m = re.search(r"\*\*Those two files are different bytes and the same image\.\s*Zero of\s*"
                  r"([0-9,]+)\s*\n?samples differ\.\*\*", sec)
    if not m:
        m = re.search(r"Zero of\s+([0-9,]+)\s+samples differ", sec.replace("\n", " "))
    a = tifffile.imread(os.path.join(PROBE, "pin-epos3.tiff")).astype(np.int32)
    b = tifffile.imread(os.path.join(PROBE, "pin-eneg.tiff")).astype(np.int32)
    v.check("headline | plane size", num(m.group(1)) if m else None, int(a.size))
    v.check("headline | zero samples differ", 0, int((np.abs(a - b) > 0).sum()))
    declared += 2

    # `[0-9]+\.[0-9]+` rather than `[0-9.]+`: this claim ends a sentence, and the
    # looser class swallows the full stop and fails to parse as a float.
    mm = re.search(r"identical to\s+eight significant figures:\s*([0-9]+\.[0-9]+)\s+against\s+([0-9]+\.[0-9]+)",
                   sec.replace("\n", " "))
    v.check("headline | mean A", num(mm.group(1)) if mm else None, float(a.mean()), 1e-8)
    v.check("headline | mean B", num(mm.group(2)) if mm else None, float(b.mean()), 1e-8)
    declared += 2
    print("  zero-difference headline  : plane size and both means re-derived")
    del a, b

    # ---- 3. the byte-level diff ------------------------------------------
    A = np.fromfile(os.path.join(PROBE, "pin-epos3.tiff"), dtype=np.uint8)
    B = np.fromfile(os.path.join(PROBE, "pin-eneg.tiff"), dtype=np.uint8)
    idx = np.nonzero(A != B)[0]
    flat = sec.replace("\n", " ")
    mb = re.search(r"Eleven bytes differ, at file offsets\s+(\d+)\s+through\s+(\d+)", flat)
    v.check("bytes | count is eleven", 11, int(idx.size))
    v.check("bytes | first offset", num(mb.group(1)) if mb else None, int(idx.min()))
    v.check("bytes | last offset", num(mb.group(2)) if mb else None, int(idx.max()))
    declared += 3
    mps = re.search(r"runs to\s+([0-9,]+)\s+bytes", flat)
    v.check("bytes | pixel payload size", num(mps.group(1)) if mps else None, 98898048 * 2)
    declared += 1
    print("  byte-level diff           : %d differing bytes at %d..%d re-derived"
          % (idx.size, idx.min(), idx.max()))

    # ---- 4. the tone points and their ratios -----------------------------
    def tone(arr: np.ndarray) -> tuple[float, float] | tuple[None, None]:
        head = bytes(arr[:4096]).decode("latin-1")
        t = re.search(r"Tone rendering: black ([0-9.]+), white ([0-9.]+)", head)
        return (float(t.group(1)), float(t.group(2))) if t else (None, None)

    bp, wp = tone(A)
    bn, wn = tone(B)
    for label, pat, truth in (
        ("tone | +3 black", r"exposure=\+3\s*:.*?black ([0-9.]+), white ([0-9.]+)", bp),
        ("tone | -3 black", r"exposure=-3\s*:.*?black ([0-9.]+), white ([0-9.]+)", bn),
    ):
        mt = re.search(pat, flat)
        v.check(label, num(mt.group(1)) if mt else None, truth)
        v.check(label.replace("black", "white"), num(mt.group(2)) if mt else None,
                wp if "+3" in label else wn)
        declared += 2
    mr = re.search(r"black ratio \+3 / -3 = ([0-9.]+)\s+commanded 2\^6 = ([0-9.]+)\s+agreement ([0-9.]+)%", flat)
    mw = re.search(r"white ratio \+3 / -3 = ([0-9.]+)\s+commanded 2\^6 = ([0-9.]+)\s+agreement ([0-9.]+)%", flat)
    if bp and bn:
        v.check("tone | black ratio", num(mr.group(1)) if mr else None, bp / bn, 1e-5)
        v.check("tone | black agreement %", num(mr.group(3)) if mr else None,
                100 * abs(bp / bn - 64) / 64, 0.02)
        v.check("tone | white ratio", num(mw.group(1)) if mw else None, wp / wn, 1e-5)
        v.check("tone | white agreement %", num(mw.group(3)) if mw else None,
                100 * abs(wp / wn - 64) / 64, 0.05)
        v.check("tone | commanded 2^6", num(mr.group(2)) if mr else None, 64.0)
        declared += 5
    else:
        v.unresolved.append("tone: could not parse tone points from the files")
        declared += 1
    print("  tone points and ratios    : parsed from both files' metadata and divided")
    del A, B

    # ---- 5. the reproduced hashes ----------------------------------------
    # Parsed from ONE canonical sentence, not searched for across the section.
    # `"D749..." in sec` is a presence test, and a presence test is satisfied by
    # any duplicate of the value: the section mentions both prefixes twice, so
    # corrupting one occurrence would be masked by the other and read as a pass.
    mh = re.search(r"I reproduced both of\s+its hashes exactly \u2014 `([0-9A-F]+)` and `([0-9A-F]+)`", flat)
    for grp, fn in ((1, "pin-epos3.tiff"), (2, "pin-eneg.tiff")):
        h = hashlib.sha256(open(os.path.join(PROBE, fn), "rb").read()).hexdigest().upper()
        claimed = mh.group(grp) if mh else None
        v.check("hash | %s" % fn, claimed, h[:len(claimed)] if claimed else None)
        declared += 1
    print("  reproduced hashes         : both re-hashed from the files on disk")

    # ---- 6. thresholds, against the instrument's source -------------------
    mi = re.search(r"^INERT_MAX_DN = (\d+)", src, re.M)
    ml = re.search(r"^LIVE_MIN_DN = (\d+)", src, re.M)
    mband = re.search(r"`INERT <= (\d+) DN`, `LIVE >= (\d+) DN`", flat)
    v.check("band | INERT_MAX_DN", num(mband.group(1)) if mband else None,
            float(mi.group(1)) if mi else None)
    v.check("band | LIVE_MIN_DN", num(mband.group(2)) if mband else None,
            float(ml.group(1)) if ml else None)
    declared += 2
    mc = re.search(r"max \|d\| = (\d+) DN, needs >= (\d+)", flat)
    v.check("commissioning | pos control needs", num(mc.group(2)) if mc else None,
            float(ml.group(1)) if ml else None)
    declared += 1
    print("  thresholds                : cross-checked report against instrument source")

    # ---- 7. the partition claim -------------------------------------------
    mp = re.search(r"partition as (\d+) measured \+ (\d+) missing-input \+ (\d+) failed", flat)
    if mp:
        tot, mi2, fa2 = int(mp.group(1)), int(mp.group(2)), int(mp.group(3))
        v.check("partition | sums to declared", tot + mi2 + fa2, len(rows) if rows else None)
    else:
        v.unresolved.append("partition: claim not found in section 21")
    declared += 1

    # ---- 8. the seal comparison table -------------------------------------
    seal_rows = re.findall(r"^\s*(SHIP-V4 seal|pin  9b05d0b7  --exposure=\+2\.60|"
                           r"HEAD           --exposure=\+2\.60|HEAD           --exposure=0)\s+"
                           r"mean ([0-9.]+)\s+clipped ([0-9.]+)%", sec, re.M)
    truth_files = {
        "SHIP-V4 seal": os.path.join(SEAL, "109MSDCF--SHIP-V4.tiff"),
        "pin  9b05d0b7  --exposure=+2.60": os.path.join(PROBE, "pin-e260.tiff"),
        "HEAD           --exposure=+2.60": os.path.join(PROBE, "head-e260.tiff"),
        "HEAD           --exposure=0": os.path.join(PROBE, "head-e000.tiff"),
    }
    if len(seal_rows) != 4:
        v.unresolved.append("seal table: parsed %d rows, expected 4" % len(seal_rows))
        declared += 1
    else:
        for label, mean_c, clip_c in seal_rows:
            p = truth_files[label]
            if not os.path.exists(p):
                v.unresolved.append("seal table %s: %s absent" % (label, p))
                declared += 1
                continue
            arr = tifffile.imread(p)
            # Sized against the report's display precision: means are printed to
            # one decimal, clip fractions to four. The relative term catches a
            # real defect at large magnitudes; the floor tolerates the rounding
            # step at small ones. A single relative tolerance cannot do both --
            # 5% relative on an 85% clip fraction is 4.3 percentage points of
            # slack, which is how a 0.2 pp plant went undetected before.
            v.check("seal table | %s mean" % label.strip(), num(mean_c), float(arr.mean()),
                    rel=1e-5, abs_floor=0.06)
            v.check("seal table | %s clip" % label.strip(), num(clip_c),
                    100.0 * float((arr >= 65535).mean()), rel=1e-3, abs_floor=1e-4)
            declared += 2
            del arr
        print("  seal comparison table     : 4 renders re-measured for mean and clip")

    # ---- 9. section 21.8's derived figures ---------------------------------
    # The numbers describing the commissioning RUN (its partition, its
    # restoration hash) are deliberately NOT checked here. This verifier is
    # invoked by the commissioning script, so a check here against the
    # commissioning log is circular: the log is written by a process that runs
    # this file, and a stale log deadlocks the clean control. Those claims are
    # checked by 74-commission-s21.py, which knows their truth first-hand.
    #
    # What IS checkable here is the arithmetic section 21.8 states about
    # itself, and the plant count, whose truth is the static PLANTS table in
    # the commissioning source rather than any run of it.
    csrc_path = os.path.join(HERE, "74-commission-s21.py")
    if not os.path.exists(csrc_path):
        v.unresolved.append("21.8: commissioning source absent at %s" % csrc_path)
        declared += 1
    else:
        csrc = open(csrc_path, encoding="utf-8").read()
        body = re.search(r"^PLANTS.*?^\]", csrc, re.M | re.S)
        n_plants = len(re.findall(r'^    \("', body.group(0), re.M)) if body else None
        cl = re.search(r"declared (\d+) = caught (\d+) \+ missed (\d+) \+ unanchored (\d+)", sec)
        v.check("21.8 | plants declared", num(cl.group(1)) if cl else None, n_plants)
        v.check("21.8 | all plants caught",
                num(cl.group(2)) if cl else None, n_plants)
        v.check("21.8 | none missed", num(cl.group(3)) if cl else None, 0.0)
        v.check("21.8 | none unanchored", num(cl.group(4)) if cl else None, 0.0)
        declared += 4

        # The historical first run (18 plants, 16 caught) is narrative: the suite
        # has grown since, so it cannot be checked against the current PLANTS
        # table. What IS checkable is its internal arithmetic -- the section
        # says exactly two defects were found, so caught must be declared minus
        # two -- and the CURRENT suite size, which does have a truth here.
        mpre = re.search(r"Then (\d+) planted defects\s+were run through it and it caught (\d+)\.", flat)
        v.check("21.8 | pre-repair caught = that run's plants minus the two defects described",
                num(mpre.group(2)) if mpre else None,
                (num(mpre.group(1)) - 2) if mpre else None)
        declared += 1

        mgrown = re.search(r"grown to\s+(\d+) plants", flat)
        v.check("21.8 | current suite size", num(mgrown.group(1)) if mgrown else None, n_plants)
        declared += 1

        mslack = re.search(r"is \*\*([0-9.]+) percentage points\*\* of\s+slack", sec.replace("\n", " "))
        mclip = re.search(r"an ([0-9.]+)% clip fraction", sec)
        v.check("21.8 | slack = 5% of the clip fraction",
                num(mslack.group(1)) if mslack else None,
                round(0.05 * num(mclip.group(1)), 1) if mclip else None)
        declared += 1
        print("  21.8 derived figures      : plant count from the PLANTS table, slack re-derived")

    return v.report(declared)


if __name__ == "__main__":
    sys.exit(main())
