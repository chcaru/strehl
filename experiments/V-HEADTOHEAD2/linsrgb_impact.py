# V-H2H2 -- DOES A HALF-RES SITE CARRY A FREQUENCY-DEPENDENT PUBLISHED NUMBER?
#
# The artifacts from the half-res `--linear-srgb` sites were cleaned from this
# machine, so their lattice cannot be measured from a file. ABSENCE OF FILES IS
# NOT AN ALL-CLEAR -- so the question is re-posed as one the surviving evidence
# CAN answer:
#
#   (a) Do the affected lanes publish any quantity with a SPATIAL SCALE in it?
#       A DN level or a ratio between two arms on the SAME lattice survives
#       binning. Anything defined against Nyquist does not, because binning
#       MOVES NYQUIST.
#   (b) Do both arms of each comparison carry the SAME flags? A comparison
#       between two renders on one lattice is internally valid whatever that
#       lattice is. A comparison ACROSS lattices is not.
#
# (b) is the load-bearing one and it is checkable from the scripts, which are
# committed even though their outputs are not.

import os, re, sys, collections

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r'C:\dev\blog\death-of-software\projects\strehl'

# Lanes whose scripts invoke `--linear-srgb` with NO `--demosaic`.
SUSPECT_DOCS = ['BUILD-HALO.md', 'BUILD-HIGHLIGHT.md']

# Terms that only make sense against a lattice. If a lane publishes these, a
# silent halving changes the published number.
FREQ = re.compile(
    r'cyc/px|cyc/output|cycles?/pixel|nyquist|\bMTF\b|SFR|slanted[- ]edge|'
    r'lp/mm|line pairs|band power|spatial frequency|top[- ]octave|'
    r'10-90|edge width|PSF|modulation transfer', re.I)

# Terms that are lattice-robust: levels, ratios, counts.
LEVEL = re.compile(r'\bDN\b|percent|ratio|fraction|count', re.I)


def scan_doc(name):
    p = os.path.join(ROOT, 'docs', 'research', name)
    if not os.path.exists(p):
        return None
    t = open(p, encoding='utf-8', errors='replace').read()
    lines = t.splitlines()
    hits = [(i + 1, ln.strip()[:130]) for i, ln in enumerate(lines) if FREQ.search(ln)]
    return dict(path=p, nlines=len(lines), freq=hits,
                nlevel=sum(1 for ln in lines if LEVEL.search(ln)))


def classify_flags(s):
    """Lattice implied by a flag string. --srgb implies --demosaic; --linear-srgb does not."""
    if '--demosaic' in s:
        return 'FULL'
    if '--binned' in s:
        return 'BINNED'
    if '--srgb' in s and '--linear-srgb' not in s:
        return 'FULL'          # --srgb turns demosaic on by default (M95)
    return 'BINNED'            # bare, or --linear-srgb alone


ARM = re.compile(r"n\s*=\s*'([^']+)'[^\n]*?a\s*=\s*@\(([^)]*)\)")
ARM2 = re.compile(r"a\s*=\s*@\(([^)]*)\)[^\n]*?n\s*=\s*'([^']+)'")


def arms_share_flags(script_dir):
    """Do all strehl renders in a lane use the same lattice?

    REACH REPAIR.  The first version of this only read logical lines matching
    `$exe stack`, and reported BUILD-HIGHLIGHT as 1 invocation on a single
    lattice.  That was WRONG: BUILD-HIGHLIGHT defines its arms in HASHTABLE
    TABLES -- `@{ n = 'L2-stack-binned'; a = @('--linear-srgb') }` -- so the
    flags never appear on an invocation line at all.  An instrument that only
    ever returned "consistent" was returning it because it could not see.
    """
    inv = collections.Counter()
    sites = []
    base = os.path.join(ROOT, 'experiments', script_dir)
    for dp, dn, fns in os.walk(base):
        for fn in fns:
            if not fn.endswith('.ps1'):
                continue
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, ROOT)
            txt = open(p, encoding='utf-8', errors='replace').read()
            seen = set()
            # (1) named arms declared in hashtable tables
            for rx, order in ((ARM, 'na'), (ARM2, 'an')):
                for m in rx.finditer(txt):
                    name, flags = (m.group(1), m.group(2)) if order == 'na' \
                        else (m.group(2), m.group(1))
                    if '--' not in flags:
                        continue
                    k = classify_flags(flags)
                    inv[k] += 1
                    sites.append((rel, name, k))
                    seen.add(name)
            # (2) direct invocations, backtick continuations joined
            joined, buf = [], ''
            for ln in txt.splitlines():
                s = ln.rstrip()
                if s.endswith('`'):
                    buf += s[:-1] + ' '
                    continue
                joined.append(buf + s)
                buf = ''
            for ll in joined:
                if not re.search(r'\$\w+\s+stack\b|strehl(\.exe)?\s+stack\b', ll):
                    continue
                st = ll.strip()
                if st.startswith('#') or st.startswith('"') or st.startswith("'"):
                    continue
                if '--' not in ll:
                    continue
                k = classify_flags(ll)
                inv[k] += 1
                sites.append((rel, '(inline)', k))
    return inv, sites


