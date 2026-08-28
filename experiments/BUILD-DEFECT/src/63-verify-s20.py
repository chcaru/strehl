"""Verify every numeric claim in BUILD-DEFECT.md section 20 against the logs.

RULE THIS OBEYS: no expected value is written in this file. Each claim is
parsed out of the report, each ground truth is parsed out of the log the
report cites, and the two are compared. A checker that compares the artifact
against its own constants runs green while the artifact drifts -- another lane
scored 37/37 that way and then caught only 5 of 13 plants.

Partition: every claim is resolved, unresolved or mismatched, and the three
sum to the number of claims found.
"""
import io, re, sys

REPORT = 'docs/research/BUILD-DEFECT.md'
LOGS = {
    'fid': 'experiments/BUILD-DEFECT/out/62-plant-fidelity.log',
    'geo': 'experiments/BUILD-DEFECT/out/61-geometry-verdict.log',
    'cen': 'experiments/BUILD-DEFECT/out/60-geometry-census.log',
}

doc = io.open(REPORT, encoding='utf-8').read()
sec = doc[doc.index('## 20. THE PLANTED-MOTE FIDELITY'):]
log = {k: io.open(v, encoding='utf-8', errors='replace').read() for k, v in LOGS.items()}

def norm(s):
    return re.sub(r'\s+', ' ', s)

nsec = norm(sec)

CLAIMS = []

# Scoped haystacks. A claim aimed at a restatement in prose must search only
# that prose: the section 20.6 table states the same quantities and matched
# first, so four claims resolved against the wrong site and read as mismatches.
def slice_between(text, start, end):
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]

def claim(label, pat, probe, src='fid', scope='all'):
    CLAIMS.append((label, pat, probe, src, scope))

claim('arm A residual', r'A CHARGE\s+planted, uncorrected\s+residual\s+([\d.]+) DN',
      lambda m: 'A CHARGE planted, uncorrected residual %s DN' % m)
claim('arm B residual', r'B FIDELITY\s+planted, exact gain\s+residual\s+([\d.]+) DN',
      lambda m: 'B FIDELITY planted, exact gain residual %s DN' % m)
claim('arm E residual', r'E PERVERSE\s+planted, 2x gain\s+residual\s+([\d.]+) DN',
      lambda m: 'E PERVERSE planted, 2x gain residual %s DN' % m)
claim('arm F0 residual', r'F0 MISMATCH\s+gaussian mote, raw\s+residual\s+([\d.]+) DN',
      lambda m: 'F0 MISMATCH gaussian mote, raw residual %s DN' % m)
claim('arm F residual', r'F\s+MISMATCH\s+gaussian, parabolic fix residual\s+([\d.]+) DN',
      lambda m: 'F MISMATCH gaussian, parabolic fix residual %s DN' % m)
claim('arm A ring', r'A CHARGE\s+planted, uncorrected\s+residual\s+[\d.]+ DN\s+ring\s+([\d.]+) DN',
      lambda m: 'ring %s DN' % m)
claim('arm F0 ring', r'F0 MISMATCH\s+gaussian mote, raw\s+residual\s+[\d.]+ DN\s+ring\s+([\d.]+) DN',
      lambda m: 'ring %s DN' % m)
claim('arm F ring', r'F\s+MISMATCH\s+gaussian, parabolic fix residual\s+[\d.]+ DN\s+ring\s+([\d.]+) DN',
      lambda m: 'ring %s DN' % m)
claim('truth HF', r'HF energy\s+truth ([\d.]+)', lambda m: 'truth %s' % m)
claim('B HF', r'HF energy\s+truth [\d.]+\s+B ([\d.]+)', lambda m: 'B %s' % m)
claim('commissioning BASELINE', r'expect >= floor\s+PASS\s+BASELINE\s+untouched site\s+([\d.]+)%',
      lambda m: 'BASELINE untouched site %s%%' % m)
