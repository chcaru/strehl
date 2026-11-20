"""What thinning would save on every stack on disk (decision D2: numbers only, nothing deleted).

  python thinning-numbers.py <captures root> <out.txt>

For each run with at least 5 recorded focus positions: its size, `strehl focus-step`'s sharp
width and suggested step, and the planes and bytes a thinning to that step would keep.
Read-only.
"""
import json
import pathlib
import subprocess
import sys
import tempfile

root, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
exe = pathlib.Path(__file__).resolve().parents[2] / 'target/release/strehl.exe'
lines = []
total = saved = 0
for run in sorted(root.iterdir()):
    if not (run / 'events.jsonl').is_file():
        continue
    size = sum(f.stat().st_size for f in run.iterdir() if f.is_file())
    with tempfile.TemporaryDirectory() as t:
        j = pathlib.Path(t) / 'r.json'
        r = subprocess.run([str(exe), 'focus-step', str(run), '--json', str(j)], capture_output=True, text=True)
        if r.returncode != 0 or not j.exists():
            lines.append('%-28s %7.1f GB  not measured: %s' % (run.name, size / 1e9, (r.stderr.strip().splitlines() or ['?'])[-1][:120]))
            continue
        v = json.loads(j.read_text())
    if v['width'] is None:
        lines.append('%-28s %7.1f GB  %3d planes  not measurable (%d tiles)' % (run.name, size / 1e9, v['planes'], v['tiles_measured']))
        continue
    keep = 1.0 / max(1.0, v['oversampling'])
    # Thinning keeps every k-th plane with k the whole factor (never a coarser step than suggested).
    k = max(1, int(v['oversampling'] + 1e-9))
    kept = -(-v['planes'] // k)
    kept_bytes = size * kept / v['planes']
    total += size
    saved += size - kept_bytes
    lines.append('%-28s %7.1f GB  %3d planes at %4.0f  sharp width %5.0f (p10-p90 %4.0f-%4.0f, %5d tiles)  suggested step %3d  -> keep every %d: %3d planes, %6.1f GB, saves %6.1f GB' % (
        run.name, size / 1e9, v['planes'], v['spacing'], v['width'], v['width_p10'], v['width_p90'], v['tiles_measured'],
        v['suggested_step'], k, kept, kept_bytes / 1e9, (size - kept_bytes) / 1e9))
lines.append('measured stacks: %.1f GB; thinning to the suggested step saves %.1f GB' % (total / 1e9, saved / 1e9))
out.write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
