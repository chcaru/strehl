"""Run over SSH as root after releasing the app's camera; never retry a shutter."""
from pathlib import Path
import ctypes
import ctypes.util
import hashlib
import http.client
import json
import select
import subprocess
import threading
import time
from urllib.parse import urlparse

cfg = json.loads(Path('/etc/strehl-capture/headless.json').read_text())
root = Path(cfg['transfer']['ram_directory'])
assert not list(root.iterdir()), 'Preserve existing unsent files'
probe = root / 'throughput-probe'
probe.mkdir()
run = 'stack-throughput-' + str(time.time_ns() // 1000000)
endpoint = urlparse(cfg['transfer']['receiver'])
http = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=90)
auth = {'Authorization': 'Bearer ' + cfg['transfer']['key']}

def request(method, path, body=None, headers=None):
    http.request(method, path, body=body, headers=auth | (headers or {}))
    response = http.getresponse()
    result = json.loads(response.read())
    assert response.status == 200 and result['ok'], (response.status, result)
    return result

request('POST', '/api/runs/' + run)
bridge = subprocess.Popen(['/opt/strehl-capture/strehl-sony-control', 'serve-host', str(probe)],
                          cwd='/opt/strehl-capture', stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
def receive(timeout=35):
    assert select.select([bridge.stdout], [], [], timeout)[0], 'Bridge response timeout; inspect RAM'
    data = json.loads(bridge.stdout.readline())
    assert data['ok'], data
    return data

def command(text):
    started = time.monotonic()
    bridge.stdin.write(text.replace(' ', '\t') + '\n'); bridge.stdin.flush()
    value = receive(125 if text.startswith('capture') else 35)
    return value, time.monotonic() - started

module_was_loaded = Path('/sys/module/usbmon').exists()
trace = None
trace_thread = None
trace_rows = []
results = {'run': run, 'frames': [], 'load_before': Path('/proc/loadavg').read_text().strip(),
           'bridge_sha256': hashlib.sha256(Path('/opt/strehl-capture/strehl-sony-control').read_bytes()).hexdigest()}
def trace_reader():
    for line in trace.stdout:
        fields = line.split()
        if len(fields) >= 6 and fields[2] in ('S', 'C') and fields[3].startswith('Bi:'):
            # Retain only URB metadata; discard every payload byte.
            address = fields[3].split(':')
            if int(address[1]) == bus and int(address[2]) == device:
                trace_rows.append({'tag': fields[0], 'event': fields[2], 'status': fields[4],
                                   'us': int(fields[1]), 'bytes': int(fields[5]), 'endpoint': int(address[3])})

def stop_trace():
    global trace, trace_thread
    if trace is not None:
        trace.terminate(); trace.wait(timeout=5); trace_thread.join(timeout=5)
        assert not trace_thread.is_alive()
        trace = None

def compress_probe(data):
    lib = ctypes.CDLL(ctypes.util.find_library('zstd'))
    lib.ZSTD_compressBound.argtypes = [ctypes.c_size_t]; lib.ZSTD_compressBound.restype = ctypes.c_size_t
    lib.ZSTD_compress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    lib.ZSTD_compress.restype = ctypes.c_size_t
    lib.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
    lib.ZSTD_decompress.restype = ctypes.c_size_t
    lib.ZSTD_isError.argtypes = [ctypes.c_size_t]; lib.ZSTD_isError.restype = ctypes.c_uint
    source = ctypes.create_string_buffer(data)
    packed = ctypes.create_string_buffer(lib.ZSTD_compressBound(len(data)))
    decoded = ctypes.create_string_buffer(len(data))
    rows = []
    for level in [1, 3]:
        t = time.monotonic()
        count = lib.ZSTD_compress(packed, len(packed), source, len(data), level)
        elapsed = time.monotonic() - t
        assert not lib.ZSTD_isError(count)
        n = lib.ZSTD_decompress(decoded, len(data), packed, count)
        assert n == len(data) and decoded.raw == data
        rows.append({'level': level, 'input_bytes': len(data), 'compressed_bytes': count,
                     'seconds': elapsed, 'MB_per_second': len(data) / elapsed / 1e6,
                     'fraction_saved': 1 - count / len(data), 'roundtrip_exact': True})
    return rows

try:
    results['hello'] = receive()
    for attempt in range(50):
        status, _ = command('status')
        if all('value' in status['properties'][x] for x in ['DriveMode', 'FocusMode', 'FileType']): break
        time.sleep(.1)
    else: raise RuntimeError('SDK property cache not ready')
    for key, value in [('StillImageStoreDestination', 1), ('DriveMode', 1), ('FocusMode', 1),
                       ('FileType', 2), ('RAW_FileCompressionType', 5)]:
        command(f'set {key} {value}')
    command('liveview 1')
    status, _ = command('status')
    results['settings'] = status
    position = status['properties']['FocusPositionCurrentValue']['value']
    assert position < 65000
    cameras = [p for p in Path('/sys/bus/usb/devices').iterdir()
               if (p/'idVendor').exists() and (p/'idVendor').read_text().strip() == '054c'
               and (p/'busnum').exists()]
    assert len(cameras) == 1
    bus = int((cameras[0]/'busnum').read_text()); device = int((cameras[0]/'devnum').read_text())
    subprocess.run(['/usr/sbin/modprobe', 'usbmon'], check=True)
    for index, settle in enumerate([500, 100, 100, 500]):
        focus, focus_seconds = command(f'focus {position+index+1} {settle}')
        if focus['readback'] != focus['requested']:
            results['focus_rejection'] = {'response': focus, 'seconds': focus_seconds}
            raise RuntimeError('Focus readback mismatch; no diagnostic exposure')
        live_view = index in (0, 3)
        command(f'liveview {int(live_view)}')
        time.sleep(.2)
        tracing = True
        trace_rows = []
        if tracing:
            trace = subprocess.Popen(['cat', f'/sys/kernel/debug/usb/usbmon/{bus}u'],
                                     stdout=subprocess.PIPE, text=True, bufsize=1)
            trace_thread = threading.Thread(target=trace_reader); trace_thread.start()
            time.sleep(.1)
        capture, seconds = command('capture-host 120')
        stop_trace()
        path = Path(capture['path']).resolve()
        assert path.parent == probe.resolve() and path.suffix.upper() == '.ARW'
        data = path.read_bytes(); assert len(data) == capture['bytes']
        digest = hashlib.sha256(data).hexdigest()
        submitted = {}
        large = []
        for item in trace_rows:
            if item['event'] == 'S':
                submitted[item['tag']] = item
            elif item['status'] == '0' and item['bytes'] >= 1024*1024:
                start = submitted.pop(item['tag'], None)
                assert start is not None, 'Missing USB submission; timing is incomplete'
                large.append({'start_us': start['us'], 'end_us': item['us'], 'bytes': item['bytes']})
        usb_span = (large[-1]['end_us'] - large[0]['start_us']) / 1e6 if large else None
        row = {'ordinal': index, 'focus': focus, 'focus_seconds': focus_seconds,
               'capture_seconds': seconds, 'capture': capture, 'tracing': tracing, 'live_view': live_view,
               'usb_large_requests': large,
               'usb_bulk_completions': trace_rows, 'usb_large_bytes': sum(r['bytes'] for r in large),
               'usb_large_span_seconds': usb_span, 'sha256': digest}
        receipt = request('PUT', f'/api/files/{run}/frame-{index+1:06}.ARW', data,
                          {'x-content-sha256': digest, 'Content-Length': str(len(data))})
        assert receipt['durable'] and receipt['sha256'] == digest and receipt['bytes'] == len(data)
        row['receipt'] = receipt
        if index == 0:
            results['compression'] = compress_probe(data)
        path.unlink()  # only after the exact PC durable receipt
        results['frames'].append(row)
        print(json.dumps({'progress': index+1, 'capture_seconds': seconds, 'focus_seconds': focus_seconds,
                          'usb_span': usb_span, 'usb_bytes': row['usb_large_bytes']}), flush=True)
    results['restore'], _ = command('quit')
    assert results['restore']['restored']
    bridge.wait(timeout=10)
    assert bridge.returncode == 0
finally:
    stop_trace()
    if bridge.poll() is None:
        bridge.stdin.close()  # EOF releases the owned session; never another shutter
        bridge.wait(timeout=15)
    if not module_was_loaded:
        subprocess.run(['/usr/sbin/modprobe', '-r', 'usbmon'], check=True)
    if not list(probe.iterdir()): probe.rmdir()
    results['remaining_ram_files'] = [p.name for p in probe.glob('*')] if probe.exists() else []
    print(json.dumps({'result': results}), flush=True)
