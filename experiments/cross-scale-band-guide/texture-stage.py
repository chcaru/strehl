"""Fixed retained RGB16 textures, not recovered camera radiance. Root executes."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
MARIGOLD = ROOT / 'experiments/marigold-comparator/run-2/developed'
CHIP = ROOT / 'experiments/chip-competitor/run-1/developed'
ICC_SHA = '238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b'
# Native source-grid origins, frozen independently of candidate or tile contents.
TRAIN_XY = [(1500, 800), (3500, 1500), (4800, 2600), (3200, 3100)]
HELD_XY = [(1460, 1240), (462, 682), (3402, 1652), (5092, 3362)]
W, H = 192, 176


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(8 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--split', choices=['training', 'heldout'], required=True)
    args = p.parse_args()
    out = args.out.resolve()
    need(out.is_relative_to(Path(__file__).resolve().parent) and not out.exists(), 'fresh owned output')
    import numpy as np
    import tifffile
    directory = MARIGOLD if args.split == 'training' else CHIP
    receipt_path = directory / 'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    if args.split == 'training':
        need(receipt['status'] == '488_UNALIGNED_NATIVE_RGB16_DEVELOPED'
             and receipt['resolved']['srgb'] is True, 'fixed marigold development')
        indices, origins = [112, 152, 320], TRAIN_XY
    else:
        need(receipt['status'] == '299_UNALIGNED_NATIVE_RGB16_DEVELOPED', 'fixed chip development')
        indices, origins = [149], HELD_XY
    out.mkdir()
    rows, sources = [], []
    for ordinal in indices:
        source = receipt['frames'][ordinal]
        need(source['ordinal'] == ordinal and source['output_wh'] == [7032, 4688], 'ordinal/native geometry')
        path = Path(source['output']).resolve()
        need(path.parent == directory.resolve() and sha(path) == source['output_sha256'], 'retained TIFF hash')
        with tifffile.TiffFile(path) as tf:
            page = tf.pages[0]
            need(len(tf.pages) == 1 and page.shape == (4688, 7032, 3)
                 and page.dtype == np.dtype('uint16'), 'native RGB16 TIFF')
            icc = bytes(page.tags[34675].value)
            need(hashlib.sha256(icc).hexdigest() == ICC_SHA, 'known embedded sRGB profile')
        image = tifffile.memmap(path, mode='r')
        for tile, (x, y) in enumerate(origins):
            encoded = image[y:y+H, x:x+W].astype(np.float32) / np.float32(65535)
            need(encoded.shape == (H, W, 3), 'frozen tile complete')
            linear = np.where(encoded <= np.float32(.04045), encoded / np.float32(12.92),
                              ((encoded + np.float32(.055)) / np.float32(1.055)) ** np.float32(2.4)).astype('<f4')
            need(np.isfinite(linear).all() and linear.min() >= 0 and linear.max() <= 1, 'finite display-linear texture')
            name = f'{args.split}-{ordinal:03}-{tile}.f32'
            dest = out / name
            with dest.open('xb') as handle:
                handle.write(linear.tobytes())
            rows.append(dict(file=str(dest), sha256=sha(dest), shape=[H, W, 3], dtype='<f4',
                             source_ordinal=ordinal, native_xywh=[x, y, W, H],
                             original_rgb16_sha256=hashlib.sha256(image[y:y+H,x:x+W].tobytes()).hexdigest()))
        del image
        need(sha(path) == source['output_sha256'], 'retained TIFF changed during read')
        sources.append(dict(path=str(path), sha256=source['output_sha256'], icc_sha256=ICC_SHA))
    result = dict(schema=1, split=args.split, tiles=rows, sources=sources,
                  development_receipt=str(receipt_path), development_receipt_sha256=sha(receipt_path),
                  source_sha256=sha(__file__), resized=False, registration_applied=False, raw_reads=False,
                  transfer='piecewise IEC sRGB decode to display-linear f32',
                  scope='Arbitrary synthetic latent texture. Tone/matrix/rolloff are not inverted; no original physical radiance or real-photo truth claim.')
    with (out / 'textures.json').open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
