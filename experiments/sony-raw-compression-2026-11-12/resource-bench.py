"""One instrumented replay per format. Fresh outputs; production untouched."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
from wire import receive

spec = importlib.util.spec_from_file_location('pi_runner', Path(__file__).with_name('run-pi.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
OUT, OPTS, DEST = runner.OUT, runner.OPTS, runner.DEST


def main():
    subprocess.run(['scp', *OPTS, str(Path(__file__).with_name('wire.py')),
                    'strehl@10.0.0.187:'+DEST+'/'], check=True)
    current = json.loads((OUT/'current-camera-bench.jsonl').read_text().splitlines()[0])
    source = Path(current['file'])
    subprocess.run(['scp', *OPTS, str(source),
                    'strehl@10.0.0.187:'+DEST+'/current-camera.ARW'], check=True)
    target = OUT/'resource-roundtrips'
    target.mkdir(exist_ok=True)
    for name, remote, sha in [
            ('61mp-cfa', 'DSC01472.ARW', '453154311a136a0bb08efc4e3f0124e6d7fdc0116a5c413893a5c6b101f25c72'),
            ('33mp-camera-lossless', 'current-camera.ARW', current['sha256'])]:
        part = target/(name+'.partial')
        final = target/(name+'.ARW')
        assert not final.exists()
        start = time.perf_counter()
        proc = subprocess.Popen(['ssh', *OPTS, 'strehl@10.0.0.187',
             'python3 '+DEST+'/wire.py send --file '+DEST+'/'+remote+' --mode cfa --workers 4 --stats'],
             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with part.open('wb') as file:
            receipt = receive(proc.stdout, file)
            file.flush()
            os.fsync(file.fileno())
        stats = proc.stderr.read().decode()
        assert proc.wait(timeout=10) == 0, stats
        assert receipt['sha256'] == sha
        part.replace(final)
        duration = time.perf_counter()-start
        assert hashlib.sha256(final.read_bytes()).hexdigest() == sha
        print(json.dumps({'case': name, 'seconds_to_durable': duration,
                          'sender_stats': json.loads(stats), **receipt}), flush=True)


if __name__ == '__main__':
    main()
