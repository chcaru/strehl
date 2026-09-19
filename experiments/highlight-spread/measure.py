"""Fixed native-source morphology profiles; no RAW, image warp or quality score."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import struct
import time

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'experiments/quality-september19/vitamin-c-comparator-2/developed'
SCAN = ROOT / 'experiments/quality-september19/vitamin-c-source-highlights/scan-1/receipt.json'
MAP = ROOT / 'experiments/quality-september19/vitamin-c-baseline-1/vitamin-c.warpmap.txt'
PIVOT = np.array([3516.0, 2344.0])
OUTPUT_ORIGIN = np.array([56.0, 38.0])
S_EDGES = np.arange(-24.0, 74.0, 2.0)
T_EDGES = np.array([-12.0, -4.0, 4.0, 12.0])
TARGETS = (
    ('facet-glint', 'facet-edges', (2624, 2906), (-22, 39)),
    ('dark-glint', 'dark-inclusion', (3080, 2150), (22, 53)),
    ('real-structure', 'dark-inclusion', (3240, 2070), (22, 53)),
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parameters(bits):
    if len(bits) != 4 or any(len(v) != 16 for v in bits):
        raise ValueError('four exact f64 transform bit patterns required')
    values = [struct.unpack('>d', bytes.fromhex(v))[0] for v in bits]
    ar, ai, br, bi = values
    if not np.isfinite(values).all() or ar * ar + ai * ai <= 0:
        raise ValueError('finite invertible similarity required')
    return ar, ai, br, bi


def map_output_to_source(x, y, bits):
    ar, ai, br, bi = parameters(bits)
    u = np.asarray(x, dtype=np.float64) + OUTPUT_ORIGIN[0] - PIVOT[0]
    v = np.asarray(y, dtype=np.float64) + OUTPUT_ORIGIN[1] - PIVOT[1]
    return PIVOT[0] + ar * u - ai * v + 2 * br, PIVOT[1] + ai * u + ar * v + 2 * bi


def map_source_to_output(x, y, bits):
    ar, ai, br, bi = parameters(bits)
    u = np.asarray(x, dtype=np.float64) - PIVOT[0] - 2 * br
    v = np.asarray(y, dtype=np.float64) - PIVOT[1] - 2 * bi
    den = ar * ar + ai * ai
    return (PIVOT[0] + (ar * u + ai * v) / den - OUTPUT_ORIGIN[0],
            PIVOT[1] + (-ai * u + ar * v) / den - OUTPUT_ORIGIN[1])


def unit_direction(direction):
    d = np.asarray(direction, dtype=np.float64)
    if d.shape != (2,) or not np.isfinite(d).all() or np.linalg.norm(d) == 0:
        raise ValueError('finite nonzero 2D direction required')
    return d / np.linalg.norm(d)


def bin_profile(rgb16, source_xy, bits, core, direction):
    """Means (3 strips,48 bins,RGB), counts(3,48); no pixel interpolation.

    source_xy is the active-native integer crop origin; integer array indices
    denote pixel centres. Empty bins have NaN means and count zero.
    """
    rgb16 = np.asarray(rgb16)
    if rgb16.dtype != np.uint16 or rgb16.ndim != 3 or rgb16.shape[2] != 3:
        raise ValueError('original RGB16 HxWx3 samples required')
    if len(source_xy) != 2 or len(core) != 2 or not np.isfinite([*source_xy, *core]).all():
        raise ValueError('finite 2D origin/core required')
    d = unit_direction(direction)
    yy, xx = np.indices(rgb16.shape[:2], dtype=np.float64)
    ox, oy = map_source_to_output(xx + source_xy[0], yy + source_xy[1], bits)
    dx, dy = ox - core[0], oy - core[1]
    s, t = dx * d[0] + dy * d[1], -dx * d[1] + dy * d[0]
    use = (s >= -24) & (s < 72) & (t >= -12) & (t < 12)
    sb = np.floor((s[use] + 24) / 2).astype(np.int64)
    tb = np.floor((t[use] + 12) / 8).astype(np.int64)
    ids = tb * 48 + sb
    counts = np.bincount(ids, minlength=144).reshape(3, 48)
    sums = np.zeros((144, 3), dtype=np.float64)
    np.add.at(sums, ids, rgb16[use])
    means = np.full((3, 48, 3), np.nan, dtype=np.float32)
    np.divide(sums.reshape(3, 48, 3), counts[..., None], out=means,
              where=counts[..., None] > 0, casting='unsafe')
    return means, counts


def support_inside(source_xy, shape, bits, core, direction):
    d = unit_direction(direction)
    normal = np.array([-d[1], d[0]])
    for s in [-24.0, 72.0]:
        for t in [-12.0, 12.0]:
            q = np.asarray(core) + s * d + t * normal
            x, y = map_output_to_source(*q, bits)
            if not (source_xy[0] + 2 <= x <= source_xy[0] + shape[1] - 3
                    and source_xy[1] + 2 <= y <= source_xy[1] + shape[0] - 3):
                raise ValueError('fixed transect not fully supported by bound crop')


def figures(out, profiles):
    os.environ.setdefault('MPLCONFIGDIR', str(out / 'matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    extent = [-24, 72, 69.5, -0.5]
    for target, (name, _, core, direction) in enumerate(TARGETS):
        fig, axes = plt.subplots(3, 4, figsize=(14, 8), sharex=True, sharey=True)
        for strip in range(3):
            data = profiles[target, :, strip] / np.float32(65535)
            for ch in range(3):
                plot = axes[strip, ch].imshow(data[:, :, ch], cmap='gray', vmin=0, vmax=1,
                    aspect='auto', extent=extent, interpolation='nearest')
                axes[strip, ch].set_title(f'{"RGB"[ch]} display code')
            axes[strip, 3].imshow(data, aspect='auto', extent=extent, interpolation='nearest')
            axes[strip, 3].set_title('RGB display codes')
            axes[strip, 0].set_ylabel(f't in [{T_EDGES[strip]:g},{T_EDGES[strip+1]:g})\nFrame index')
            for ax in axes[strip]:
                ax.axvline(0, color='cyan', linewidth=0.5, alpha=0.5)
                ax.set_xlabel('Signed native distance from core')
        fig.suptitle(f'{name}: core{core}, direction{direction}\n'
                     'SOURCE MORPHOLOGY ONLY — no physical PSF or output-quality claim')
        fig.subplots_adjust(top=0.87, bottom=0.08, left=0.09, right=0.84, hspace=0.42, wspace=0.18)
        fig.colorbar(plot, cax=fig.add_axes([0.9, 0.22, 0.014, 0.52]), label='Unchanged RGB16 / 65535')
        fig.savefig(out / f'{name}.png', dpi=130)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(HERE) or out.exists():
        raise ValueError('new output directory under highlight-spread required')
    started = time.perf_counter()
    scan = json.loads(SCAN.read_text())
    if sha(MAP) != scan['warpmap_sha256'] or sha(SOURCE / 'receipt.json') != scan['source_receipt_sha256']:
        raise ValueError('held map/export receipt changed')
    maps = {}
    for line in MAP.read_text().splitlines():
        p = line.split()
        if len(p) > 5 and p[0].isdigit():
            if p[1] != 'placed':
                raise ValueError('all fixed source frames must be placed')
            maps[int(p[0])] = p[2:6]
    rows = {(r['index0'], r['region']): r for r in scan['frames']}
    expected = {(i, region) for i in range(70) for region in ['facet-edges', 'dark-inclusion']}
    if len(scan['frames']) != 140 or set(rows) != expected or sorted(maps) != list(range(70)):
        raise ValueError('exact original 70-frame/two-window identity required')
    profiles = np.empty((3, 70, 3, 48, 3), dtype=np.float32)
    counts = np.empty((3, 70, 3, 48), dtype=np.int64)
    bindings = []
    for index in range(70):
        path = SOURCE / f'DSC{index+94:05}.tiff'
        stat = path.stat()
        image = tifffile.memmap(path, mode='r')
        if image.shape != (4688, 7032, 3) or image.dtype != np.uint16:
            raise ValueError('original export extent/type changed')
        for region in ['facet-edges', 'dark-inclusion']:
            record = rows[index, region]
            if (Path(record['source_tiff']).resolve() != path.resolve()
                    or (stat.st_size, stat.st_mtime_ns) != (record['source_bytes'], record['source_mtime_ns'])
                    or record['pull_bits'] != maps[index]):
                raise ValueError('source metadata/map identity changed')
            x, y, w, h = record['source_native_xywh']
            if w != 384 or h != 384 or min(x, y) < 0 or x+w > 7032 or y+h > 4688:
                raise ValueError('original bound crop changed')
            crop = np.asarray(image[y:y+h, x:x+w]).copy()
            digest = hashlib.sha256(crop.tobytes()).hexdigest()
            if digest != record['crop_rgb16_sha256']:
                raise ValueError('original crop pixel hash changed')
            for target, (_, source_region, core, direction) in enumerate(TARGETS):
                if source_region == region:
                    support_inside((x, y), crop.shape, maps[index], core, direction)
                    profile, count = bin_profile(crop, (x, y), maps[index], core, direction)
                    if not np.isfinite(profile).all() or (count <= 0).any():
                        raise ValueError('empty/nonfinite actual profile bin')
                    profiles[target, index], counts[target, index] = profile, count
            bindings.append({'index0': index, 'region': region, 'source_native_xywh': [x, y, w, h],
                'crop_rgb16_sha256': digest, 'pull_bits': maps[index], 'source_tiff': str(path),
                'source_bytes': stat.st_size, 'source_mtime_ns': stat.st_mtime_ns})
        del image
        after = path.stat()
        if (stat.st_size, stat.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('source metadata changed during read')
    out.mkdir()
    np.savez_compressed(out / 'profiles.npz', rgb16_mean=profiles, pixel_count=counts,
                        distance_edges=S_EDGES, transverse_edges=T_EDGES, frame_index0=np.arange(70))
    figures(out, profiles)
    receipt = {'status': 'SOURCE_MORPHOLOGY_ONLY', 'seconds': time.perf_counter()-started,
        'script_sha256': sha(__file__), 'plan_sha256': sha(HERE / 'plan.md'),
        'scan_receipt_sha256': sha(SCAN), 'export_receipt_sha256': scan['source_receipt_sha256'],
        'warpmap_sha256': scan['warpmap_sha256'], 'profiles_sha256': sha(out / 'profiles.npz'),
        'source_tone_bits': scan['source_tone_bits'], 'source_wb_bits': scan['source_wb_bits'],
        'targets': [{'name': n, 'source_region': r, 'core_output_native': c, 'direction': d} for n,r,c,d in TARGETS],
        'axes': ['target', 'frame_index0', 'transverse_strip', 'distance_bin', 'RGB'],
        'units': 'Unchanged developed RGB16 display codes, arithmetic mean; not linear radiance',
        'pixel_count_range': [int(counts.min()), int(counts.max())], 'bindings': bindings,
        'interpretation': 'No quality score, focus optimum, optical PSF, spectral attribution or RAW clipping measurement.'}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k: receipt[k] for k in ['status', 'seconds', 'pixel_count_range']}))


if __name__ == '__main__':
    main()
