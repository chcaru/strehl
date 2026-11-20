"""Run a lab script on the studio Pi with the experimental bridge and save its timestamped log.

  run-lab.py install <local aarch64 binary>     copy the lab bridge to /home/strehl/lab (not /opt)
  run-lab.py run <script.txt> <log.jsonl> [timeout_s]
  run-lab.py remove                              delete /home/strehl/lab

`run` needs the controller disconnected from the camera (rig.py disconnect) and the camera
powered. A script is one bridge command per line, fields separated by spaces (sent as tabs);
`#` lines are comments. `quit` is appended, which restores the camera settings the script saved.
Prints no keys.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import HOST, OPTIONS, state, remote  # noqa: E402
sys.path.insert(0, str(ROOT / 'experiments/sony-edup-2026-11-12'))
from remote import ssh  # noqa: E402

LAB = '/home/strehl/lab'
op = sys.argv[1]
if op == 'install':
    print(remote('import pathlib\npathlib.Path(%r).mkdir(exist_ok=True)\nprint("dir ok")' % LAB))
    subprocess.run(['scp', *OPTIONS, '-o', 'HostKeyAlias=10.0.0.187', sys.argv[2], 'strehl@' + HOST + ':' + LAB + '/strehl-sony-ptp-lab'], check=True)
    print(remote('import os,hashlib\np=%r\nos.chmod(p,0o755)\nprint(hashlib.sha256(open(p,"rb").read()).hexdigest())' % (LAB + '/strehl-sony-ptp-lab')))
elif op == 'remove':
    print(remote('import shutil\nshutil.rmtree(%r, ignore_errors=True)\nprint("removed")' % LAB))
elif op == 'run':
    s = state()
    assert not s['connected'] and not s['busy'], 'disconnect the controller from the camera first'
    lines = [l.strip() for l in pathlib.Path(sys.argv[2]).read_text().splitlines()]
    cmds = ['\t'.join(l.split()) for l in lines if l and not l.startswith('#')]
    timeout = int(sys.argv[4]) if len(sys.argv) > 4 else 120
    program = '''
import subprocess, glob, os
cmds = %r
p = subprocess.run([%r, 'serve-host', '/run/strehl-raw'], input='\\n'.join(cmds) + '\\nquit\\n',
                   capture_output=True, text=True, timeout=%d)
print(p.stdout)
print('#EXIT', p.returncode, p.stderr[-1500:].replace('\\n', ' | '))
left = glob.glob('/run/strehl-raw/lab-*')
for f in left:
    os.remove(f)
print('#LEFTOVER', len(left))
''' % (cmds, LAB + '/strehl-sony-ptp-lab', timeout)
    r = ssh(program, host=HOST, timeout=timeout + 30)
    out = r.stdout
    pathlib.Path(sys.argv[3]).write_bytes(out.replace('\r\n', '\n').encode())
    n = 0
    for line in out.splitlines():
        if line.startswith('#'):
            print(line[:400])
        elif line.strip():
            n += 1
            try:
                v = json.loads(line)
            except ValueError:
                print('??', line[:200])
                continue
            if v.get('ok') is False:
                print('ERROR', line[:300])
    print(n, 'lines ->', sys.argv[3], '| ssh exit', r.returncode, r.stderr[-300:])
else:
    raise SystemExit(__doc__)
