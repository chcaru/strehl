"""Registered negative controls for verify_s32.py.

Section 32's central claim is a NEGATIVE -- no render was short-bracketed --
and negatives are the easiest thing in this corpus to assert vacuously. So
two of these arms plant the very thing the section says is absent (a
`--limit` in a measurement script, and a binary-invoking script) and require
the verifier to notice. If it cannot, the section proves nothing.

Same rules as control_s31.py: unique single-line anchors, hard error if an
anchor does not land, backup to %TEMP% and restore from that copy rather than
`git checkout --`, exit codes read from returncode in Python, and one arm
expected GREEN so that "every arm red" cannot be confused with a verifier
that fails on any edit.
"""
import os
import pathlib
import shutil
import subprocess
import sys

SRC = pathlib.Path(__file__).resolve().parent
ROOT = SRC.parents[2]
DOC = ROOT / "docs" / "research" / "M87-occlusion.md"
DATA = SRC.parent / "data"
VERIFY = SRC / "verify_s32.py"
PLANT = SRC / "93-plant-control.py"
TMP = pathlib.Path(os.environ["TEMP"]) / "M87-s32-controls"

ARMS = [
    ("N1  aligned ISO in the 32.2 table", DOC,
     "| aligned (shipped default) | **0.06406** | **72.93%** |",
     "| aligned (shipped default) | **0.06416** | **72.93%** |", "RED"),
    ("N2  JSON operand: unaligned ISO", DATA / "51-zoomnull.json",
     '"before": 0.06878296931291605', '"before": 0.06578296931291605', "RED"),
    ("N3  JSON operand: aligned delta", DATA / "51-zoomnull.json",
     '"delta_pct": 72.93287068931788', '"delta_pct": 74.93287068931788',
     "RED"),
    ("N4  audit share decoupled from operands", DATA / "93-audit.json",
     '"align_share_of_halo_pct": 6.862844189363607',
     '"align_share_of_halo_pct": 6.962844189363607', "RED"),
    ("N5  31.1 loses its explicit gate", DOC,
     "gate           : 4.0  (resolved DEFAULT_GATE, `merge.rs:297`; recorded",
     "gate           : the shipped default (`merge.rs:297`; recorded", "RED"),
    ("N6  31.1 hides that the gate defaulted", DOC,
     "    --index-map ... --n-eff-map ...        # no --gate flag was passed",
     "    --index-map ... --n-eff-map ...", "RED"),
    ("N7  prose reworded, no figure touched", DOC,
     "I hold no claim that needs retaking on this account.",
     "No claim of mine needs retaking on this account.", "GREEN"),
]


def run_verifier():
    r = subprocess.run([sys.executable, str(VERIFY)], capture_output=True,
                       cwd=str(ROOT),
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")


def plant_arms():
    """Arms that add a FILE rather than edit one -- the two claims section
    32.1 rests on. A verifier that reads the recorded zero instead of
    re-counting from disk stays green through both of these."""
    out = []
    for name, text, want in (
        ("N8  a measurement script passes --limit",
         'CMD = ["strehl", "stack", "D:/x", "--limit", "40"]\n', "RED"),
        ("N9  a script invokes the binary",
         'import subprocess\nsubprocess.run([r"C:\\x\\strehl-m87.exe"])\n',
         "RED"),
    ):
        PLANT.write_text('"""control plant."""\n' + text, encoding="utf-8")
        rc, o = run_verifier()
        PLANT.unlink()
        got = "GREEN" if rc == 0 else "RED"
        first = next((l for l in o.splitlines() if "FAIL" in l), "").strip()
        out.append((name, want, got, got == want, first[:78]))
    return out


def main():
    code, out = run_verifier()
    if code != 0:
        print("BASELINE IS NOT GREEN -- controls are meaningless")
        print(out)
        return 1
    print(f"baseline GREEN: {out.strip().splitlines()[0]}\n")

    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)
    backups = {}
    for p in {p for _, p, _, _, _ in ARMS}:
        b = TMP / p.name
        shutil.copy2(p, b)
        backups[p] = b

    results, bad = [], 0
    try:
        for name, path, old, new, want in ARMS:
            src = backups[path].read_bytes().decode("utf-8")
            n = src.count(old)
            if n != 1:
                raise SystemExit(
                    f"MUTATION TARGET NOT FOUND: arm {name!r} anchor occurs "
                    f"{n} times in {path.name}, need exactly 1")
            path.write_bytes(src.replace(old, new).encode("utf-8"))
            rc, o = run_verifier()
            got = "GREEN" if rc == 0 else "RED"
            first = next((l for l in o.splitlines() if "FAIL" in l), "").strip()
            shutil.copy2(backups[path], path)
            ok = got == want
            bad += 0 if ok else 1
            results.append((name, want, got, ok, first[:78]))
        results.extend(plant_arms())
        bad += sum(0 if r[3] else 1 for r in results[len(ARMS):])
    finally:
        for p, b in backups.items():
            shutil.copy2(b, p)
        if PLANT.exists():
            PLANT.unlink()

    rc, _ = run_verifier()
    restored = "GREEN" if rc == 0 else "RED"
    print(f"{'arm':<42} {'want':<6} {'got':<6} ok  first failure")
    for name, want, got, ok, first in results:
        print(f"{name:<42} {want:<6} {got:<6} "
              f"{'yes' if ok else 'NO ':<3} {first}")
    print(f"\nrestored baseline: {restored}")
    if restored != "GREEN":
        print("RESTORE FAILED -- the tree is not as it was")
        bad += 1
    print(f"{len(results)} arms, {bad} disagreements")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
