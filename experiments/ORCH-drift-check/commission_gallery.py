"""Commission the gallery verifier's structural checks by making them fail.

verify_gallery.py grew three checks tonight -- capture-tag presence, div/section
nesting, and whether the page's stated retouch-vs-reshoot splits are actually
borne out by the rendered tags. All three printed a zero on their first run,
which is exactly what they would print if they were incapable of firing.

The nesting check in particular was added *because* a truncated <div> had just
sailed past the verifier. A check written in response to a specific failure
must be shown to catch that specific failure, or it is decoration.

Each sabotage is anchored on a unique full-line string and hard-errors if the
anchor is not found, so a sabotage that silently fails to apply cannot be read
as a check that passed. The real index.html is never modified: every arm runs
against a copy written alongside it (so relative asset paths still resolve) and
that copy is removed afterwards.
"""
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
VIEW = pathlib.Path(r"C:\dev\strehl-out\VIEW")
IDX = VIEW / "index.html"
TMP = VIEW / "_commission.html"
VERIFY = HERE / "verify_gallery.py"


def anchored(doc: str, needle: str, repl: str, label: str) -> str:
    """Replace `needle` exactly once, or refuse."""
    n = doc.count(needle)
    if n != 1:
        raise SystemExit(
            f"SABOTAGE ANCHOR FAILED [{label}]: found {n} occurrences of\n"
            f"  {needle!r}\nexpected exactly 1. Refusing to run a sabotage "
            f"that did not land -- it would look identical to a passing check.")
    return doc.replace(needle, repl, 1)


def run(path: pathlib.Path):
    p = subprocess.run([sys.executable, str(VERIFY), str(path)],
                       capture_output=True, text=True)
    return p.returncode, p.stdout


def drop_last_div(doc: str) -> str:
    """Remove the </div> that closes the 'Two tags per subject' note."""
    key = "reshoot-this. Hover a capture tag for the number behind it."
    i = doc.index(key)
    j = doc.index("</div>", i)
    return doc[:j] + doc[j + len("</div>"):]


def main() -> int:
    if not IDX.exists():
        print(f"REFUSE: {IDX} does not exist -- build the gallery first")
        return 1
    real_before = IDX.read_bytes()
    doc = IDX.read_text(encoding="utf-8")

    arms = []

    # Null arm: an untouched copy must still verify, or the harness is the bug.
    arms.append(("NULL (untouched copy)", doc, None))

    # 1. Structural truncation -- the failure that motivated the check.
    arms.append((
        "unclosed <div> in a note",
        drop_last_div(doc),
        "malformed div/section nesting",
    ))

    # 2. A card loses its capture tag. Anchored on a per-card detail string so
    #    the anchor is unique -- the bare g-good tag occurs 12 times, and the
    #    first attempt at this arm was correctly refused for that reason.
    strip = ('<span class="tag g-gap" title="BUILD-TRIAGE classified the whole '
             'frame. 8/24 blocks (5 far, 3 near)">reshoot: coverage gap</span>')
    arms.append((
        "a card stripped of its capture tag",
        anchored(doc, strip, "", "capture tag"),
        "cards missing a capture tag",
    ))

    # 3. A stated retouch/reshoot split silently becomes agreement.
    arms.append((
        "tweezers-cpl reshoot tag flipped to clean",
        anchored(doc, '<span class="tag g-gap" title="BUILD-TRIAGE classified '
                      'the whole frame. 6/24 blocks, all far">'
                      'reshoot: coverage gap</span>',
                 '<span class="tag g-good" title="x">capture: clean</span>',
                 "conflict split"),
        "stated retouch/reshoot splits not borne out by tags",
    ))

    caught = missed = 0
    null_ok = False
    print(f"{'arm':<44} {'rc':>3}  outcome")
    print("-" * 78)
    for label, text, expect in arms:
        TMP.write_text(text, encoding="utf-8")
        rc, out = run(TMP)
        if expect is None:
            null_ok = (rc == 0 and "GALLERY VERIFIED" in out)
            print(f"{label:<44} {rc:>3}  "
                  f"{'VERIFIED as expected' if null_ok else 'BROKEN HARNESS'}")
            continue
        line = [ln for ln in out.splitlines() if expect in ln]
        fired = bool(line) and not line[0].rstrip().endswith(" 0")
        refused = rc != 0 and "GALLERY NOT VERIFIED" in out
        if refused and fired:
            caught += 1
            print(f"{label:<44} {rc:>3}  CAUGHT  ({line[0].strip()})")
        else:
            missed += 1
            print(f"{label:<44} {rc:>3}  *** MISSED *** "
                  f"(refused={refused} fired={fired})")

    if TMP.exists():
        TMP.unlink()

    # The real page must be byte-identical to how we found it.
    untouched = IDX.read_bytes() == real_before

    print()
    print(f"sabotages planted : {caught + missed}")
    print(f"  caught          : {caught}")
    print(f"  missed          : {missed}")
    print(f"null arm verified : {null_ok}")
    print(f"real index.html untouched : {untouched}")
    ok = null_ok and missed == 0 and caught == 3 and untouched
    print()
    print("COMMISSIONED" if ok else "NOT COMMISSIONED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
