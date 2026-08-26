"""Commission the stated-count check in verify_gallery.py.

The check passed on its first run. A check that has never been shown to fail is
indistinguishable from a check that cannot fail -- this project has shipped two
of those tonight. So plant defects it MUST catch and require RED on each.

Every plant is anchored on a unique full-line-ish string and hard-errors if the
anchor does not land exactly once. A sabotage that silently fails to apply
produces a green that looks like a pass, which is the failure mode this file
exists to prevent.

The real index.html is never modified: each arm is written to a temp copy and
verify_gallery.py is pointed at it via argv[1].
"""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
IDX = pathlib.Path(r"C:\dev\strehl-out\VIEW\index.html")
VERIFY = HERE / "verify_gallery.py"


def anchored(doc: str, old: str, new: str, label: str) -> str:
    n = doc.count(old)
    if n != 1:
        raise SystemExit(
            f"MUTATION TARGET NOT FOUND for {label!r}: anchor matched {n} times, "
            f"expected exactly 1. Fix the anchor; do not weaken the plant."
        )
    return doc.replace(old, new, 1)


def run(doc: str, label: str, expect_red: bool) -> bool:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="commission-")) / "index.html"
    tmp.write_text(doc, encoding="utf-8")
    p = subprocess.run(
        [sys.executable, str(VERIFY), str(tmp)],
        capture_output=True, text=True,
    )
    red = p.returncode != 0
    hit = "count mismatch" in p.stdout
    if expect_red:
        ok = red and hit
        detail = "" if ok else "  (did NOT fire on the count check)"
        print(f"  {'CAUGHT ' if ok else 'MISSED '} {label}{detail}")
    else:
        ok = not red
        print(f"  {'CLEAN  ' if ok else 'FALSE+ '} {label}")
    shutil.rmtree(tmp.parent, ignore_errors=True)
    return ok


def main() -> int:
    if not IDX.exists():
        raise SystemExit(f"REFUSE: {IDX} does not exist")
    base = IDX.read_text(encoding="utf-8")

    print("commissioning the stated-count check")
    print()
    print("null arm (unmodified page must stay green):")
    results = [run(base, "unmodified index.html", expect_red=False)]
    print()
    print("planted arms (each must go RED on the count check):")

    # 1. the stated word no longer matches the list beside it
    results.append(run(
        anchored(base,
                 "Twenty-four subjects have been judged print-worthy by eye at",
                 "Twenty-five subjects have been judged print-worthy by eye at",
                 "count word"),
        "stated count says Twenty-five, list still has 24", expect_red=True))

    # 2. a subject is dropped from the list while the count stays
    results.append(run(
        anchored(base,
                 "<code>flower-bud-alone-cpl</code> and <code>wrapped-text-2</code>",
                 "<code>wrapped-text-2</code>", "dropped subject"),
        "a subject removed from the list, count unchanged", expect_red=True))

    # 3. the page understates how many subjects were opened
    results.append(run(
        anchored(base,
                 "<b>All 26 subjects have now been opened at 1:1",
                 "<b>All 24 subjects have now been opened at 1:1",
                 "opened count"),
        "stated 'opened' count disagrees with the cards rendered",
        expect_red=True))

    # 4. a duplicate in the list inflates it to match a wrong count
    results.append(run(
        anchored(base,
                 "<code>coffee-bubbles</code>, <code>couch-fibers-cpl</code>,",
                 "<code>coffee-bubbles</code>, <code>foam</code>, "
                 "<code>couch-fibers-cpl</code>,", "duplicate subject"),
        "list padded with a duplicate to reach the stated count",
        expect_red=True))

    # 5. the subjects that did NOT pass stop being named. This is the check
    #    that replaced the old opened==print-worthy equality: the difference
    #    between the two counts must be discharged by naming every subject it
    #    covers, so a subject cannot be quietly dropped from the pass list.
    results.append(run(
        anchored(base,
                 "not called print-worthy are not merge failures either:",
                 "not called print-worthy are NOT NAMED HERE:",
                 "unnamed exceptions"),
        "the non-passing subjects stop being named", expect_red=True))

    # 6. a subject named as NOT print-worthy is ALSO claimed as print-worthy.
    #    Counting alone cannot catch this if the count is edited to match, so
    #    the overlap is checked directly.
    results.append(run(
        anchored(base,
                 "<code>wrapped-text-2</code>. Compound-eye",
                 "<code>flowers-cpl</code>, <code>wrapped-text-2</code>. "
                 "Compound-eye", "double-counted subject"),
        "a non-passing subject also claimed as print-worthy", expect_red=True))

    print()
    caught = sum(results[1:])
    print("=" * 58)
    print(f"null arm clean : {'yes' if results[0] else 'NO -- false positive'}")
    print(f"planted        : {len(results) - 1}")
    print(f"caught         : {caught}")
    print(f"missed         : {len(results) - 1 - caught}")
    ok = all(results)
    print("CHECK COMMISSIONED" if ok else "CHECK NOT COMMISSIONED")
    print("=" * 58)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
