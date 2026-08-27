# V-H2H2 -- MEASURE the lattice of every render produced by a `--linear-srgb`
# site, from the FILE, not from the flags.
#
# The static audit (linsrgb_audit.py) locates candidate sites. It cannot settle
# anything on its own: this lane has already published one all-clear that
# rested on a filename, and the owner's instruction is explicit that the
# resulting lattice be measured from the file.
#
# The discriminator is arithmetic and needs no reference: this camera's CFA
# plane is 3516 or 3520 wide depending on the RAW recording mode, and the
# demosaiced output is exactly twice that. So width <= 3600 is BINNED and
# width >= 7000 is FULL. Anything else is neither and must be reported as
# UNKNOWN rather than forced into a bucket.

import os, sys, collections, tifffile

# Output roots named by the half-res invocation sites found in the static audit.
ROOTS = [
    (r'C:\dev\strehl-out\VETO',        'BUILD-HALO veto/veilz/twomech'),
    (r'C:\dev\strehl-out\BUILD-HALO',  'BUILD-HALO (other)'),
    (r'C:\dev\strehl-out\BUILD-HIGHLIGHT', 'BUILD-HIGHLIGHT h5/l1/l3/m1'),
    (r'C:\dev\strehl-out\V-HIGHLIGHT', 'V-HIGHLIGHT (declares its lattices)'),
]

BINNED_MAX, FULL_MIN = 3600, 7000


def classify(w):
    if w <= BINNED_MAX:
        return 'BINNED'
    if w >= FULL_MIN:
        return 'FULL'
    return 'UNKNOWN'


def main():
    grand = collections.Counter()
    for root, label in ROOTS:
        print(f'=== {label}')
        print(f'    {root}')
        if not os.path.isdir(root):
            print('    (absent -- nothing rendered here on this machine)\n')
            grand['ABSENT ROOT'] += 1
            continue
        found = collections.Counter()
        widths = collections.Counter()
        examples = {}
        nread = nfail = 0
        for dp, dn, fns in os.walk(root):
            for fn in fns:
                if not fn.lower().endswith(('.tif', '.tiff')):
                    continue
                p = os.path.join(dp, fn)
                try:
                    w = tifffile.TiffFile(p).pages[0].shape[1]
                except Exception:
                    nfail += 1
                    continue
                nread += 1
                c = classify(w)
                found[c] += 1
                widths[w] += 1
                examples.setdefault(c, fn)
        if nread == 0 and nfail == 0:
            print('    (no TIFFs)\n')
            continue
        for c in ('BINNED', 'FULL', 'UNKNOWN'):
            if found[c]:
                print(f'    {c:<8} {found[c]:>5}   e.g. {examples[c]}')
                grand[c] += found[c]
        print(f'    widths seen: {dict(widths)}')
        print(f'    PARTITION: {sum(found.values())} classified + {nfail} unreadable '
              f'= {nread + nfail} files\n')
        grand['unreadable'] += nfail

    print('=== GRAND TOTAL ===')
    for k, v in sorted(grand.items()):
        print(f'    {k:<14} {v}')

    # --- COMMISSIONING: the classifier must be able to say BINNED -----------
    print('\n=== commissioning the width classifier ===')
    cases = [(3516, 'BINNED'), (3520, 'BINNED'), (7032, 'FULL'),
             (7040, 'FULL'), (5000, 'UNKNOWN'), (1758, 'BINNED')]
    ok = 0
    for w, want in cases:
        got = classify(w)
        ok += got == want
        print(f'  {"OK " if got == want else "**FAIL**"}  width {w:>5} -> '
              f'{got:<8} (wanted {want})')
    print(f'\n  commissioning: {ok}/{len(cases)}')
    print('  The UNKNOWN bucket is the point: a width that is neither must not')
    print('  be silently rounded into BINNED or FULL.')
    return 0 if ok == len(cases) else 1


if __name__ == '__main__':
    sys.exit(main())
