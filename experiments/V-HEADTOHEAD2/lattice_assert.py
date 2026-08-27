# V-H2H2 -- THE OUTPUT LATTICE ASSERTION.
#
# WHY THIS EXISTS.  The defect that produced the gallery the owner called
# unusable was a resampling path that silently band-limited every frame to a
# quarter of output Nyquist, and it survived because NOTHING ASSERTED THE
# OUTPUT LATTICE.  This asserts it.
#
# It checks two DIFFERENT things, and the difference is the point:
#
#   (1) ANNOUNCED == ACTUAL.  The `wrote:` line names the lattice it emitted.
#       Does the file on disk agree?  This catches a tool that says one thing
#       and does another -- the failure a user cannot see.
#
#   (2) ACTUAL == REQUESTED.  Does the lattice match what the documented flag
#       semantics promise?  This catches a tool that is honest about doing the
#       wrong thing.
#
# A harness that only checked (1) would pass a build that halved every output
# and faithfully reported it.  A harness that only checked (2) would pass a
# build whose log lies.  Both are needed.
#
# COMMISSIONED IN BOTH DIRECTIONS at the bottom: the checker must ACQUIT the
# real renders and CONVICT planted mismatches of each kind.  A checker only
# ever shown to pass is not evidence.

import os, re, subprocess, sys, tifffile

EXE = r'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe'
SRC = r'D:\personal\macro\foam'
OUT = r'C:\dev\strehl-out\V-H2H2\lattice'
PLANE_W, PLANE_H = 3516, 2344          # foam's CFA plane, from its own render log
FULL_W, FULL_H = PLANE_W * 2, PLANE_H * 2

# Expectations are derived from `strehl stack --help`, quoted, not guessed:
#   default  -- "By DEFAULT the output is BINNED ... at half the sensor's
#                linear resolution ... It is byte-frozen."
#   --demosaic -- "Emit at full sensor resolution ... Doubles linear resolution"
#                "This is ON BY DEFAULT whenever --srgb is given"
#   --binned -- "Opt out: bin each 2x2 quad to one pixel in the --srgb render"
#   --demosaic + --binned -- documented as mutually exclusive
CASES = [
    ('default',            [],                              (PLANE_W, PLANE_H)),
    ('demosaic',           ['--demosaic'],                   (FULL_W, FULL_H)),
    ('srgb',               ['--srgb'],                       (FULL_W, FULL_H)),
    ('srgb+binned',        ['--srgb', '--binned'],           (PLANE_W, PLANE_H)),
    ('linear-srgb',        ['--linear-srgb'],                None),   # UNDOCUMENTED: measure it
    ('linear-srgb+demo',   ['--linear-srgb', '--demosaic'],  (FULL_W, FULL_H)),
    ('demosaic+binned',    ['--demosaic', '--binned'],       'ERROR'),
]

WROTE = re.compile(r'wrote\s*:.*?\((\d+) x (\d+)')


def render(tag, flags):
    """Run one render. Returns (exit, announced|None, actual|None, logtext)."""
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, f'{tag}.tiff')
    if os.path.exists(dst):
        os.remove(dst)
    env = dict(os.environ)
    for v in ('STREHL_FULLRES_GATHER', 'STREHL_WARPMAP', 'STREHL_MERGE',
              'STREHL_FIX_CA', 'STREHL_PHOTOMETRIC'):
        env.pop(v, None)
    env['STREHL_ALIGN'] = '0'          # flag-behaviour test; registration is irrelevant
    cmd = [EXE, 'stack', SRC, '--out', dst, '--merge', 'pyramid',
           '--pyramid-gate', '4.5', '--limit', '8'] + flags
    p = subprocess.run(cmd, capture_output=True, env=env)
    log = (p.stdout + p.stderr).decode('utf-8', 'replace')
    m = WROTE.search(log)
    announced = (int(m.group(1)), int(m.group(2))) if m else None
    actual = None
    if os.path.exists(dst):
        pg = tifffile.TiffFile(dst).pages[0]
        actual = (pg.shape[1], pg.shape[0])
    return p.returncode, announced, actual, log


def check(tag, expect, code, announced, actual):
    """The two assertions. Returns (ok, note)."""
    if expect == 'ERROR':
        return (code != 0 and actual is None,
                f'exit={code} (want nonzero, no file)')
    if actual is None:
        return False, f'NO FILE WRITTEN (exit {code})'
    if announced is None:
        return False, 'NO `wrote:` LINE -- lattice unannounced'
    if announced != actual:
        return False, f'LOG LIES: announced {announced} actual {actual}'
    if expect is not None and actual != expect:
        return False, f'WRONG LATTICE: got {actual} want {expect}'
    return True, f'{actual} announced and actual agree'


def main():
    print('=== output lattice matrix, one binary, foam, --limit 8 ===\n')
    print(f'{"case":<20}{"flags":<28}{"exit":>5}{"announced":>14}{"actual":>14}  result')
    print('-' * 100)
    results = {}
    npass = nfail = ninfo = 0
    for tag, flags, expect in CASES:
        code, ann, act, log = render(tag, flags)
        ok, note = check(tag, expect, code, ann, act)
        results[tag] = (code, ann, act)
        if expect is None:
            ninfo += 1
            verdict = f'MEASURED (no documented expectation): {note}'
        elif ok:
            npass += 1
            verdict = f'PASS  {note}'
        else:
            nfail += 1
            verdict = f'** FAIL ** {note}'
        print(f'{tag:<20}{" ".join(flags) or "(none)":<28}{code:>5}'
              f'{str(ann):>14}{str(act):>14}  {verdict}')
    print(f'\nPARTITION: {npass} pass + {nfail} fail + {ninfo} measured-only '
          f'= {len(CASES)} cases')

    # ---- COMMISSIONING: the checker must convict, not merely acquit ---------
    print('\n=== commissioning the checker (planted mismatches must be caught) ===')
    plants = [
        ('P1 log lies (announced != actual)', 'default', (PLANE_W, PLANE_H),
         0, (PLANE_W, PLANE_H), (FULL_W, FULL_H)),
        ('P2 silently halved output',         'demosaic', (FULL_W, FULL_H),
         0, (PLANE_W, PLANE_H), (PLANE_W, PLANE_H)),
        ('P3 lattice unannounced',            'default', (PLANE_W, PLANE_H),
         0, None, (PLANE_W, PLANE_H)),
        ('P4 error case silently succeeded',  'x', 'ERROR',
         0, (FULL_W, FULL_H), (FULL_W, FULL_H)),
    ]
    caught = 0
    for name, _t, expect, code, ann, act in plants:
        ok, note = check('plant', expect, code, ann, act)
        if not ok:
            caught += 1
        print(f'  {"CAUGHT" if not ok else "** MISSED **":<14}{name:<38}{note}')
    # negative control: the checker must ACQUIT a correct case, or it convicts all
    ok, note = check('neg', (FULL_W, FULL_H), 0, (FULL_W, FULL_H), (FULL_W, FULL_H))
    print(f'  {"ACQUIT" if ok else "** FALSE CONVICTION **":<14}'
          f'{"N1 correct render must not be flagged":<38}{note}')
    print(f'\n  commissioning: {caught}/{len(plants)} planted defects caught, '
          f'negative control {"acquitted" if ok else "FAILED"}')
    return 0 if (nfail == 0 and caught == len(plants) and ok) else 1


if __name__ == '__main__':
    sys.exit(main())
