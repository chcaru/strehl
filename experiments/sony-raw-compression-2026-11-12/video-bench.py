"""FFV1 lossless high-bit-depth intra-frame baseline; never convert to RGB.

Each original CFA phase is rearranged into a contiguous grayscale panel.
Only a single sensor image is resident per encode/decode operation.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
import imagecodecs as ic
from bench import OUT, load

FFMPEG = next((Path.home() / 'AppData/Local/Microsoft/WinGet/Packages').glob(
    'Gyan.FFmpeg_*/ffmpeg-*-full_build/bin/ffmpeg.exe'))


def roundtrip(a, name):
    path = OUT / 'ffv1' / (name + '.mkv')
    path.parent.mkdir(exist_ok=True)
    h, w = a.shape
    assert h % 2 == 0 and w % 2 == 0
    start = time.perf_counter()
    packed = a.reshape(h // 2, 2, w // 2, 2).transpose(1, 3, 0, 2).copy().reshape(h * 2, w // 2)
    args = [str(FFMPEG), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
            '-f', 'rawvideo', '-pixel_format', 'gray16le', '-video_size', f'{w//2}x{h*2}',
            '-framerate', '1', '-i', 'pipe:0', '-frames:v', '1', '-c:v', 'ffv1',
            '-level', '3', '-coder', '1', '-context', '1', '-slices', '16',
            '-slicecrc', '1', '-threads', '4', '-f', 'matroska', str(path)]
    p = subprocess.run(args, input=packed.tobytes(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    assert p.returncode == 0, p.stderr.decode(errors='replace')
    enc = time.perf_counter() - start
    start = time.perf_counter()
    p = subprocess.run([str(FFMPEG), '-hide_banner', '-loglevel', 'error', '-nostdin',
                        '-threads', '4', '-i', str(path), '-f', 'rawvideo',
                        '-pix_fmt', 'gray16le', 'pipe:1'], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=180)
    assert p.returncode == 0, p.stderr.decode(errors='replace')
    assert len(p.stdout) == a.nbytes
    b = np.frombuffer(p.stdout, dtype='<u2').reshape(2, 2, h//2, w//2).transpose(2, 0, 3, 1).copy().reshape(h, w)
    assert np.array_equal(a, b)
    return {'codec_bytes': path.stat().st_size, 'encode_s_including_process': enc,
            'decode_s_including_process': time.perf_counter() - start,
            'exact_cfa': True, 'workers': 4, 'command': args}


def main():
    version = subprocess.run([str(FFMPEG), '-version'], capture_output=True, text=True, check=True)
    print(json.dumps({'ffmpeg_version': version.stdout.splitlines()[0]}), flush=True)
    rng = np.random.default_rng(119)
    test = rng.integers(0, 65536, (256, 256), dtype='u2')
    test[0, :2] = [0, 65535]
    print(json.dumps({'full16bit_control': roundtrip(test, 'control')}), flush=True)
    for group in ['4', '16']:
        file = sorted((OUT/'inputs'/('pixel-shift-'+group)).glob('*.ARW'))[0]
        data, a, off = load(file)
        side = data[:off] + data[off+a.nbytes:]
        extra = ic.zstd_encode(side, level=1)
        assert ic.zstd_decode(extra) == side
        result = roundtrip(a, file.stem)
        result.update(group=group, file=file.name, input_bytes=len(data),
                      encoded_bytes=result['codec_bytes']+len(extra)+512,
                      sha256=hashlib.sha256(data).hexdigest(), exact_side=True,
                      descriptor_budget=512)
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
