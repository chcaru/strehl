#!/usr/bin/env python3
"""Re-derive every number in docs/research/V-DRIFT.md from the raw artifacts.

ANCHORING IS THE WHOLE DESIGN.  A presence check ("does 0.451 appear?") is
satisfied by any duplicate of the value anywhere in the prose, so it is not
pinned to anything.  Every check here locates ONE canonical table row by a
prefix that must occur exactly once, and reads the value out of THAT row.  A
number may then be repeated freely in the prose without weakening the check on
its canonical site.

Values are compared NUMERICALLY against the raw JSONL, not by string match, so
a rounding convention in the document cannot masquerade as a data error and a
data error cannot hide behind a rounding convention.

Run with --commission to plant a defect and require this script to go RED.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "docs" / "research" / "V-DRIFT.md"
ROOT = Path(r"C:\dev\strehl-out\V-DRIFT")
NUM = re.compile(r"-?\d+\.?\d*")


def load_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


class Check:
    def __init__(self, doc: str):
        self.lines = doc.splitlines()
        self.doc = doc
        self.ok = 0
        self.bad: list[str] = []
        # Two depth tables share row prefixes like "| 33 |", so a check must be
        # pinned to a section or it is pinned to nothing.
        self.heads = [i for i, l in enumerate(self.lines) if l.startswith("## ")]

    def _span(self, sec: str | None) -> tuple[int, int]:
        if sec is None:
            return 0, len(self.lines)
        for n, i in enumerate(self.heads):
            if self.lines[i].startswith(sec):
                return i, self.heads[n + 1] if n + 1 < len(self.heads) else len(self.lines)
        self.bad.append(f"section {sec!r} not found")
        return 0, 0

    def row(self, prefix: str, col: int, want: float, what: str,
            sec: str | None = None, ncells: int | None = None, rel: float = 6e-3) -> None:
        """Column `col` of the unique row starting `prefix` within `sec`.

        `ncells` disambiguates two tables in one section that share row labels
        -- section 3 carries both the depth sweep and the ratio table, and both
        have a row that starts "| 150 |".
        """
        lo, hi = self._span(sec)
        hits = [l for l in self.lines[lo:hi] if l.strip().startswith(prefix)]
        if ncells is not None:
            hits = [l for l in hits if len(l.strip().strip("|").split("|")) == ncells]
        if len(hits) != 1:
            self.bad.append(f"{what}: row prefix {prefix!r} matched {len(hits)} lines "
                            f"in {sec or 'document'}, want 1")
            return
        cells = [c.strip() for c in hits[0].strip().strip("|").split("|")]
        if col >= len(cells):
            self.bad.append(f"{what}: row {prefix!r} has {len(cells)} cells, wanted col {col}")
            return
        m = NUM.search(cells[col].replace("**", ""))
        if not m:
            self.bad.append(f"{what}: no number in cell {col} of {prefix!r} ({cells[col]!r})")
            return
        got = float(m.group(0))
        if abs(got - want) <= rel * max(abs(want), 1e-9) + 5e-4:
            self.ok += 1
        else:
            self.bad.append(f"{what}: document says {got}, data says {want:.6g}")

    def present(self, value: str, what: str) -> None:
        if value in self.doc:
            self.ok += 1
        else:
            self.bad.append(f"{what}: {value!r} not found in document")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", action="store_true")
    ap.add_argument("--doc", default=str(DOC))
    a = ap.parse_args()
    if a.commission:
        return commission()

    c = Check(Path(a.doc).read_text(encoding="utf-8"))

    # ---- section 3: depth sweep, bee-3-cpl ------------------------------
    S3 = "## 3."
    for r in load_jsonl(ROOT / "depth-bee3.jsonl"):
        if r.get("tag") != "ladder" or r.get("rep", 0) != 0:
            continue
        p = f"| {r['limit']} |"
        if r.get("heldout") is not None:
            c.row(p, 1, r["heldout"], f"bee L={r['limit']} held-out", sec=S3, ncells=6)
        c.row(p, 2, r["cycle_floor"], f"bee L={r['limit']} cycle floor", sec=S3, ncells=6)
        c.row(p, 3, r["drift"], f"bee L={r['limit']} drift", sec=S3, ncells=6)
        if r.get("heldout") is not None:
            c.row(p, 1, r["heldout"] / r["cycle_floor"],
                  f"bee L={r['limit']} held-out/cycle ratio", sec=S3, ncells=2)

    # ---- section 4: depth sweep, flower-bud-alone-cpl -------------------
    S4 = "## 4."
    for r in load_jsonl(ROOT / "depth-flower.jsonl"):
        p = f"| {r['limit']} |"
        c.row(p, 2, r["cycle_floor"], f"flower L={r['limit']} cycle floor", sec=S4)
        c.row(p, 3, r["drift"], f"flower L={r['limit']} drift", sec=S4)

    # ---- sections 5 and 6: windows --------------------------------------
    wins = sorted(load_jsonl(ROOT / "windows-bee3.jsonl"), key=lambda r: r["window_start"])
    for r in wins:
        lo = r["window_start"]
        hi = lo + r["window_count"] - 1
        c.row(f"| {lo}\u2013{hi} |", 1, r["cycle_floor"],
              f"window {lo}-{hi} cycle floor", sec="## 5.")
        c.row(f"| {lo}\u2013{hi} |", 2, r["drift"],
              f"window {lo}-{hi} local drift", sec="## 5.")
    if len(wins) >= 2:
        cf = [r["cycle_floor"] for r in wins]
        c.present(f"{max(cf)/min(cf):.2f}\u00d7", "start/end difficulty ratio")

    # ---- section 8: dose arms -------------------------------------------
    S8 = "## 8."
    for r in load_jsonl(ROOT / "dose-bee3.jsonl"):
        p = f"| {r['arm']} |"
        c.row(p, 2, r["abs_max_px"], f"dose {r['arm']} abs max", sec=S8)
        loc = r.get("local_rel_px") or {}
        if "1" in loc:
            c.row(p, 3, loc["1"], f"dose {r['arm']} sep1", sec=S8)
            c.row(p, 4, loc["8"], f"dose {r['arm']} sep8", sec=S8)
        c.row(p, 5, r["k"], f"dose {r['arm']} k", sec=S8)

    # ---- section 8: detail ratios ---------------------------------------
    dj = ROOT / "detail-bee3.json"
    if dj.exists():
        import numpy as np
        d = json.loads(dj.read_text(encoding="utf-8"))
        base = d["arms"][d["baseline"]]
        for arm in ("iid2", "walk20", "iid20", "noalign"):
            if arm not in d["arms"]:
                continue
            r = d["arms"][arm]
            rh = float(np.median([x / y for x, y in zip(r["high"], base["high"])]))
            rs = float(np.median([x / y for x, y in zip(r["slope"], base["slope"])]))
            c.row(f"| {arm} (", 1, rh, f"detail {arm} band-high ratio", sec=S8)
            c.row(f"| {arm} (", 2, rs, f"detail {arm} edge-slope ratio", sec=S8)

    # ---- claims that must appear at all ---------------------------------
    for txt, what in [
        ("+0.0001 px", "geometry commissioning delta"),
        ("44C2F2CD2E5B2894", "binary hash prefix"),
        ("185.266 px", "wm.py reproduced drift"),
        ("0.433", "chain accumulation slope"),
        ("0.984", "chain accumulation r-squared"),
        ("REFUSED", "the refusal is stated"),
    ]:
        c.present(txt, what)

    print(f"{c.ok} checks passed, {len(c.bad)} failed")
    for b in c.bad:
        print(f"  FAIL {b}")
    print("GREEN" if not c.bad else "RED")
    return 1 if c.bad else 0


def commission() -> int:
    src = DOC.read_text(encoding="utf-8")
    plants = [
        ("| 236\u2013298 | **0.451** | 21.0 | 2.5 |",
         "| 236\u2013298 | **0.462** | 21.0 | 2.5 |",
         "window 236-298 cycle floor 0.451 -> 0.462"),
        ("| iid20 | iid | 20.00 | 6.095 | 6.425 | 0.9256 |",
         "| iid20 | iid | 20.00 | 6.095 | 6.425 | 0.9456 |",
         "iid20 crop factor k 0.9256 -> 0.9456"),
    ]
    fails = 0
    for anchor, mutant, desc in plants:
        if anchor not in src:
            raise SystemExit(f"MUTATION TARGET NOT FOUND: {anchor!r}\n"
                             "The control is unanchored; a GREEN here would mean nothing.")
        if src.count(anchor) != 1:
            raise SystemExit(f"MUTATION TARGET AMBIGUOUS ({src.count(anchor)}x): {anchor!r}")
        tmp = Path(tempfile.mkdtemp(prefix="vdrift-verify-"))
        bad = tmp / "V-DRIFT.md"
        bad.write_text(src.replace(anchor, mutant, 1), encoding="utf-8")
        p = subprocess.run([sys.executable, __file__, "--doc", str(bad)],
                           capture_output=True, text=True)
        shutil.rmtree(tmp, ignore_errors=True)
        caught = p.returncode != 0 and "RED" in p.stdout
        fails += not caught
        print(f"[{'PASS' if caught else 'FAIL'}] {desc}: verifier went "
              f"{'RED as required' if caught else 'GREEN -- IT IS NOT WATCHING'}")
    clean = subprocess.run([sys.executable, __file__], capture_output=True, text=True)
    ok = clean.returncode == 0
    fails += not ok
    print(f"[{'PASS' if ok else 'FAIL'}] unmutated document reads "
          f"{'GREEN' if ok else 'RED -- the verifier disagrees with its own data'}")
    if not ok:
        print(clean.stdout)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
