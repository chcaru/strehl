"""Negative control on the guard: break it on purpose, require the suite to notice.

A commissioning suite that has only ever returned COMMISSIONED is in exactly the
position of the guard it commissions -- it has never been observed to refuse.

Two sabotages, each aimed at a different arm group:

  FROZEN   corpora() stops scanning and returns a hand-written snapshot. This is
           the decay mode the derived manifest exists to prevent, and it must be
           caught by the seal-perturbation arms specifically -- arms 1-8 keep
           passing under it, which is the whole point.
  PERMIT   refuse() returns OK instead of REFUSE, turning every refusal into a
           warning. Must be caught by the RED arms.

Each mutation is anchored on a full line asserted to occur EXACTLY ONCE, and
hard-errors if it does not land. A negative control that silently failed to
apply is a green that means nothing.

The file is restored from a $env:TEMP copy, never from git.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SUITE = os.path.join(HERE, "pincommission.py")

FROZEN = ("pinmanifest.py",
          '    root = root or os.path.join(OUT_ROOT, "acceptance")',
          '    return {"SHIP-V3": {"15EA73461905EA2D44B2F8242D578CD9330454450F61269AE1B1FBA71682A7B0": 26},\n'
          '            "SHIP-V4": {"44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490": 26}}')
PERMIT = ("pincheck.py",
          '    print("REFUSED: " + msg)',
          '    return OK')


def run_suite():
    p = subprocess.run([sys.executable, SUITE], capture_output=True, text=True)
    return p.returncode, p.stdout


def sabotage(fname, anchor, inject):
    path = os.path.join(HERE, fname)
    lines = open(path, encoding="utf-8").read().split("\n")
    hits = [i for i, l in enumerate(lines) if l == anchor]
    if len(hits) != 1:
        raise SystemExit("MUTATION TARGET NOT FOUND: %r occurs %d times in %s"
                         % (anchor, len(hits), fname))
    lines.insert(hits[0] + 1, inject)
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return path


if __name__ == "__main__":
    rc, out = run_suite()
    print("BASELINE                     exit %d  %s"
          % (rc, "COMMISSIONED" if rc == 0 else "not commissioned"))
    if rc != 0:
        raise SystemExit("baseline is already red; nothing to control")

    tmp = tempfile.mkdtemp(prefix="vg-pin-")
    for fname, anchor, inject in (FROZEN, PERMIT):
        path = os.path.join(HERE, fname)
        backup = os.path.join(tmp, fname)
        shutil.copy2(path, backup)
        try:
            sabotage(fname, anchor, inject)
            rc, out = run_suite()
            wrong = [l for l in out.split("\n") if "WRONG" in l]
            tag = "FROZEN" if fname == "pinmanifest.py" else "PERMIT"
            print("SABOTAGE %-20s exit %d  %s  (%d arms caught it)"
                  % (tag, rc, "RED -- caught" if rc != 0 else "GREEN -- BLIND",
                     len(wrong)))
            for l in wrong[:6]:
                print("     " + l.strip())
        finally:
            shutil.copy2(backup, path)

    rc, out = run_suite()
    same = all(open(os.path.join(HERE, f), "rb").read()
               == open(os.path.join(tmp, f), "rb").read()
               for f, _, _ in (FROZEN, PERMIT))
    print("RESTORED                     exit %d  %s   files byte-identical to backup: %s"
          % (rc, "COMMISSIONED" if rc == 0 else "STILL RED", same))
    shutil.rmtree(tmp, ignore_errors=True)