def main():
    print('=== (a) do the affected lanes publish a frequency-dependent number? ===\n')
    for name in SUSPECT_DOCS:
        d = scan_doc(name)
        if d is None:
            print(f'  {name}: DOC ABSENT -- cannot assess\n')
            continue
        print(f'  {name}  ({d["nlines"]} lines, {d["nlevel"]} lines with a level/ratio term)')
        print(f'    lines with a lattice-dependent term: {len(d["freq"])}')
        for ln, s in d['freq'][:12]:
            print(f'      {ln}: {s}')
        if len(d['freq']) > 12:
            print(f'      ... and {len(d["freq"]) - 12} more')
        print()

    print('=== (b) do both arms of each comparison share a lattice? ===\n')
    for lane in ('BUILD-HALO', 'BUILD-HIGHLIGHT'):
        inv, sites = arms_share_flags(lane)
        print(f'  {lane}: {dict(inv)}')
        if len(inv) <= 1:
            print(f'    -> ALL {sum(inv.values())} renders share one lattice: '
                  f'comparisons are internally consistent.')
        else:
            print(f'    -> ** MIXED LATTICES ** across {sum(inv.values())} renders:')
            for rel, name, k in sites:
                mark = '  <<<' if k == 'FULL' else ''
                print(f'         {k:<7} {name:<22} {rel}{mark}')
        print()

    # --- COMMISSIONING ------------------------------------------------------
    print('=== commissioning 1: can the FREQ detector see a frequency claim? ===')
    plants = [
        ('a real MTF claim', 'the 10-90% edge width is 5.13 px', True),
        ('a cyc/px band claim', 'band power at 0.30-0.40 cyc/px rose 3.46x', True),
        ('a Nyquist claim', 'plane Nyquist at f = 0.25 cyc/output px', True),
        ('a pure DN level', 'the backdrop sits 4739 DN below its far field', False),
        ('a pure ratio', 'the pyramid wins by a factor of 2.4x', False),
        ('a percentage', 'clips 32% of the frame', False),
    ]
    ok = 0
    for name, text, want in plants:
        got = bool(FREQ.search(text))
        ok += (got == want)
        print(f'  {"OK " if got == want else "**FAIL**"}  {name:<24} '
              f'-> {"FREQ" if got else "level":<6} (wanted {"FREQ" if want else "level"})')
    print(f'\n  commissioning: {ok}/{len(plants)}')
    print('  The three "level" arms are the ones that matter: a detector that')
    print('  flagged every number would make the audit unfalsifiable.')

    # The load-bearing arm. `arms_share_flags` had only ever returned ONE
    # bucket -- and the first version returned it because it COULD NOT SEE
    # table-declared arms, not because the lane was consistent. A "consistent"
    # from a probe never shown to say "mixed" is not a result.
    print('\n=== commissioning 2: can the LATTICE detector say MIXED? ===')
    fcases = [
        ("@('--linear-srgb')",              'BINNED'),
        ("@('--linear-srgb', '--demosaic')", 'FULL'),
        ("@('--srgb')",                     'FULL'),
        ("@('--srgb', '--binned')",         'BINNED'),
        ("stack $d -o $o --gate 4.0",       'BINNED'),
        ("@('--demosaic')",                 'FULL'),
    ]
    ok2 = 0
    for s, want in fcases:
        got = classify_flags(s)
        ok2 += (got == want)
        print(f'  {"OK " if got == want else "**FAIL**"}  {s:<36} -> '
              f'{got:<7} (wanted {want})')
    mixed = collections.Counter([classify_flags("@('--linear-srgb')"),
                                 classify_flags("@('--linear-srgb','--demosaic')")])
    same = collections.Counter([classify_flags("@('--linear-srgb')"),
                                classify_flags("@('--linear-srgb')")])
    print(f'\n  planted MIXED lane -> {dict(mixed)}  '
          f'{"REPORTS MIXED" if len(mixed) > 1 else "** MISSED **"}')
    print(f'  planted SAME  lane -> {dict(same)}   '
          f'{"reports consistent" if len(same) == 1 else "** FALSE ALARM **"}')
    ok2 += (len(mixed) > 1) + (len(same) == 1)
    print(f'\n  commissioning: {ok2}/{len(fcases) + 2}')
    return 0 if (ok == len(plants) and ok2 == len(fcases) + 2) else 1


if __name__ == '__main__':
    sys.exit(main())
