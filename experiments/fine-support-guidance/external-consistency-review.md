# Retained MIT comparator: consistency and colour reassignment

Read-only review completed 2026-09-19; persisted here without further research. **VERIFIED source facts** below describe the exact retained version, not a new execution or causal ablation. No build, RAW read, comparator rerender or source edit was performed.

## Licence and provenance

The reviewed directory is `experiments/M175-fork-arm/work/repro/source-a`. Its `LICENSE.md` grants the MIT licence, copyright 2019 Petteri Aimonen. The pin is `experiments/M175-fork-arm/source-pin.json`:

- Commit: `4bc7f95e448cf20ee2bdd758403ec43e2612a1c6`.
- Git subtree: `543b825e325f959ed15c10032d2b8156f11070cc`.
- Canonical source-manifest SHA256: `494d3abb49ccec3f23d7c37676acd806111f973f12c0cf416ae45999359d1196`.
- Rebuilt comparator executable SHA256: `691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac`, as retained in M175 and used for the vitamin-C comparison.

A Python `hashlib.sha256` check was run against each inspected file and asserted equality to its corresponding `source-pin.json` entry. All ten matched:

| Path relative to reviewed directory | SHA256 |
| --- | --- |
| `LICENSE.md` | `5e11fc4bce97ec54bfe65e8b74da8010fd1d7f2427d35f28e3cab25607109e57` |
| `src/main.cc` | `d515176145bd4ae050bd0c78661a1ee975b6e571b52f6f364452ca500b5e1d1a` |
| `src/task_merge.cc` | `eee52b9269b55eb2158dff2b66fbb7831abaea5a2b0933eb0c85ed10b190957d` |
| `src/task_merge.hh` | `199a5feec9e2c0eebc2b54cc2321cc09491364acda27926dc5980248b89875f7` |
| `src/task_grayscale.cc` | `892592dc2da4274cc924ae20d7dc016bc4e26a91e0bfeb61ad36550918a0d380` |
| `src/task_wavelet.cc` | `e0ce7d6051a7ad6a1b544da460a67cc5560cb9d9d04697bf96a049f2c11fa665` |
| `src/task_wavelet.hh` | `47f292cddd805871914ebaaf92727ff3af018ea0f13ca49e3bc6849da1f99ebd` |
| `src/task_reassign.cc` | `e5e780b8dea9ac448001d776935d1609a9100560e566c86a828e95a168ae98d3` |
| `src/focusstack.cc` | `acc1717e3e14618c481900e9967edb7b58982c1e6b04235261d4ec6d4b3b10ef` |
| `src/task_denoise.cc` | `4bdd3b17db4bb07b7f3f465fd21ffea4a2608d369dcb961ade4818dcc3c25196` |

No prohibited GPL/LGPL implementation was opened.

## What consistency2 actually changes

**VERIFIED, code reading:** `main.cc:155` sets the CLI default to 2. `FocusStack::schedule_single_image_processing`, `focusstack.cc:411`, converts aligned RGB to one shared-PCA grayscale signal and transforms that signal. `Task_Grayscale::task`, `task_grayscale.cc:38`, reuses the reference weights and quantizes the result to 8-bit at line 59. Consistency therefore operates on **grayscale complex wavelets and their frame-index map**, not independent RGB channels or Bayer phases.

`Task_Merge::task`, `task_merge.cc:45`, first chooses each coefficient by maximum squared complex magnitude. At lines 63 and 68, level 2 enables these two operations, in order:

1. **Same-scale directional agreement:** `Task_Merge::denoise_subbands`, line108, visits the corresponding horizontal, vertical and diagonal detail positions at every decomposition level. If two donor indices agree, the third index and its complex coefficient are replaced to match. Three different donors are left alone. This is a two-out-of-three **directional** vote. It is not a parent–child scale vote, a coarse-only rule, an RGB vote, or an energy-support average. The residual low-pass corner is not one of the three detail subbands.
2. **Isolated ordinal extrema repair:** `Task_Merge::denoise_neighbours`, line160, scans the whole packed index array in place. A centre changes only if it is strictly larger than all four cardinal neighbours or strictly smaller than all four (`line172`). It assigns the rounded mean index `(top+bottom+left+right+2)/4` (`line176`) and replaces the coefficient. It is **not spatial majority voting**, a median, or a noise-aware test. The scan includes packed subband boundaries and the low-pass region; it does not implement a clean same-scale neighbourhood everywhere.

