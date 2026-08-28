"""Clipping audit of this lane's ENTIRE evidence base, after ORCH's HEAD exposure regression.

ORCH measured that at HEAD `--srgb --auto-exposure` double-applies a tone
normalisation and blows 11 of 18 masters (up to 92.13% of pixels pinned at
65535). It asked every lane which of three cases it is in.

The point of this script is that the answer is MEASURED, not read off the
flags. A flag audit proves what was requested; a pixel audit proves what was
produced. Those differ whenever a flag silently stops doing what it says --
which is the exact class of defect ORCH just found, and the reason
`vn_shipfr.py` already refuses when `--limit` and the log disagree.

Three populations are audited:

  masters   the 26 re-rendered `--linear-srgb --demosaic` masters behind
            sections 1-8
  renders   the four HEAD-pin renders behind section 9.26, against the four
            old-pin renders of the same arms
  bundles   the cached arrays behind sections 9.24 and 9.25 -- the hull,
            sub-gate and dilution work

`kept` arrays are frame INDICES, not pixels, and are excluded by name rather
than by a max-value heuristic: an index array whose largest value happens to be
its own length would otherwise read as 100% "clipped".

Outcomes partition: blown + clean + unreadable sums to the number of files
found, so a file that could not be opened can never read as a clean one.

Never writes to D:. Reads only.
"""
import glob
import io
import json
import os

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\V-NEVERWORSE"
MASTERS = os.path.join(OUT, "masters")
HEADR = os.path.join(OUT, "dilute", "shipfr")
OLDR = os.path.join(OUT, "dilute", "shipfr-pin-9b05d0b7")
BUNDLES = [os.path.join(OUT, "bundle"), os.path.join(OUT, "gbundle")]

CEIL = 65535
BLOWN_PCT = 25.0          # ORCH's threshold
NOT_PIXELS = ("kept",)


def tiff_stat(p):
    a = np.asarray(tifffile.imread(p))
    if a.dtype != np.uint16:
        raise ValueError("%s is %s, expected uint16" % (p, a.dtype))
    return float((a >= CEIL).mean()) * 100.0, float(np.median(a))


def audit_tiffs(paths):
    rows, unreadable = [], []
    for p in paths:
        try:
            clip, med = tiff_stat(p)
        except Exception as e:                                  # noqa: BLE001
            unreadable.append(dict(file=os.path.basename(p), error=str(e)))
            continue
        rows.append(dict(file=os.path.basename(p), clip_pct=clip, median=med,
                         blown=clip > BLOWN_PCT))
    return rows, unreadable


def audit_bundles():
    rows, unreadable = [], []
    for d in BUNDLES:
        for npz in sorted(glob.glob(os.path.join(d, "*.npz"))):
            try:
                z = np.load(npz)
                worst, worst_key, mx = 0.0, None, 0.0
                for k in z.keys():
                    if k in NOT_PIXELS:
                        continue
                    a = z[k]
                    if a.dtype != np.uint16:
                        continue
                    frac = float((a >= CEIL).mean()) * 100.0
                    if frac >= worst:
                        worst, worst_key = frac, k
                    mx = max(mx, float(a.max()))
                rows.append(dict(file=os.path.basename(npz),
                                 dir=os.path.basename(d),
                                 worst_clip_pct=worst, worst_key=worst_key,
                                 max_value=mx, blown=worst > BLOWN_PCT))
            except Exception as e:                              # noqa: BLE001
                unreadable.append(dict(file=os.path.basename(npz),
                                       error=str(e)))
    return rows, unreadable


