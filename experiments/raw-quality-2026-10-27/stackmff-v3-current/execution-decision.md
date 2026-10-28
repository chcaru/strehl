# Root release of one complete weevil observation

2026-10-27. **MEASURED controls and cost; UNVERIFIED photographic quality.**
The fixed model, native output extent, all 299 sources and two-scale soft
readout remain unchanged. Root releases one complete observation under the
already declared 3600s/24GiB host/24GiB Torch limits. This is feasible for a
bounded research photograph, not competitive processing speed or product
admission. No source subset, lower resolution, reduced halo or mixed precision.

Commands actually run:

```text
python -B -X faulthandler experiments/raw-quality-2026-10-27/stackmff-v3-current/run.py controls
python -B -X faulthandler experiments/raw-quality-2026-10-27/stackmff-v3-current/run.py cost
python -B -X faulthandler experiments/raw-quality-2026-10-27/stackmff-v3-current/run.py full
```

Controls complete in3.687s with2,938,761,216bytes peak host job commitment.
All declared mechanical and small generated quality guards pass. Correct
interior/outer-edge probability maxima differ from direct official inference
by2.265e-6/2.354e-6; RGB maxima differ by1.192e-7. The wrong-halo foil instead
differs by0.20445 in probability and0.005962 in RGB, failing the unchanged
bounds. Direct small official probabilities and output codes are exact.
The noisy flat retains a small error increase over uniform averaging, within
the fixed allowance. These results do not establish real occlusion physics,
native RAW fidelity or photographic improvement.

The actual fixed tile uses all299 sources, a256-square core and512-square
context. Two unchanged calls take5.5994s and4.0474s, of which gather costs
3.7573s/2.7907s and inference/fusion1.8421s/1.2567s. Delivered codes repeat
exactly. Torch peaks at15,420,138,496bytes allocated and16,414,408,704reserved;
host job peaks at20,282,814,464bytes. The bounded cost process completes
in83.875s, including full59.14GB before/after input hash sweeps. All original
developed TIFF bytes and metadata remain unchanged.

The conservative486-tile projection is2721.3s, excluding process startup,
preparation, model load, complete export and preservation checks. Actual
preparation and final preservation take36.297s/35.275s in this cost process.
This projects a complete observation inside one hour, but is markedly slower
than the retained native and Helicon workflows. Only the complete job can
establish its actual runtime and peak memory. Existing development and alignment
costs are additional to this saved-input fusion experiment.

The full command has been dispatched; completion, input preservation, every
output pixel, master readback and independent complete photographic review are
still required. No quality claim follows from this release. See
[independent model review](model-review.md), [comparison protocol](comparison-protocol.md)
and the immutable job receipts under `outputs/raw-quality-2026-10-27/`.
