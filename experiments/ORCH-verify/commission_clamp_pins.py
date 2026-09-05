"""Commission the 2.9.76 clamp pins added to v2954.py.

Two classes of arm, and the difference is stated in the output rather than
blurred:

  WIRING arms mutate a file I own (STATUS.md, ORCH-clamp-default-decision.md),
  re-run the real verifier, and prove the check fires end to end.

  PREDICATE arms do NOT touch the tree. `crates/strehl-cli/src/align_cmd.rs` and
  `crates/strehl-core/src/restore.rs` are shared source read by ~23 concurrent
  agents, and a sabotaged resampler constant could be picked up by someone
  else's `cargo build` and silently corrupt their measurement. So those checks
  are commissioned by evaluating the exact predicate string against known-good
  and known-bad inputs. That proves the predicate discriminates; it does not
  prove the wiring, and it is labelled accordingly.

Restores come from $TEMP copies and are SHA-verified. `git checkout --` is never
used.
"""
import hashlib
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
V2954 = ROOT / "experiments" / "ORCH-verify" / "v2954.py"
STATUS = ROOT / "docs" / "STATUS.md"
CLAMP = ROOT / "docs" / "research" / "ORCH-clamp-default-decision.md"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verifier():
    r = subprocess.run([sys.executable, str(V2954)],
                       capture_output=True, text=True, cwd=str(ROOT))
    return "GREEN" if r.returncode == 0 else "RED"


WIRING = [
    ("W1 scoreboard silently cashed", STATUS,
     "**The scoreboard is unchanged at `0 of 12`.** Nothing above is a pass.",
     "**The scoreboard is now `1 of 12`.** Nothing above is a pass.", "RED"),
    ("W2 N5 prohibition deleted", CLAMP,
     "> **A clamped shipping default is NOT a route to an M8 PASS while M1 is absent.**",
     "> A clamped shipping default is one route among several.", "RED"),
    ("W3 clamp decision quietly resolved", CLAMP,
     "**UNRESOLVED.** No arm has been read.",
     "**GO.** All arms read and passed.", "RED"),
    ("W4 (inert) unrelated prose edit", CLAMP,
     "## 1. The decision",
     "## 1. The decision under consideration", "GREEN"),
]

# (label, predicate as evaluated in v2954, good input, bad input)
PREDICATE = [
    ("P1 resampler default flipped",
     lambda s: 'pub const DEFAULT_RESAMPLER_NAME: &str = "catmull-rom";' in s,
     'pub const DEFAULT_RESAMPLER_NAME: &str = "catmull-rom";',
     'pub const DEFAULT_RESAMPLER_NAME: &str = "clamped-catmull-rom";'),
    ("P2 restoration silently allows clamp",
     lambda s: "!matches!(r, Resampler::ClampedCatmullRom)" in s,
     "    !matches!(r, Resampler::ClampedCatmullRom)\n}",
     "    true\n}"),
]


def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="v2976-commission-"))
    originals = {}
    for p in {STATUS, CLAMP}:
        b = tmp / p.name
        shutil.copy2(p, b)
        originals[p] = (b, sha(p))

    if verifier() != "GREEN":
        print("ABORT: baseline v2954 is not GREEN; commissioning is meaningless")
        return 2

    caught = missed = inert_ok = inert_bad = 0
    try:
        for label, path, needle, repl, expected in WIRING:
            txt = path.read_text(encoding="utf-8")
            n = txt.count(needle)
            if n != 1:
                raise SystemExit(
                    f"MUTATION TARGET NOT FOUND: {label!r} matched {n} times in "
                    f"{path.name}, expected exactly 1")
            path.write_text(txt.replace(needle, repl, 1), encoding="utf-8")
            got = verifier()
            ok = got == expected
            if expected == "RED":
                caught += ok
                missed += (not ok)
            else:
                inert_ok += ok
                inert_bad += (not ok)
            print(f"  [{'ok ' if ok else 'BAD'}] WIRING    {label}: {got}, expected {expected}")
            shutil.copy2(originals[path][0], path)
    finally:
        for p, (b, s) in originals.items():
            shutil.copy2(b, p)
            if sha(p) != s:
                print(f"  RESTORE FAILED for {p}")
                return 3
        shutil.rmtree(tmp, ignore_errors=True)

    pred_ok = 0
    for label, pred, good, bad in PREDICATE:
        good_green = pred(good)
        bad_red = not pred(bad)
        ok = good_green and bad_red
        pred_ok += ok
        print(f"  [{'ok ' if ok else 'BAD'}] PREDICATE {label}: "
              f"accepts good={good_green}, rejects bad={bad_red}")

    final = verifier()
    total = caught + missed + inert_ok + inert_bad
    print()
    print(f"wiring arms       {len(WIRING)}  caught {caught}  missed {missed}  "
          f"inert-green {inert_ok}  inert-red {inert_bad}  accounted {total}")
    print(f"predicate arms    {len(PREDICATE)}  discriminating {pred_ok}  "
          f"non-discriminating {len(PREDICATE) - pred_ok}")
    print("NOTE: predicate arms prove the test discriminates, NOT that it is wired.")
    print(f"restored baseline {final}")
    good = (missed == 0 and inert_bad == 0 and total == len(WIRING)
            and pred_ok == len(PREDICATE) and final == "GREEN")
    print("COMMISSIONED" if good else "NOT COMMISSIONED")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