claim('prior-stat unsigned', r'PRIOR-STAT\s+unsigned worst quad\s+([\d.]+)%\s+expect >= floor\s+PASS',
      lambda m: 'PRIOR-STAT unsigned worst quad %s%%' % m)
claim('commissioning DEFECT', r'DEFECT\s+disc in both halves\s+([\d.]+)%',
      lambda m: 'DEFECT disc in both halves %s%%' % m)
claim('commissioning NULL', r'NULL\s+disc in one half only\s+([\d.]+)%',
      lambda m: 'NULL disc in one half only %s%%' % m)
claim('commissioning IMPROVEMENT', r'IMPROVEMENT planted mote divided out\s+([\d.]+)%',
      lambda m: 'IMPROVEMENT planted mote divided out %s%%' % m)
claim('disc response at site', r'disc response ([\d.]+)%',
      lambda m: 'disc response %s%%' % m)
claim('worst single quad', r'worst single quad in the same region ([\d.]+)%',
      lambda m: 'worst single quad in the same region %s%%' % m)
claim('site signal DN', r'site reads ([\d.]+) DN = ',
      lambda m: 'site signal : %s DN' % m)
claim('dark-on-subject count', r'which is where ([\d,]+) of the',
      lambda m: 'dark-on-subject %s' % m.replace(',', ''))
claim('candidates scanned', r'refused all ([\d,]+) candidates',
      lambda m: 'scanned %s' % m.replace(',', ''))
claim('near-mote count', r'Only (\d+) sites were excluded by mote clearance',
      lambda m: 'near-mote %s' % m)
claim('corrector examined', r'examined (\d+) = corrected', lambda m: 'examined %s = corrected' % m)
claim('wide mismatch pct', r'wide\s+7040x4688\s+ADMITTED\s+mismatch ([\d.]+)%',
      lambda m: 'mismatch %s%%' % m, 'geo')
claim('mapped quad max', r'max mapped quad px (\d+)', lambda m: 'max mapped quad px %s' % m, 'geo')
claim('narrow quad limit', r'narrow quad limit (\d+)', lambda m: 'narrow quad limit %s' % m, 'geo')
claim('census exact-match', r'exact-match (\d+) / 27', lambda m: 'exact-match %s / 27' % m, 'cen')
claim('census differing', r'differing-but-admitted (\d+) / 27',
      lambda m: 'differing-but-admitted %s / 27' % m, 'cen')
claim('mapped motes', r'the ([\d,]+) quads this map names',
      lambda m: 'dust quads : %s' % m.replace(',', ''), 'geo')
claim('flats used', r'The (\d+) usable flats were therefore accumulated',
      lambda m: 'used %s' % m)
claim('narrow admitted pct', r'narrow\s+7032x4688\s+ADMITTED\s+mismatch ([\d.]+)%',
      lambda m: 'mismatch %s%%' % m, 'geo')

# --- section 20.7 restates the arm-F numbers in prose --------------------
# The commissioning run caught this gap: a plant on the 20.7 ring stayed GREEN
# because only the 20.6 table was pinned. One measured number with two sites in
# the document needs two anchors, or the unpinned one drifts silently.
claim('20.7 uncorrected pair',
      r'uncorrected\s+residual ([\d.]+) DN\s+ring [\d.]+ DN',
      lambda m: 'F0 MISMATCH gaussian mote, raw residual %s DN' % m, 'fid', 's207')
claim('20.7 uncorrected ring',
      r'uncorrected\s+residual [\d.]+ DN\s+ring ([\d.]+) DN',
      lambda m: 'gaussian mote, raw residual 67.365 DN ring %s DN' % m, 'fid', 's207')
claim('20.7 corrected residual',
      r'\bcorrected\s+residual ([\d.]+) DN\s+ring [\d.]+ DN',
      lambda m: 'F MISMATCH gaussian, parabolic fix residual %s DN' % m, 'fid', 's207')
