"""Commission the repaired verify_gallery.py: prove it can still say NO.

I changed a verifier and it immediately reported GALLERY VERIFIED on the deliverable.
That is exactly the reading a verifier gives when it has been broken into silence, so
the green is worthless until the instrument is shown to be potent.

Method: copy the whole gallery to a scratch tree (assets are resolved relative to the
index, so the index alone is not enough), then run four arms:

  NULL    unmutated copy                      -> must be GREEN
  M1      break an <img src>                  -> must be RED
  M2      delete one card section             -> must be RED
  M3      truncate a container (nesting)      -> must be RED

Each mutation is anchored on a unique full-line/substring and HARD-ERRORS if the anchor
is not found, because a mutation that silently fails to apply produces a GREEN that
looks exactly like a passing control.
"""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

SRC = pathlib.Path(r"C:\dev\strehl-out\VIEW-SHIP")
VERIFY = pathlib.Path(__file__).with_name("verify_gallery.py")


def run(idx):
    p = subprocess.run([sys.executable, str(VERIFY), str(idx)],
                       capture_output=True, text=True)
    out = p.stdout + p.stderr
    if "GALLERY VERIFIED" in out:
        return "GREEN", out
    if "GALLERY NOT VERIFIED" in out or "REFUSE" in out:
        return "RED", out
    return f"UNREADABLE(rc={p.returncode})", out


def anchored(doc, needle, repl, label):
    n = doc.count(needle)
    if n == 0:
        raise SystemExit(f"MUTATION TARGET NOT FOUND for {label}: {needle[:70]!r}")
    return doc.replace(needle, repl, 1)


def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="commission-gallery-"))
    dst = tmp / "VIEW-SHIP"
    print(f"pinning {SRC} -> {dst}")
    shutil.copytree(SRC, dst)
    idx = dst / "index.html"
    base = idx.read_text(encoding="utf-8")
    print(f"  pinned index {len(base)} chars, {len(list((dst/'assets').iterdir()))} assets\n")

    results = {}

    v, _ = run(idx)
    results["NULL  (unmutated)"] = (v, "GREEN")

    m1 = anchored(base,
                  'src="assets/bee-1-cpl--SHIP-V2--full.jpg"',
                  'src="assets/DOES-NOT-EXIST.jpg"', "M1 broken img src")
    idx.write_text(m1, encoding="utf-8")
    v, _ = run(idx)
    results["M1    broken <img src>"] = (v, "RED")

    sec = re.search(r'<section class="card">.*?</section>\s*', base, re.S)
    if not sec:
        raise SystemExit("MUTATION TARGET NOT FOUND for M2: no card section")
    m2 = base.replace(sec.group(0), "", 1)
    idx.write_text(m2, encoding="utf-8")
    v, _ = run(idx)
    results["M2    deleted one card"] = (v, "RED")

    m3 = anchored(base, '<div class="pair">', '<div class="pair"><div>', "M3 nesting")
    idx.write_text(m3, encoding="utf-8")
    v, _ = run(idx)
    results["M3    unbalanced container"] = (v, "RED")

    idx.write_text(base, encoding="utf-8")
    v, _ = run(idx)
    results["NULL2 (restored)"] = (v, "GREEN")

    print("arm                          got     expected  verdict")
    print("-" * 58)
    ok = True
    for k, (got, exp) in results.items():
        good = got == exp
        ok &= good
        print(f"{k:28s} {got:7s} {exp:8s}  {'ok' if good else '** MISMATCH **'}")
    print()
    if ok:
        print("COMMISSIONED: the verifier is potent -- it reports RED on all three "
              "sabotages and GREEN on both nulls.")
    else:
        print("NOT COMMISSIONED: an arm disagreed; the GREEN on the deliverable "
              "cannot be trusted.")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
