"""V-KILLB0 softaudit.py -- conclusion-reversal audit of softverdict.py,
run THROUGH ITS SHIPPED ENTRY POINT (subprocess), per ORCH's three lessons:

  1. An inert plant and a dead instrument give the identical green.
     -> commission the PASS/FAIL CHANNEL: clean->0, planted->non-zero, prose->0.
  2. Commissioning sensitivity is not commissioning specificity.
     -> plant NOISE too: innocuous edits that must NOT flip the verdict.
  3. Commission DELETION as well as reversal.

Every mutation is anchored on a UNIQUE FULL LINE and hard-errors if it does not
land, so a green cannot come from an edit that silently missed.
"""
import subprocess, sys, os, shutil

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "softverdict.py")
OUT = r"D:\strehl-out\V-KILLB0\audit"
os.makedirs(OUT, exist_ok=True)
BASE = open(SRC, encoding="utf-8").read()

def mutate(text, old, new, tag):
    """Anchor on a unique full line; hard-error if it does not land."""
    if old is None:
        return text
    n = text.count(old)
    if n != 1:
        raise SystemExit("FATAL anchor for %r matched %d times, not 1: %r" % (tag, n, old))
    return text.replace(old, new)

def run(text, tag):
    path = os.path.join(OUT, "mut_%s.py" % tag)
    open(path, "w", encoding="utf-8").write(text)
    r = subprocess.run([sys.executable, path], capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")

ARMS = [
    # tag, anchor(old), replacement, must_exit_nonzero, why
    ("clean",   None, None, False, "CHANNEL: unmutated must be green (exit 0)"),
    ("flip_pyr",
     "    ndiff_pyr_112            = 0,     # gaussian vs unset, pyramid, 112MSDCF",
     "    ndiff_pyr_112            = 99999,",
     True,  "REVERSAL: pyramid moved pixels -> verdict must change and be caught"),
    ("flip_typo",
     "    typo_exit_pyramid_bee    = 0,     # same, bee-1-cpl --srgb",
     "    typo_exit_pyramid_bee    = 101,",
     True,  "REVERSAL: typo failed loudly on pyramid too"),
    ("dead_comparator",
     "    comparator_null          = 0,     # array vs itself -> must read 0",
     "    comparator_null          = 7,",
     True,  "REVERSAL: comparator dead -> must VOID, not pass"),
    ("delete_key",
     "    ndiff_est_112            = 14626891,",
     "",
     True,  "DELETION: removing a measurement must be caught, not silently green"),
    ("delete_arm",
     '    ("comparator dead (null broken)",      dict(comparator_null=7),                "VOID"),',
     "",
     True,  "DELETION: removing a commissioning arm must not stay 7/7 green"),
    ("prose",
     '"""V-KILLB0 softverdict.py -- verdict-binding check for the SOFT GATE finding.',
     '"""V-KILLB0 softverdict.py -- INNOCUOUS PROSE EDIT, no number touched.',
     False, "SPECIFICITY: prose-only edit must stay green (exit 0)"),
    ("noise_digit",
     "    ndiff_est_expo           = 22109494,",
     "    ndiff_est_expo           = 22109493,",
     False, "SPECIFICITY: irrelevant 1-count perturbation must NOT flip the verdict"),
]

print("%-18s %-6s %-8s %s" % ("arm", "exit", "result", "why"))
print("-" * 100)
bad = 0
for tag, old, new, want_fail, why in ARMS:
    text = mutate(BASE, old, new, tag)
    code, out = run(text, tag)
    failed = (code != 0)
    ok = (failed == want_fail)
    if not ok: bad += 1
    print("%-18s %-6d %-8s %s" % (tag, code, "OK" if ok else "*** BAD ***", why))
    if not ok:
        print("      expected exit %s, got %d" % ("non-zero" if want_fail else "0", code))
        print("      tail: " + out.strip().splitlines()[-1][:110] if out.strip() else "      (no output)")

print("-" * 100)
print("arms behaving correctly: %d/%d" % (len(ARMS) - bad, len(ARMS)))
if bad:
    sys.exit("FATAL: softverdict.py's pass/fail channel is not trustworthy")
print("PASS/FAIL CHANNEL COMMISSIONED: reversal->non-zero, deletion->non-zero, prose/noise->0.")
