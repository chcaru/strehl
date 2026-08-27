# V-H2H2 -- THE `--linear-srgb` LATTICE AUDIT.
#
# THE QUESTION.  `--srgb` implies `--demosaic`; `--linear-srgb` does NOT.
# `--linear-srgb` is what `strehl stack --help` calls "THE MODE TO MEASURE IN".
# So a measurement taken with `--linear-srgb` alone is taken at HALF sensor
# resolution -- and the Nyquist frequency itself moves.  Every spatial-frequency
# quantity in this project is defined against a lattice.  Did this bite a
# published number?
#
# WHY A NAIVE GREP IS NOT ENOUGH.  Both flags are frequently on DIFFERENT
# SOURCE LINES of the same command:
#
#     & $exe stack $src --out $dst --merge pyramid --pyramid-gate 4.5 `
#       --linear-srgb --demosaic 2>&1 | Out-File ...
#
# A line-oriented search reports the first line as "--linear-srgb without
# --demosaic" and convicts a site that is correct.  This reconstructs LOGICAL
# commands first: PowerShell backtick continuations are joined, and Python
# statements are joined while bracket depth is unbalanced.
#
# AND A STATIC READ IS STILL NOT EVIDENCE.  The owner's instruction is explicit:
# the resulting lattice must be MEASURED FROM THE FILE, not inferred from the
# flags.  Static parsing locates the sites; `lattice_scan.py` measures them.
# This lane has already published one all-clear that rested on a filename.
#
# PARTITION.  Every occurrence lands in exactly one bucket and the buckets sum
# to the number of occurrences found.  A skipped site must never read as a
# clean one.

import os, re, sys, collections

ROOT = r'C:\dev\blog\death-of-software\projects\strehl'
FLAG = '--linear-srgb'
DEMO = '--demosaic'

RUNS_SH = re.compile(r'(\$\w+|strehl(\.exe)?)\s+stack\b')
RUNS_PY = re.compile(r"(subprocess|check_call|check_output|Popen)")
RUNS_PY_ARG = re.compile(r"""['"]stack['"]""")


def runs(ll):
    """Does this logical line actually invoke `strehl stack`?"""
    return bool(RUNS_SH.search(ll)) or bool(
        RUNS_PY.search(ll) and RUNS_PY_ARG.search(ll))


# ...but that still admits three kinds of TEXT that merely quote a command.
# Each of these was a false conviction in the first run of this audit:
#   a comment quoting the help text      (linsrgb_audit.py's own header)
#   a log/label string holding a command ("invocation : $exe stack ...")
#   a docstring citing `strehl stack --help`
IS_COMMENT = re.compile(r'^\s*(#|//|--\s)')
IS_STRING_FIRST = re.compile(r'^\s*["\']')
CITES_HELP = re.compile(r'--help')


def logical_lines_ps1(text):
    """Join PowerShell backtick continuations into logical commands."""
    out, buf, start = [], '', None
    for i, ln in enumerate(text.splitlines(), 1):
        if start is None:
            start = i
        s = ln.rstrip()
        if s.endswith('`'):
            buf += s[:-1] + ' '
            continue
        out.append((start, buf + s))
        buf, start = '', None
    if buf:
        out.append((start or 1, buf))
    return out


def logical_lines_py(text):
    """Join Python statements while bracket depth is unbalanced."""
    out, buf, start, depth = [], '', None, 0
    for i, ln in enumerate(text.splitlines(), 1):
        if start is None:
            start = i
        buf += ln + ' '
        # crude but adequate: ignore brackets inside quotes is not attempted,
        # and the failure mode is OVER-joining, which is conservative here --
        # it can only make a site look MORE like it has --demosaic, so any
        # conviction this produces is a floor, not a ceiling.
        depth += ln.count('(') + ln.count('[') - ln.count(')') - ln.count(']')
        if depth <= 0:
            out.append((start, buf))
            buf, start, depth = '', None, 0
    if buf:
        out.append((start or 1, buf))
    return out