def commission():
    """Prove the audit can FAIL before its zero is believed.

    Three planted files with known truth:
      C1 a clean image  -> must read clean
      C2 a blown image (92% of pixels pinned at 65535, ORCH's observed rate)
         -> must read BLOWN
      C3 an unreadable file -> must count as unreadable, NOT as clean

    C3 is the one that matters. The whole point of partitioning is that a file
    the instrument could not open must never be absorbed into the clean count,
    and that is invisible unless something unopenable is actually planted.
    """
    import shutil
    import tempfile
    d = tempfile.mkdtemp(prefix="vn-clipcomm-")
    ok = bad = 0
    try:
        rng = np.random.default_rng(0)
        clean = rng.integers(0, 20000, size=(256, 256), dtype=np.uint16)
        tifffile.imwrite(os.path.join(d, "c1-clean.tiff"), clean)

        blown = clean.copy()
        n = blown.size
        flat = blown.reshape(-1)
        flat[:int(0.9203 * n)] = CEIL          # ORCH measured 92.03% on 109MSDCF
        tifffile.imwrite(os.path.join(d, "c2-blown.tiff"),
                         flat.reshape(blown.shape))

        io.open(os.path.join(d, "c3-corrupt.tiff"), "wb").write(b"not a tiff")

        rows, un = audit_tiffs(sorted(glob.glob(os.path.join(d, "*.tiff"))))
        by = {r["file"]: r for r in rows}

        for label, cond in (
            ("C1 a clean image reads clean",
             "c1-clean.tiff" in by and not by["c1-clean.tiff"]["blown"]),
            ("C2 a 92.03%-clipped image reads BLOWN",
             "c2-blown.tiff" in by and by["c2-blown.tiff"]["blown"]),
            ("C2 recovers the planted clip fraction to within 0.5%",
             "c2-blown.tiff" in by
             and abs(by["c2-blown.tiff"]["clip_pct"] - 92.03) < 0.5),
            ("C3 an unreadable file counts as unreadable, not clean",
             len(un) == 1 and un[0]["file"] == "c3-corrupt.tiff"
             and "c3-corrupt.tiff" not in by),
            ("outcomes partition: 2 readable + 1 unreadable = 3 planted",
             len(rows) + len(un) == 3),
        ):
            print("  %-58s %s" % (label, "PASS" if cond else "FAIL"))
            ok += bool(cond)
            bad += (not cond)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print("commission: %d ok, %d failed" % (ok, bad))
    return bad


def main():
    print("--- commissioning the audit before believing its zero ---")
    if commission():
        print("REFUSED: the audit failed its own commissioning")
        return 2
    print()

    res = {}
    m, mu = audit_tiffs(sorted(glob.glob(os.path.join(MASTERS, "*.tiff"))))
    res["masters"] = dict(rows=m, unreadable=mu)
    h, hu = audit_tiffs(sorted(glob.glob(os.path.join(HEADR, "*.tiff"))))
    o, ou = audit_tiffs(sorted(glob.glob(os.path.join(OLDR, "*.tiff"))))
    res["head_renders"] = dict(rows=h, unreadable=hu)
    res["old_renders"] = dict(rows=o, unreadable=ou)
    b, bu = audit_bundles()
    res["bundles"] = dict(rows=b, unreadable=bu)

    tot_blown = tot_clean = tot_unread = 0
    for name in ("masters", "head_renders", "old_renders", "bundles"):
        rows = res[name]["rows"]
        un = res[name]["unreadable"]
        blown = sum(1 for r in rows if r["blown"])
        tot_blown += blown
        tot_clean += len(rows) - blown
        tot_unread += len(un)
        key = "worst_clip_pct" if name == "bundles" else "clip_pct"
        worst = max([r[key] for r in rows] or [0.0])
        print("%-14s %3d files: %d blown, %d clean, %d unreadable "
              "(worst %.2f%%)"
              % (name, len(rows) + len(un), blown, len(rows) - blown,
                 len(un), worst))

    print("\nTOTAL %d blown, %d clean, %d unreadable -- %d files examined"
          % (tot_blown, tot_clean, tot_unread,
             tot_blown + tot_clean + tot_unread))

    # The claim this lane is making to ORCH, derived rather than asserted.
    hp = max([r["clip_pct"] for r in h] or [0.0])
    op = max([r["clip_pct"] for r in o] or [0.0])
    res["summary"] = dict(
        blown=tot_blown, clean=tot_clean, unreadable=tot_unread,
        worst_master=max([r["clip_pct"] for r in m] or [0.0]),
        worst_head_render=hp, worst_old_render=op,
        worst_bundle=max([r["worst_clip_pct"] for r in b] or [0.0]),
        head_median=[r["median"] for r in h],
        old_median=[r["median"] for r in o])
    if tot_unread:
        print("REFUSED: %d file(s) could not be read; an unexamined file is "
              "not a clean one" % tot_unread)
        return 2
    p = os.path.join(OUT, "dilute", "clipaudit.json")
    json.dump(res, io.open(p, "w", encoding="utf-8"), default=float, indent=1)
    print("wrote", p)
    return 1 if tot_blown else 0


if __name__ == "__main__":
    raise SystemExit(main())