These operations run after **every batch**, via `FocusStack::schedule_batch_merge`, `focusstack.cc:442`. With the comparator's batch size 2, retrieval deserves care: `Task_Merge::get_source_img`, `task_merge.cc:97`, returns a requested original coefficient only if that frame is in the current batch. Otherwise line 103 returns the previous **composite**, regardless of the requested older donor index. Thus it is not equivalent to a global final index-map filter with all original coefficients still available. Earlier filtered coefficients also enter later maximum-magnitude comparisons.

`--denoise=1` is separate: `Task_Denoise::task` shrinks or zeros detail coefficients by squared magnitude, leaving the lowest low-pass image untouched. It is scheduled after the last merge and before inverse transformation (`focusstack.cc:524`).

## The separate, more direct colour mechanism

**VERIFIED, code reading:** final `Task_Reassign` is always scheduled at `focusstack.cc:562`. Its colour map retains an aligned RGB16 tuple for each distinct **8-bit grayscale code** at each output location. `Task_Reassign_Map::build_color`, `task_reassign.cc:107`, copies old entries first; line 122 only inserts a new tuple when that grayscale code is unseen.

`Task_Reassign::reassign_color`, line 233, searches for the stored grayscale closest to the reconstructed grayscale. It copies the entire selected RGB tuple at line 250. Ties retain the first entry because line 241 updates only for strictly smaller error. This is a whole-colour donor selection after grayscale fusion, not a use of the wavelet donor-index map.

Default scheduling is reference outwards, `focusstack.cc:292` and `:304`: for 70 inputs, 35, 34, 36, 33, 37, … . Hence an earlier tuple survives when a later frame has the same grayscale code. This ordering fact does not establish which frame supplied any particular reviewed output pixel.

## What follows, and what does not

**DERIVED from the rules:** a coherent late-frame 69 feature that wins all three directional subbands and its spatial neighbours is unchanged by both consistency operations. Therefore consistency 2 is not a general remedy for the measured dominant late-frame contribution. The native fine-band support experiment changes a different decision: the spatial support of the energy used for selection.

**ARGUED hypothesis, unmeasured:** final whole-RGB reassignment is a more direct explanation candidate for fewer coloured fans than consistency alone. It prevents independently synthesized output colour tuples and can preserve earlier tuples at equal grayscale codes. Its selection can also retain grain. However the available whole-output comparison changes alignment, CA treatment, grayscale representation, fusion, denoising, reassignment and development order together. Neither the reduction in long coloured spokes nor the increased grain has been causally assigned to this step. Existing long fans in late source frames also prevent treating every output fan as colour newly invented by reconstruction.

Do not copy this exact consistency implementation as a presumed fix. If a later bounded ablation is needed, isolate donor-coherent colour reassignment separately from energy-support pooling, retaining a low-detail control and actual structure checks. The current program is testing smaller **band0-only** support pooling, not reproducing the comparator.

## Existing project coverage

The focused report search found `C-landscape.md:194` already describing the pipeline and colour reassignment. Its cited warning says reassignment can make occlusion artifacts worse; it is not an unconditional remedy. `M162-noise-regression.md:30` also summarizes these stages, but its “spatial/subband majority filtering” wording is imprecise for the exact spatial rule above. `G-edof-deconvolution.md:143` and `M79-edof-microscopy-survey.md:165` discuss Forster's consistency/reassignment results. I found no exact retained-version mechanism ablation in the searched reports. These prior surveys should be reused rather than repeated; they do not prove the cause of the current vitamin-C result.