def scan():
    rows = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in ('.git', 'target', 'node_modules')]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in ('.ps1', '.py', '.md', '.rs', '.tsv', '.txt'):
                continue
            p = os.path.join(dirpath, fn)
            try:
                t = open(p, encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            if FLAG not in t:
                continue
            rel = os.path.relpath(p, ROOT)
            lls = logical_lines_ps1(t) if ext == '.ps1' else logical_lines_py(t)
            for lineno, ll in lls:
                if FLAG not in ll:
                    continue
                if ext in ('.md', '.rs', '.tsv', '.txt'):
                    kind = 'doc'
                elif IS_COMMENT.search(ll) or IS_STRING_FIRST.search(ll) \
                        or CITES_HELP.search(ll):
                    kind = 'text'
                elif not runs(ll):
                    kind = 'doc'
                else:
                    kind = 'invocation'
                rows.append(dict(file=rel, line=lineno, ext=ext,
                                 demo=DEMO in ll, kind=kind,
                                 snip=re.sub(r'\s+', ' ', ll).strip()[:150]))
    return rows


def main():
    rows = scan()
    buckets = collections.defaultdict(list)
    for r in rows:
        if r['kind'] == 'doc':
            buckets['DOC (prose, .md/.rs, non-command)'].append(r)
        elif r['kind'] == 'text':
            buckets['TEXT (comment / label / help quote)'].append(r)
        elif r['demo']:
            buckets['INVOCATION + --demosaic (full res)'].append(r)
        else:
            buckets['INVOCATION, NO --demosaic (HALF RES)'].append(r)

    print(f'=== `{FLAG}` occurrences, logical commands, under {ROOT} ===\n')
    for k in ('INVOCATION, NO --demosaic (HALF RES)',
              'INVOCATION + --demosaic (full res)',
              'TEXT (comment / label / help quote)',
              'DOC (prose, .md/.rs, non-command)'):
        v = buckets[k]
        print(f'--- {k}: {len(v)} ---')
        if k.startswith('INVOCATION, NO'):
            for r in sorted(v, key=lambda r: r['file']):
                print(f'    {r["file"]}:{r["line"]}')
                print(f'        {r["snip"]}')
        elif k.startswith('INVOCATION +'):
            for r in sorted(v, key=lambda r: r['file']):
                print(f'    {r["file"]}:{r["line"]}')
        elif k.startswith('TEXT'):
            for r in sorted(v, key=lambda r: r['file']):
                print(f'    {r["file"]}:{r["line"]}')
        else:
            files = sorted({r['file'] for r in v})
            print(f'    {len(files)} file(s): ' + ', '.join(files[:8]) +
                  (' ...' if len(files) > 8 else ''))
        print()

    tot = sum(len(v) for v in buckets.values())
    print('PARTITION: ' + ' + '.join(str(len(buckets[k])) for k in buckets) +
          f' = {tot} occurrences (found {len(rows)})')
    assert tot == len(rows), 'PARTITION DOES NOT SUM'

    # --- COMMISSIONING: the audit must be able to CONVICT -------------------
    print('\n=== commissioning: can this audit see a half-res invocation? ===')
    plants = [
        ('P1 bare --linear-srgb, one line',
         "& $exe stack $src --out $d --linear-srgb", '.ps1', True),
        ('P2 --linear-srgb --demosaic, one line',
         "& $exe stack $src --out $d --linear-srgb --demosaic", '.ps1', False),
        ('P3 flags split by backtick continuation',
         "& $exe stack $src --out $d `\n  --linear-srgb --demosaic", '.ps1', False),
        ('P4 backtick split, demosaic ABSENT',
         "& $exe stack $src --out $d `\n  --linear-srgb --merge pyramid", '.ps1', True),
        ('P5 python list split across lines',
         "p = subprocess.run([EXE, 'stack', src,\n  '--linear-srgb', '--demosaic'])", '.py', False),
        ('P6 python list, demosaic ABSENT',
         "p = subprocess.run([EXE, 'stack', src,\n  '--linear-srgb'])", '.py', True),
        # The four false convictions the first run of this audit made. Kept as
        # arms: a repair that is not pinned by a test regresses.
        ('P7 comment quoting the help text',
         "# `--linear-srgb` is what `strehl stack --help` calls the mode", '.py', False),
        ('P8 log string holding a command',
         '"invocation : $exe stack $src --linear-srgb -o $out",', '.ps1', False),
        ('P9 label naming a lattice',
         'b = edgechroma(path, "--linear-srgb (BINNED, NO demosaic)", 2.0)', '.py', False),
        ('P10 docstring citing --help',
         "- `strehl stack --help` on `--linear-srgb`: THE MODE TO MEASURE IN", '.py', False),
    ]
    caught = 0
    for name, src, ext, want_convict in plants:
        lls = logical_lines_ps1(src) if ext == '.ps1' else logical_lines_py(src)
        hit = [ll for _, ll in lls if FLAG in ll]
        convicted = bool(hit) and not any(DEMO in ll for ll in hit) \
            and any(runs(ll) for ll in hit) \
            and not any(IS_COMMENT.search(ll) or IS_STRING_FIRST.search(ll)
                        or CITES_HELP.search(ll) for ll in hit)
        ok = (convicted == want_convict)
        caught += ok
        verdict = 'CONVICT' if convicted else 'acquit'
        print(f'  {"OK " if ok else "**FAIL**"}  {name:<44} -> {verdict}'
              f'   (wanted {"CONVICT" if want_convict else "acquit"})')
    print(f'\n  commissioning: {caught}/{len(plants)}')
    print('  P3/P5 are the load-bearing arms: a line-oriented grep FAILS both,')
    print('  convicting correct sites whose flags span a continuation.')
    print('  P7-P10 are the FALSE CONVICTIONS this audit made on its first run,')
    print('  kept as arms so the repair cannot silently regress.')
    return 0 if caught == len(plants) else 1


if __name__ == '__main__':
    sys.exit(main())
