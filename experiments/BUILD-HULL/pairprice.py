"""The clamp's price, from a matched pair that differs ONLY in Hull.

`blend-render` is the only binary in the tree where `Hull::Unclamped` is
reachable, so a clamped/unclamped pair from it isolates the clamp exactly: one
build, one flag, same alignment, same everything else. That is the design the
failed S-vs-W build control forces -- the two strehl.exe builds differ by up to
3902 DN on a path containing no hull code at all, so no cross-build comparison
can price the clamp.

Two subjects, and the pairing matters as much as the numbers:

  flower-bud-alone-cpl  POTENCY CONTROL. Known to clip. If this reads ~0 the
                        instrument is not looking and the placebo below is
                        worthless -- a zero from a dead detector and a zero from
                        an inert clamp are the same glyph.
  coffee-bean           PLACEBO. ORCH measured 0.000% exact-zero px in the
                        delivered master. The claim under test is that the clamp
                        "cannot cost anything real"; here is where that is
                        cheapest to falsify.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import tifffile

BL = Path("bl")
SUBJECTS = [("fb", "flower-bud-alone-cpl", "POTENCY CONTROL (clips)"),
            ("cb", "coffee-bean", "PLACEBO (does not clip)")]


def load(p: Path) -> np.ndarray:
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p} is {a.dtype}, expected uint16"
    return a


def read_log(p: Path) -> str:
    """Decode a PowerShell `*>` log.

    PowerShell redirection writes UTF-16LE with a BOM on Windows. Decoding that
    as UTF-8 with errors="replace" yields garbage that still looks like text, so
    a present number reads as absent with no error raised -- which is exactly
    what this function was written to stop after it reported "NOT REPORTED" for
    a `hull clamp` line that was sitting in the file all along.
    """
    b = p.read_bytes()
    for bom, enc in ((b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16"), (b"\xef\xbb\xbf", "utf-8-sig")):
        if b.startswith(bom):
            return b.decode(enc, errors="replace")
    return b.decode("utf-8", errors="replace")


def self_report(tag: str) -> str:
    """What the merge says its own clamp did, in its own CFA-quad domain."""
    log = BL / f"{tag}-clamped.log"
    if not log.exists():
        return "no log"
    m = re.search(r"hull clamp\s+:\s*([0-9.%][0-9.%\s]*)", read_log(log))
    return m.group(1).strip() if m else "NOT REPORTED"


def determinism_null() -> None:
    """Same flags, twice. If two identical runs differ, the clamped/unclamped
    pair below is measuring run-to-run noise and not the clamp."""
    a, b = BL / "cb-clamped.tiff", BL / "cb-clamped-RERUN.tiff"
    print("  --- DETERMINISM NULL: same flags, two runs ---")
    if not b.exists():
        print("    SKIPPED -- no rerun present. The pair result is NOT commissioned.")
        return
    x, y = load(a).astype(np.int64), load(b).astype(np.int64)
    d = x - y
    n = int((d != 0).sum())
    print(f"    coffee-bean clamped vs clamped-RERUN : differing samples={n} "
          f"max|d|={int(np.abs(d).max())} DN")
    print("    identical => any difference in the pair below is the flag, not noise."
          if n == 0 else
          "    NOT IDENTICAL => the pipeline is non-deterministic and the pair is void.")


def main() -> int:
    print("=== the clamp's price: matched pairs, one build, one flag ===")
    print("  binary: ORCH-SHIP blend-render.exe, --camera-linear (never a tone curve)\n")

    print(f"  {'subject':<22} {'role':<26} {'hull clamp (module self-report, CFA domain)'}")
    for tag, name, role in SUBJECTS:
        print(f"  {name:<22} {role:<26} {self_report(tag)}")

    print("\n  --- what the clamp actually MOVED in the delivered pixels ---")
    determinism_null()
    print()
    print(f"  {'subject':<22} {'samples':>12} {'moved':>12} {'pct':>9} "
          f"{'max|d|':>8} {'mean|d| moved':>14} {'zeros unclamped':>16} {'zeros clamped':>14}")

    requested, scored, missing = len(SUBJECTS), [], []
    rows = {}
    for tag, name, _role in SUBJECTS:
        c, u = BL / f"{tag}-clamped.tiff", BL / f"{tag}-unclamped.tiff"
        if not (c.exists() and u.exists()):
            missing.append(name)
            print(f"  {name:<22} MISSING -- not scored (this is NOT a pass)")
            continue
        scored.append(name)
        ca, ua = load(c).astype(np.int64), load(u).astype(np.int64)
        assert ca.shape == ua.shape, f"{name}: shape mismatch {ca.shape} vs {ua.shape}"
        d = ca - ua
        moved = d != 0
        nm = int(moved.sum())
        rows[tag] = (nm, d.size, int(np.abs(d).max()) if nm else 0)
        print(f"  {name:<22} {d.size:>12} {nm:>12} {100.0 * nm / d.size:>8.4f}% "
              f"{(int(np.abs(d).max()) if nm else 0):>8} "
              f"{(np.abs(d[moved]).mean() if nm else 0.0):>14.2f} "
              f"{int((ua == 0).sum()):>16} {int((ca == 0).sum()):>14}")

    print(f"\n  subjects REQUESTED : {requested}")
    print(f"  subjects SCORED    : {len(scored)}  {scored}")
    print(f"  subjects MISSING   : {len(missing)}  {missing}")
    assert len(scored) + len(missing) == requested, "subject partition does not sum"

    print("\n  --- POTENCY vs PLACEBO ---")
    if "fb" in rows and "cb" in rows:
        fb, cb = rows["fb"], rows["cb"]
        fpc, cpc = 100.0 * fb[0] / fb[1], 100.0 * cb[0] / cb[1]
        print(f"    potency (flower-bud) : {fpc:.4f}% of samples moved, max {fb[2]} DN")
        print(f"    placebo (coffee-bean): {cpc:.4f}% of samples moved, max {cb[2]} DN")
        if fpc <= 0.0:
            print("    INSTRUMENT DEAD: the potency control did not move. The placebo")
            print("    result below proves nothing and must not be reported as inert.")
        else:
            print(f"    ratio                : {fpc / cpc:.1f}x more movement on the clipping subject"
                  if cpc > 0 else
                  "    ratio                : placebo EXACTLY inert while potency moved")
    else:
        print("    SKIPPED -- a subject is missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
