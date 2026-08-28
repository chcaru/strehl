"""V-H2H2: conclusion-reversal audit of griddiag.py, through its shipped entry point.

ORCH, after six lanes each found their own verifier blind to a reversed
conclusion: "If you have not run a conclusion-reversal audit on your own harness
through its shipped entry point, run it before you report again." Three lessons
came with it and this suite implements all three:

  1. An inert plant and a dead instrument give the identical green.
     -> commission the PASS/FAIL CHANNEL: clean -> 0, planted -> non-zero.
  2. Commissioning sensitivity is not commissioning specificity.
     -> plant NOISE too (innocuous prose) and require it be REJECTED.
  3. Commission DELETION as well as reversal.
     -> deletion arms, because removing a finding is cheaper than misstating it.

griddiag.py is run as a subprocess -- `python griddiag.py` -- so this measures
the artefact that actually ships, not an importable inner function that ships
alongside it.

SAFETY: this working tree is shared by ~12 concurrent lanes and one of these
files (merge_cmd.rs) belongs to BUILD-CROP. Nothing is mutated in place. The
three sources are copied to a scratch tree and griddiag is pointed at the copy
via STREHL_GRIDDIAG_ROOT. The real tree is opened read-only, and never with
`git checkout --`.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REAL = Path(r"C:\dev\blog\death-of-software\projects\strehl")
GRIDDIAG = REAL / "experiments" / "V-H2H2-MOTTLE" / "griddiag.py"

MERGE = "crates/strehl-cli/src/merge_cmd.rs"
ALIGN = "crates/strehl-cli/src/align_cmd.rs"
PYR = "crates/strehl-core/src/pyramid.rs"
SOURCES = [MERGE, ALIGN, PYR]


def sub(rel, old, new):
    """Anchored single replacement. A mutation that does not land is an inert
    plant, and an inert plant is indistinguishable from a dead instrument -- so
    a miss is a hard error, never a silent no-op."""
    def apply(root):
        p = root / rel
        t = p.read_text(encoding="utf-8", errors="replace")
        n = t.count(old)
        if n != 1:
            raise SystemExit(
                f"MUTATION TARGET NOT FOUND ({n} occurrences) in {rel}:\n  {old!r}\n"
                "The plant would have been inert and the arm meaningless.")
        p.write_text(t.replace(old, new, 1), encoding="utf-8")
    return apply


def append(rel, text):
    def apply(root):
        p = root / rel
        p.write_text(p.read_text(encoding="utf-8", errors="replace") + text,
                     encoding="utf-8")
    return apply


# name, expectation, mutation. RED = griddiag must exit non-zero.
ARMS = [
    ("CLEAN                      no mutation at all",
     "GREEN", None),

    # -- REVERSAL: the code flips while the prose asserting it stays true-looking
    # The bare expression occurs TWICE (merged_luma[...] at :5701 contains it as
    # a substring), and the guard above refused the ambiguous plant on the first
    # run. Anchored on the full line, exactly as griddiag anchors it.
    ("REVERSE_LUMA               decision var G1+G2 -> R+B, doc comment left intact",
     "RED", sub(MERGE,
                "\n        luma[i] = 0.5 * (planes[1][i] + planes[2][i]);\n",
                "\n        luma[i] = 0.5 * (planes[0][i] + planes[3][i]);\n")),
    ("REVERSE_PLANES             BAND_PLANES 4 -> 3",
     "RED", sub(MERGE, "const BAND_PLANES: usize = 4;",
                "const BAND_PLANES: usize = 3;")),
    ("REVERSE_ESCAPE             full-res planes escape via the return type",
     "RED", None),  # installed specially below; the anchor spans a signature

    # -- DELETION: the finding is removed rather than misstated
    ("DELETE_GREENLUMA           drop the green-luma doc line",
     "RED", sub(PYR, "/// made on green luma only", "/// (removed)")),
    ("DELETE_BANNER              drop the tool's own one-decision-per-quad admission",
     "RED", sub(MERGE,
                "decision per quad. Interpolated -- do not measure resolution on it.",
                "decision per quad.")),

    # -- SPECIFICITY: plant NOISE and require it be rejected
    ("PROSE_INNOCUOUS            harmless trailing comment, no claim touched",
     "GREEN", append(PYR, "\n// housekeeping: nothing in this line bears on any claim\n")),
    ("PROSE_DECOY                duplicate the green-luma anchor elsewhere",
     "RED", append(PYR, "\n// see also: /// made on green luma only\n")),
]


def reverse_escape(root):
    """Change ONLY warp_frame_in_place_fullres's return type so the full-res
    planes can leave the function. `) -> Result<f64> {` is NOT unique in this
    file, so anchor on the unique fn name and take the first return arrow after
    it."""
    p = root / ALIGN
    t = p.read_text(encoding="utf-8", errors="replace")
    key = "pub fn warp_frame_in_place_fullres("
    i = t.find(key)
    if i < 0:
        raise SystemExit("MUTATION TARGET NOT FOUND: warp_frame_in_place_fullres")
    j = t.find(") -> Result<f64> {", i)
    if j < 0:
        raise SystemExit("MUTATION TARGET NOT FOUND: return arrow after the fn")
    p.write_text(t[:j] + ") -> Result<(f64, Vec<f32>)> {" + t[j + len(") -> Result<f64> {"):],
                 encoding="utf-8")


ARMS = [(n, e, reverse_escape if n.startswith("REVERSE_ESCAPE") else m)
        for n, e, m in ARMS]


def run(root):
    env = dict(os.environ, STREHL_GRIDDIAG_ROOT=str(root))
    r = subprocess.run([sys.executable, str(GRIDDIAG)],
                       capture_output=True, text=True, env=env)
    return r.returncode, (r.stdout + r.stderr)


print("=" * 78)
print("CONCLUSION-REVERSAL AUDIT -- griddiag.py via `python griddiag.py`")
print("=" * 78)
print(f"{'arm':<62}{'want':<7}{'got':<7}")

results = []
for name, expect, mutate in ARMS:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for rel in SOURCES:
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REAL / rel, dst)
        if mutate is not None:
            mutate(root)
        rc, out = run(root)
    got = "GREEN" if rc == 0 else "RED"
    ok = (got == expect)
    results.append((name, expect, got, ok, out))
    print(f"{name:<62}{expect:<7}{got:<7}{'ok' if ok else '<<< WRONG'}")

caught = sum(1 for _, e, _, ok, _ in results if e == "RED" and ok)
red = sum(1 for _, e, _, _, _ in results if e == "RED")
green_ok = sum(1 for _, e, _, ok, _ in results if e == "GREEN" and ok)
green = sum(1 for _, e, _, _, _ in results if e == "GREEN")

print()
print(f"SENSITIVITY  {caught}/{red} planted defects caught")
print(f"SPECIFICITY  {green_ok}/{green} clean/innocuous inputs correctly passed")
print(f"PARTITION    {len(results)} arms = {sum(1 for r in results if r[3])} correct"
      f" + {sum(1 for r in results if not r[3])} wrong")

for name, expect, got, ok, out in results:
    if not ok:
        print(f"\n--- {name}: wanted {expect}, got {got} ---")
        print("\n".join(out.strip().splitlines()[-12:]))

if caught != red or green_ok != green:
    sys.exit("AUDIT FAILED -- this verifier cannot be trusted to report")
print("\nAUDIT PASSED")
