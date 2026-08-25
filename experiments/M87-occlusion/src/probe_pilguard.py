import pathlib, shutil, subprocess, sys, tempfile, os
SRC = pathlib.Path("src")
AUD = [sys.executable, "src/fix_audit.py"]

def run():
    r = subprocess.run(AUD, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)

rc, out = run()
print("BASELINE      rc=%d  %s" % (rc, "PASS" if rc == 0 else "FAIL"))
print("   ", [l for l in out.splitlines() if "invocation" in l or "P40" in l])

# negative control: plant a PIL .tif read in a NON-exempt measurement script
TARGET = SRC / "44-detail-check.py"
ANCHOR = 'S = pathlib.Path(r"C:\\dev\\strehl-out\\M87-before-after")'
orig = TARGET.read_text(encoding="utf-8")
if ANCHOR not in orig:
    raise SystemExit("MUTATION TARGET NOT FOUND -- control is invalid, aborting")
bak = pathlib.Path(tempfile.gettempdir()) / "44-detail-check.py.bak"
shutil.copy2(TARGET, bak)
try:
    TARGET.write_text(orig.replace(ANCHOR, ANCHOR + '\nz = Image.open(S/"30-SHIP-BEFORE-default.tif")', 1),
                      encoding="utf-8")
    rc2, out2 = run()
    print("NEGCTL(plant) rc=%d  %s" % (rc2, "RED (guard fired)" if rc2 != 0 else "GREEN -- GUARD IS BLIND"))
    print("   ", [l.strip() for l in out2.splitlines() if "P40" in l])
finally:
    shutil.copy2(bak, TARGET)
    os.remove(bak)
assert TARGET.read_text(encoding="utf-8") == orig, "RESTORE FAILED"
rc3, _ = run()
print("RESTORED      rc=%d  %s" % (rc3, "PASS" if rc3 == 0 else "FAIL"))
