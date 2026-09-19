"""Presentation-only repair from retained profiles; no source photograph reads."""
from pathlib import Path
import argparse
import hashlib
import json
import os

import numpy as np

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=HERE / 'run-1/profiles.npz')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source, out = args.input.resolve(), args.out.resolve()
    if not out.is_relative_to(HERE) or out.exists():
        raise ValueError('new presentation directory under highlight-spread required')
    original_hash = sha(source)
    receipt_path = source.with_name('receipt.json')
    receipt = json.loads(receipt_path.read_text())
    if receipt['profiles_sha256'] != original_hash:
        raise ValueError('retained profile hash differs from original receipt')
    with np.load(source, allow_pickle=False) as saved:
        profiles = saved['rgb16_mean'].copy()
        distance_edges = saved['distance_edges'].copy()
        strips = saved['transverse_edges'].copy()
        frames = saved['frame_index0'].copy()
    if (profiles.shape != (3, 70, 3, 48, 3) or not np.isfinite(profiles).all()
            or not np.array_equal(distance_edges, np.arange(-24, 74, 2))
            or not np.array_equal(strips, [-12, -4, 4, 12])
            or not np.array_equal(frames, np.arange(70))):
        raise ValueError('unexpected retained profile geometry')
    out.mkdir()
    os.environ['MPLCONFIGDIR'] = str(out / 'matplotlib-cache')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    outputs = []
    for target, binding in enumerate(receipt['targets']):
        # No pyplot registry or shared axes: every figure and axis owns labels.
        fig = Figure(figsize=(16, 10), dpi=130)
        canvas = FigureCanvasAgg(fig)
        axes = fig.subplots(3, 4, sharex=False, sharey=False)
        fig.subplots_adjust(left=0.13, right=0.89, bottom=0.08, top=0.86,
                            hspace=0.62, wspace=0.38)
        for strip in range(3):
            display = profiles[target, :, strip] / np.float32(65535)
            for column in range(4):
                ax = axes[strip, column]
                data = display if column == 3 else display[:, :, column]
                kwargs = {} if column == 3 else {'cmap': 'gray', 'vmin': 0, 'vmax': 1}
                artist = ax.imshow(data, aspect='auto', extent=(-24, 72, 69.5, -0.5),
                                   interpolation='nearest', **kwargs)
                if column == 0:
                    scalar_artist = artist
                ax.set_xlim(-24, 72)
                ax.set_ylim(69.5, -0.5)
                ax.set_xticks([-24, 0, 24, 48, 72])
                ax.set_yticks([0, 17, 35, 52, 69])
                ax.tick_params(axis='both', labelbottom=True, labelleft=True, labelsize=8)
                ax.set_xlabel('Signed distance from core (native pixels)', fontsize=8)
                ax.set_ylabel('Original frame index', fontsize=8)
                ax.set_title(['R display code', 'G display code', 'B display code', 'RGB display codes'][column], fontsize=10)
                ax.axvline(0, color='cyan', linewidth=0.5, alpha=0.5)
            position = axes[strip, 0].get_position()
            fig.text(0.018, (position.y0 + position.y1) / 2,
                     f'Strip {strip+1}\nt in [{strips[strip]:g}, {strips[strip+1]:g})\nnative pixels',
                     va='center', ha='left', fontsize=10)
        fig.suptitle(f"{binding['name']}: core {binding['core_output_native']}, direction {binding['direction']}\n"
                     'SOURCE MORPHOLOGY ONLY — no physical PSF or output-quality claim', fontsize=13)
        fig.colorbar(scalar_artist, cax=fig.add_axes([0.94, 0.22, 0.012, 0.52]),
                     label='Unchanged RGB16 / 65535')
        destination = out / f"{binding['name']}.png"
        canvas.print_png(destination)
        outputs.append({'path': str(destination), 'sha256': sha(destination)})
        fig.clear()
    if sha(source) != original_hash:
        raise ValueError('retained profiles changed during presentation')
    result = {'status': 'PRESENTATION_ONLY', 'script_sha256': sha(__file__),
              'profiles': str(source), 'profiles_sha256': original_hash,
              'source_receipt_sha256': sha(receipt_path), 'outputs': outputs,
              'changes': 'Fresh standalone figures; explicit axes, ticks and strip labels. No numerical changes.'}
    (out / 'receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
