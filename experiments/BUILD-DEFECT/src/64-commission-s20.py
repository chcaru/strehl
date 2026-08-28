"""Commission 63-verify-s20.py by planting known defects in the report.

A checker that runs green has said nothing until it has been shown to go RED.
Each plant below is anchored on a UNIQUE full-line string and the script hard
errors if the anchor does not land -- a bare replace(x, y, 1) that silently
hits the wrong occurrence banks a green as a catch.

Partition: every plant is caught, missed or unanchored, and the three sum.
"""
import io, os, re, shutil, subprocess, sys, tempfile

REPORT = 'docs/research/BUILD-DEFECT.md'
VERIFY = 'experiments/BUILD-DEFECT/src/63-verify-s20.py'

# (label, exact unique line fragment to find, replacement)
PLANTS = [
    ('arm B residual digit',
     'B FIDELITY     planted, exact gain     residual    0.097 DN   ring   0.019 DN',
     'B FIDELITY     planted, exact gain     residual    0.098 DN   ring   0.019 DN'),
    ('arm F residual',
     'F  MISMATCH    gaussian, parabolic fix residual   31.825 DN   ring  33.250 DN',
     'F  MISMATCH    gaussian, parabolic fix residual   21.825 DN   ring  33.250 DN'),
    ('arm F ring',
     'corrected    residual 31.825 DN   ring 33.250 DN     -> 52.8% of the charge removed',
     'corrected    residual 31.825 DN   ring 13.250 DN     -> 52.8% of the charge removed'),
    ('commissioning DEFECT',
     'DEFECT      disc in both halves          1.88280%   expect >= 4x baseline   PASS',
     'DEFECT      disc in both halves          1.88281%   expect >= 4x baseline   PASS'),
    ('prior-stat value',
     'PRIOR-STAT  unsigned worst quad   0.47301%   expect >= floor   PASS',
     'PRIOR-STAT  unsigned worst quad   0.47302%   expect >= floor   PASS'),
    ('wide mismatch pct',
     'wide   7040x4688  ADMITTED   mismatch 0.1138% vs bar 1.00%',
     'wide   7040x4688  ADMITTED   mismatch 0.1139% vs bar 1.00%'),
    ('census differing count',
     'differing-but-admitted 12 / 27',
     'differing-but-admitted 11 / 27'),
    ('near-mote count',
     'Only 568 sites were excluded by mote clearance',
     'Only 569 sites were excluded by mote clearance'),
    ('candidates scanned',
     'It refused all 110,538 candidates',
     'It refused all 110,539 candidates'),
    ('dark-on-subject count',
     'which is where 85,764 of the 110,538 candidates go',
     'which is where 85,760 of the 110,538 candidates go'),
    ('flats used',
     'The 120 usable flats were therefore accumulated',
     'The 140 usable flats were therefore accumulated'),
    ('truth HF',
     'D INVENTION    HF energy   truth 334.6762   B 334.7147   E 346.7149',
     'D INVENTION    HF energy   truth 334.6763   B 334.7147   E 346.7149'),
    ('mapped quad max',
     'max mapped quad px 3448, narrow quad limit 3516',
     'max mapped quad px 3444, narrow quad limit 3516'),
    ('site signal',
     'the site reads 2061.4 DN = 0.139 of range',
     'the site reads 2061.5 DN = 0.139 of range'),
]

orig = io.open(REPORT, encoding='utf-8').read()
backup = os.path.join(tempfile.gettempdir(), 'BUILD-DEFECT.s20commission.bak')
io.open(backup, 'w', encoding='utf-8', newline='').write(orig)
print('backup ->', backup)

def run_verifier():
    r = subprocess.run([sys.executable, VERIFY], capture_output=True, text=True)
    return r.returncode, r.stdout

rc, out = run_verifier()
if rc != 0:
    print('ABORT: the live report does not verify clean; commissioning is meaningless')
    print(out)
    sys.exit(2)
print('live report verifies clean (rc=0)')
print()

caught, missed, unanchored = [], [], []
try:
    for label, needle, repl in PLANTS:
        n = orig.count(needle)
        if n != 1:
            unanchored.append((label, 'anchor occurs %d times, need exactly 1' % n))
            continue
        io.open(REPORT, 'w', encoding='utf-8', newline='\n').write(orig.replace(needle, repl, 1))
        rc, out = run_verifier()
        if rc != 0:
            caught.append((label, re.findall(r'  (?:MISMATCH|UNRESOLVED)\s+\S.*', out)[:1]))
        else:
            missed.append((label, 'verifier stayed GREEN'))
        io.open(REPORT, 'w', encoding='utf-8', newline='').write(orig)
finally:
    io.open(REPORT, 'w', encoding='utf-8', newline='').write(orig)

print('plants declared :', len(PLANTS))
print('caught          :', len(caught))
print('missed          :', len(missed))
print('unanchored      :', len(unanchored))
tot = len(caught) + len(missed) + len(unanchored)
print('partition sums  :', tot == len(PLANTS), '(%d)' % tot)
print()
for l, w in caught:
    print('  CAUGHT    ', l, '->', (w[0].strip() if w else ''))
for l, w in missed:
    print('  MISSED    ', l, '--', w)
for l, w in unanchored:
    print('  UNANCHORED', l, '--', w)

# The report must be byte-identical to how it started.
after = io.open(REPORT, encoding='utf-8').read()
print()
print('report restored byte-identical :', after == orig)
sys.exit(0 if (not missed and not unanchored and after == orig) else 1)