"""Measure STREHL_FULLRES_GATHER's default on the pinned shipping binary.

Three arms, ONE binary, identical flags, differing only in the variable:

  unset  -- what the product does when nobody touches it
  off    -- the old per-CFA-plane gather
  bogus  -- must PANIC, which is the positive control proving the read is live

The pair (unset, off) proves the polarity: if the renders differ, unset is
demonstrably not off. The bogus arm is what makes a null in the first pair
interpretable -- without it, two identical renders could mean "the default is
off" or "the variable is never read at all", and those are different facts.
"""

import hashlib
import pathlib
import subprocess
import sys

PIN = pathlib.Path(
    r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
)
SUBJECT = pathlib.Path(r"D:\personal\macro\bee-3-cpl")
OUTDIR = pathlib.Path(r"C:\dev\strehl-out\ORCH-fullres")


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16].upper()


def run(tag: str, value: str | None) -> tuple[int, str, str]:
    out = OUTDIR / f"{tag}.tiff"
    if out.exists():
        out.unlink()
    env = None
    if value is not None:
        import os

        env = dict(os.environ)
        env["STREHL_FULLRES_GATHER"] = value
    else:
        import os

        env = dict(os.environ)
        env.pop("STREHL_FULLRES_GATHER", None)
    r = subprocess.run(
        [
            str(PIN),
            "stack",
            str(SUBJECT),
            "--out",
            str(out),
            "--srgb",
            "--auto-exposure",
            "--limit",
            "3",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    digest = sha(out) if out.exists() else "(no output)"
    return r.returncode, digest, (r.stderr or "")[-400:]


def main() -> int:
    if not PIN.exists():
        print(f"FATAL: pin missing: {PIN}")
        return 2
    if not SUBJECT.exists():
        print(f"FATAL: subject missing: {SUBJECT}")
        return 2
    OUTDIR.mkdir(parents=True, exist_ok=True)

    print(f"pin     : {PIN}")
    print(f"pin sha : {sha(PIN)}")
    print(f"subject : {SUBJECT}  (--limit 3)")
    print()

    rc_unset, h_unset, e_unset = run("unset", None)
    print(f"unset   rc={rc_unset}  sha={h_unset}")
    rc_off, h_off, e_off = run("off", "off")
    print(f"off     rc={rc_off}  sha={h_off}")
    rc_bad, h_bad, e_bad = run("bogus", "maybe")
    print(f"bogus   rc={rc_bad}  sha={h_bad}")
    print()

    ok = True

    if rc_unset != 0 or rc_off != 0:
        print("FAIL: an arm that should render did not render.")
        print(f"  unset stderr tail: {e_unset}")
        print(f"  off   stderr tail: {e_off}")
        ok = False

    if h_unset == "(no output)" or h_off == "(no output)":
        print("FAIL: missing render.")
        ok = False
    elif h_unset == h_off:
        print(
            "FAIL: unset and off are byte-identical. Either the default IS off,\n"
            "      or the variable is not read on this path. The bogus arm below\n"
            "      is what distinguishes those two."
        )
        ok = False
    else:
        print(f"PASS: unset ({h_unset}) differs from off ({h_off}).")
        print("      unset is demonstrably NOT off.")

    if rc_bad == 0:
        print(
            "FAIL: STREHL_FULLRES_GATHER=maybe was ACCEPTED. The doc comment says an\n"
            "      unrecognised value must panic rather than fall back, because a typo\n"
            "      that silently selects the default is exactly the failure that matters."
        )
        ok = False
    else:
        print(f"PASS: bogus value refused (rc={rc_bad}) -- the read is live.")
        tail = e_bad.strip().splitlines()
        if tail:
            print(f"      {tail[-1][:160]}")

    print()
    print("VERDICT:", "GREEN" if ok else "RED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
