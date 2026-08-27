# V-H2H2 -- WOULD MAKING `--linear-srgb` IMPLY `--demosaic` MOVE A BYTE FREEZE?
#
# READ-ONLY. `crates/strehl-cli/tests/byte-freezes.tsv` is ORCH-owned and is
# not edited here.
#
# The freeze registry pins exact output bytes for a set of recorded
# invocations. A flag-semantics change moves a freeze if and only if some
# frozen row's invocation would render differently under the new semantics.
# That is decidable from the registry itself: a row is affected only if it
# passes `--linear-srgb` WITHOUT `--demosaic`.
#
# The byte COUNT is an independent, arithmetic cross-check that needs no
# column parsing at all: a binned 3516x2344 RGB16 frame is
#   3516 * 2344 * 3 * 2 = 49,449,024 payload bytes,
# and a full-resolution 7032x4688 one is exactly 4x that. So the file size
# alone says which lattice each frozen row is on.

import csv, os, sys, collections

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
TSV = r'C:\dev\blog\death-of-software\projects\strehl\crates\strehl-cli\tests\byte-freezes.tsv'

BINNED_PAYLOAD = 3516 * 2344 * 3 * 2
FULL_PAYLOAD = 7032 * 4688 * 3 * 2


def lattice_from_bytes(n):
    """TIFF adds a small header/IFD, so allow a slack window."""
    for label, payload in (('BINNED', BINNED_PAYLOAD), ('FULL', FULL_PAYLOAD),
                           ('BINNED-3520', 3520 * 2344 * 3 * 2),
                           ('FULL-7040', 7040 * 4688 * 3 * 2)):
        if 0 <= n - payload < 20000:
            return label
    return f'UNKNOWN({n})'


def main():
    with open(TSV, encoding='utf-8', errors='replace', newline='') as f:
        rows = list(csv.reader(f, delimiter='\t'))
    # The registry opens with a long `#` prose block. Skip comments and blanks,
    # then the FIRST remaining row is the verbatim header.
    live = [r for r in rows if r and r[0].strip()
            and not r[0].lstrip().startswith('#')]
    header, data = live[0], live[1:]
    print(f'registry: {len(data)} data rows, {len(header)} columns')
    print(f'columns : {header}\n')

    # Which column holds the byte count? Find it by content, not by name.
    bcol = None
    for i in range(len(header)):
        vals = [r[i] for r in data if i < len(r)]
        if vals and all(v.isdigit() and len(v) > 6 for v in vals):
            bcol = i
            break
    assert bcol is not None, 'no byte-count column found'
    print(f'byte-count column located by content: index {bcol} '
          f'("{header[bcol]}")\n')

    lat = collections.Counter()
    for r in data:
        lat[lattice_from_bytes(int(r[bcol]))] += 1
    print('=== lattice of every frozen row, from its byte count ===')
    for k, v in sorted(lat.items()):
        print(f'    {k:<14} {v}')
    print(f'    PARTITION: {sum(lat.values())} = {len(data)} rows\n')

    # Does any frozen row pass --linear-srgb WITHOUT --demosaic?
    # Search only the FLAG-BEARING columns, never the free-text note, or a row
    # whose NOTE discusses demosaic would acquit itself by talking about it.
    note_col = max(range(len(header)), key=lambda i:
                   max((len(r[i]) for r in data if i < len(r)), default=0))
    print(f'free-text note column excluded from the flag search: index '
          f'{note_col} ("{header[note_col]}")\n')
    affected = []
    for r in data:
        fields = [v for i, v in enumerate(r) if i != note_col]
        joined = ' '.join(fields)
        if '--linear-srgb' in joined and '--demosaic' not in joined:
            affected.append(r[0])
    print('=== rows that pass --linear-srgb WITHOUT --demosaic ===')
    print(f'    {len(affected)}' + (': ' + ', '.join(affected) if affected else
                                    '  -- none. No freeze moves.'))

    # --- COMMISSIONING ------------------------------------------------------
    print('\n=== commissioning ===')
    cases = [(49450019, 'BINNED'), (49449024, 'BINNED'),
             (197796096, 'FULL'), (197797000, 'FULL'),
             (49505280, 'BINNED-3520'), (12345, 'UNKNOWN(12345)')]
    ok = sum(lattice_from_bytes(n) == w for n, w in cases)
    for n, w in cases:
        g = lattice_from_bytes(n)
        print(f'  {"OK " if g == w else "**FAIL**"}  {n:>10} -> {g:<14} (wanted {w})')

    # The flag search must be able to CONVICT, and must not be fooled by a note.
    plant_hit = ['r1', 'a', '--linear-srgb --gate 4.0', 'note mentions nothing']
    plant_ok = ['r2', 'a', '--linear-srgb --demosaic', 'note']
    plant_note = ['r3', 'a', '--linear-srgb', 'this note discusses --demosaic at length']
    def conv(row, ncol):
        j = ' '.join(v for i, v in enumerate(row) if i != ncol)
        return '--linear-srgb' in j and '--demosaic' not in j
    r1, r2, r3 = conv(plant_hit, 3), conv(plant_ok, 3), conv(plant_note, 3)
    print(f'  {"OK " if r1 else "**FAIL**"}  planted affected row          -> '
          f'{"CONVICT" if r1 else "acquit"} (wanted CONVICT)')
    print(f'  {"OK " if not r2 else "**FAIL**"}  planted safe row              -> '
          f'{"CONVICT" if r2 else "acquit"} (wanted acquit)')
    print(f'  {"OK " if r3 else "**FAIL**"}  affected row w/ chatty note   -> '
          f'{"CONVICT" if r3 else "acquit"} (wanted CONVICT -- the note must not acquit it)')
    total = ok + r1 + (not r2) + r3
    print(f'\n  commissioning: {total}/{len(cases) + 3}')
    return 0 if total == len(cases) + 3 else 1


if __name__ == '__main__':
    sys.exit(main())
