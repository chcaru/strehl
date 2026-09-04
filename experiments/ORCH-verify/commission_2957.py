"""Commission the three 2.9.57 claims added to v2954.py.

A check that has never failed may be a silent no-op. Each claim below is
proven live by planting the exact defect it targets in STATUS.md and
requiring the verifier to go RED.

STATUS.md is backed up to a temp copy and restored from that copy -- never
via `git checkout --`, which reverts to HEAD and destroys uncommitted work.
Every mutation is anchored on a unique full-line-ish literal and HARD ERRORS
if the anchor is not found, because a mutation that silently fails to apply
reads as a pass.
"""
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "docs" / "STATUS.md"
VERIFIER = ROOT / "experiments" / "ORCH-verify" / "v2954.py"
BACKUP = Path(os.environ["TEMP"]) / "STATUS_2957_commission_backup.md"

# (label, anchor that must exist, replacement)
MUTATIONS = [
    ("m137 flat beats detail",
     "ratio **`1.0249391472947889`**",
     "ratio **`1.0249391472947880`**"),
    ("m2 battery replay",
     "blurred/unblurred = **`0.5712148772282098`**",
     "blurred/unblurred = **`0.5712148772282090`**"),
    ("m167 results sha",
     "`210675AB3BC25FCE53EE090AAEE98E69330E95F3EC8C19FDC1CA59BCEF9229B0`",
     "`210675AB3BC25FCE53EE090AAEE98E69330E95F3EC8C19FDC1CA59BCEF9229B1`"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def run_verifier() -> tuple[int, str]:
    r = subprocess.run([sys.executable, "-B", str(VERIFIER)],
                       capture_output=True, text=True, cwd=str(ROOT))
    return r.returncode, r.stdout + r.stderr


def main() -> int:
    original_sha = sha(STATUS)
    shutil.copy2(STATUS, BACKUP)
    print(f"backup      : {BACKUP}")
    print(f"STATUS sha  : {original_sha}")

    rc, out = run_verifier()
    if rc != 0 or "VERDICT: GREEN" not in out:
        print("PRECONDITION FAILED: verifier is not GREEN before commissioning.")
        print(out[-2000:])
        return 1
    print("precondition: GREEN\n")

    caught, missed = 0, []
    try:
        for label, anchor, replacement in MUTATIONS:
            text = BACKUP.read_text(encoding="utf-8")
            if anchor not in text:
                raise SystemExit(
                    f"MUTATION TARGET NOT FOUND for {label!r}: {anchor!r}. "
                    "Refusing to report a result on an unapplied mutation."
                )
            if text.count(anchor) != 1:
                raise SystemExit(
                    f"ANCHOR NOT UNIQUE for {label!r}: {text.count(anchor)} sites. "
                    "A presence check is satisfied by any duplicate."
                )
            STATUS.write_text(text.replace(anchor, replacement, 1), encoding="utf-8")
            rc, out = run_verifier()
            red = rc != 0 or "VERDICT: RED" in out
            if red:
                caught += 1
                detail = [ln for ln in out.splitlines()
                          if ln.startswith("RED") and label.split()[0] in ln.lower()]
                print(f"  RED   {label:28s} control PASSED"
                      + (f"  | {detail[0][:90]}" if detail else ""))
            else:
                missed.append(label)
                print(f"  GREEN {label:28s} *** CONTROL FAILED -- CHECK IS A NO-OP ***")
    finally:
        shutil.copy2(BACKUP, STATUS)

    restored_sha = sha(STATUS)
    print(f"\nrestored sha: {restored_sha}")
    if restored_sha != original_sha:
        print("*** RESTORE MISMATCH -- STATUS.md DIFFERS FROM BACKUP ***")
        return 1
    print("restore     : byte-identical to backup")

    rc, out = run_verifier()
    final_green = rc == 0 and "VERDICT: GREEN" in out
    print(f"final run   : {'GREEN' if final_green else 'NOT GREEN'}")

    total = len(MUTATIONS)
    print(f"\ncontrols    : {caught} caught + {len(missed)} missed = {total} of {total}")
    if missed:
        print(f"MISSED      : {missed}")
    ok = caught == total and not missed and final_green
    print(f"\nVERDICT: {'COMMISSIONED' if ok else 'NOT COMMISSIONED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