claim('20.7 corrected ring',
      r'\bcorrected\s+residual [\d.]+ DN\s+ring ([\d.]+) DN',
      lambda m: 'gaussian, parabolic fix residual 31.825 DN ring %s DN' % m, 'fid', 's207')

# --- DERIVED checks: recomputed, never string-matched ---------------------
# A percentage that is only compared against itself elsewhere in the document
# is not verified. These recompute the claim from the report's OWN residuals
# and require the arithmetic to agree, so a defect in either input surfaces
# here even if that input's own claim were somehow satisfied.
DERIVED = []

def derived(label, fn):
    DERIVED.append((label, fn))

def _f(pat, text):
    m = re.search(pat, text)
    return float(m.group(1)) if m else None

def check_removed_pct():
    s = norm(slice_between(sec, '### 20.7', '### 20.8'))
    f0 = _f(r'uncorrected\s+residual ([\d.]+) DN', s)
    f1 = _f(r'\bcorrected\s+residual ([\d.]+) DN', s)
    claimed = _f(r'-> ([\d.]+)% of the charge removed', s)
    if None in (f0, f1, claimed):
        return None, 'an input to the derivation is missing'
    calc = 100.0 * (1.0 - f1 / f0)
    return abs(calc - claimed) <= 0.05, 'report %.1f%% vs recomputed %.4f%%' % (claimed, calc)

def check_ring_pct():
    s = norm(slice_between(sec, '### 20.7', '### 20.8'))
    r0 = _f(r'uncorrected\s+residual [\d.]+ DN\s+ring ([\d.]+) DN', s)
    r1 = _f(r'\bcorrected\s+residual [\d.]+ DN\s+ring ([\d.]+) DN', s)
    claimed = _f(r'a\s+reduction of ([\d.]+)%', s)
    if None in (r0, r1, claimed):
        return None, 'an input to the derivation is missing'
    calc = 100.0 * (1.0 - r1 / r0)
    return abs(calc - claimed) <= 0.05, 'report %.1f%% vs recomputed %.4f%%' % (claimed, calc)

derived('52.8% charge removed is arithmetic on 20.7 residuals', check_removed_pct)
derived('12.8% ring reduction is arithmetic on 20.7 rings', check_ring_pct)

SCOPES = {
    'all': nsec,
    's207': norm(slice_between(sec, '### 20.7', '### 20.8')),
}

resolved, unresolved, mismatched = [], [], []
for label, pat, probe, src, scope in CLAIMS:
    m = re.search(pat, SCOPES[scope])
    if not m:
        unresolved.append((label, 'claim not found in the report'))
        continue
    val = m.group(1) if m.groups() else ''
    want = norm(probe(val))
    hay = norm(log[src])
    if want in hay:
        resolved.append((label, val))
    else:
        mismatched.append((label, val, want))

for label, fn in DERIVED:
    ok, why = fn()
    if ok is None:
        unresolved.append(('DERIVED ' + label, why))
    elif ok:
        resolved.append(('DERIVED ' + label, why))
    else:
        mismatched.append(('DERIVED ' + label, why, 'recomputation disagrees'))

TOTAL = len(CLAIMS) + len(DERIVED)
print('claims declared   :', TOTAL, '(%d parsed + %d derived)' % (len(CLAIMS), len(DERIVED)))
print('resolved          :', len(resolved))
print('unresolved        :', len(unresolved))
print('mismatched        :', len(mismatched))
tot = len(resolved) + len(unresolved) + len(mismatched)
print('partition sums    :', tot == TOTAL, '(%d)' % tot)
for l, w in unresolved:
    print('  UNRESOLVED', l, '--', w)
for l, v, w in mismatched:
    print('  MISMATCH  ', l, '| report value', repr(v), '| probe', repr(w))
sys.exit(0 if not unresolved and not mismatched else 1)