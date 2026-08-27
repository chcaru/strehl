r"""Sabotage the guard three ways and require it to notice each one.

FROZEN and PERMIT were the original two. The third, NARROW, exists because this
lane's own scan was the thing that failed tonight: it reverts find_binaries to
the exact-name query that produced the false negative. If the commissioning's
reach arms are real, NARROW must turn them RED. If they stay green, the decoys
are decoration.

Every mutation is anchored on a full line asserted to occur EXACTLY ONCE and
hard-errors otherwise -- a sabotage that silently fails to land reads as a clean
pass, which is the failure mode this whole exercise exists to prevent. Files are
restored from a %TEMP% copy, never from git.
"""
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
COMMISSION = os.path.join(HERE, "pincommission.py")

SABOTAGE = {
    "FROZEN": (
        os.path.join(HERE, "pinmanifest.py"),
        '    """Pass-through by default. pinnegctl.py\'s FROZEN sabotage rebinds this."""\n'
        '    return _ORIG_CORPORA(root)',
        '    """FROZEN: cache the derived manifest to disk and never refresh it."""\n'
        '    import json as _j, tempfile as _t\n'
        '    c = os.path.join(_t.gettempdir(), "pin-frozen-manifest.json")\n'
        '    key = os.path.normcase(root or "(default)")\n'
        '    d = {}\n'
        '    if os.path.exists(c):\n'
        '        d = _j.load(open(c, encoding="utf-8"))\n'
        '        if key in d:\n'
        '            return d[key]\n'
        '    v = _ORIG_CORPORA(root)\n'
        '    d[key] = v\n'
        '    _j.dump(d, open(c, "w", encoding="utf-8"))\n'
        '    return v',
        "the manifest is derived ONCE and cached; every later call reads the cache.\n"
        "         Values start CORRECT, so nothing about any binary looks wrong"),
    "PERMIT": (
        os.path.join(HERE, "pincheck.py"),
        '    print("REFUSED: " + msg)',
        '    print("REFUSED: " + msg)\n    return 0',
        "every refusal downgrades to a warning that still exits 0"),
    "NARROW": (
        os.path.join(HERE, "pinmanifest.py"),
        "def find_binaries(root, pattern=PIN_PATTERN):",
        "def find_binaries(root, pattern=PIN_PATTERN):\n"
        "    import glob as _g\n"
        "    return [p for p in _g.glob(os.path.join(root, '**', 'strehl.exe'),\n"
        "                               recursive=True) if os.path.isfile(p)]",
        "the scan reverts to the exact-name query that produced the false negative"),
}


def run_commission():
    p = subprocess.run([sys.executable, COMMISSION], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def arms(out):
    """Split the suite's arms into the two families a sabotage can hit."""
    binary = seals = reach = 0
    for line in out.splitlines():
        if "WRONG" not in line:
            continue
        if line.startswith("REACH"):
            reach += 1
        elif "re-seal" in line or "RESEALED" in line or "seals perturbed" in line:
            seals += 1
        else:
            binary += 1
    return binary, seals, reach


if __name__ == "__main__":
    rc, out = run_commission()
    print("BASELINE  exit=%d  %s" % (rc, "COMMISSIONED" if rc == 0 else "NOT COMMISSIONED"))
    if rc != 0:
        raise SystemExit("baseline is not green; sabotage results would be unreadable")

    stale = os.path.join(tempfile.gettempdir(), "pin-frozen-manifest.json")
    if os.path.exists(stale):
        os.remove(stale)
    tmp = tempfile.mkdtemp(prefix="pinnegctl-")
    originals = {}
    try:
        for name, (path, anchor, repl, why) in SABOTAGE.items():
            back = os.path.join(tmp, "%s-%s" % (name, os.path.basename(path)))
            shutil.copy2(path, back)
            originals[back] = path
            s = io.open(path, encoding="utf-8").read()
            if s.count(anchor) != 1:
                raise SystemExit("MUTATION TARGET NOT FOUND: %r occurs %d times in %s"
                                 % (anchor[:50], s.count(anchor), path))
            io.open(path, "w", encoding="utf-8", newline="\n").write(
                s.replace(anchor, repl))
            rc2, out2 = run_commission()
            b, sl, r = arms(out2)
            print("\n%-8s %s" % (name, why))
            print("         exit=%d   arms that went RED: binary %d, seals %d, reach %d"
                  % (rc2, b, sl, r))
            print("         %s" % ("CAUGHT" if rc2 != 0 else
                                   "*** NOT CAUGHT -- the suite is blind to this ***"))
            shutil.copy2(back, path)
            if os.path.exists(stale):
                os.remove(stale)
    finally:
        for back, path in originals.items():
            shutil.copy2(back, path)
        for back, path in originals.items():
            a = hashlib.sha256(open(back, "rb").read()).hexdigest()
            b = hashlib.sha256(open(path, "rb").read()).hexdigest()
            print("restored %-18s %s" % (os.path.basename(path),
                                         "byte-identical" if a == b else "*** DIFFERS ***"))
        shutil.rmtree(tmp, ignore_errors=True)

    rc3, _ = run_commission()
    print("\nAFTER RESTORE  exit=%d  %s" % (rc3, "green again" if rc3 == 0 else "STILL RED"))
