# M194d literature scope check

2026-09-07, root. **VERIFIED primary-paper content; no external model run.**
This is a bounded refresh alongside the local admission audit, not a complete
literature survey or an external performance comparison. No external repository
source, model weights or dataset was opened or downloaded.

Mechanical prior-art command run:

```text
python -X utf8 experiments/ORCH-drift-check/prior_art.py StackMFF diffusion learned focus
```

The leading relevant record is `docs/research/B-algorithms-sota.md`, especially
sections3 and9. It already covers GMFF/StackMFF and Araujo's RAW work. The refresh
does not turn those into new discoveries. The neighboring M69/M70/M67 records
remain the local calibration/admission constraints.

Exact web searches run:

- `site.arxiv.org multi focus image fusion noise 2025 2026 focus stacking`
- `site.openaccess.thecvf.com focus stacking noise multi-focus image fusion 2025`

## Papers and implications

**GMFF / StackMFF V4, arXiv2512.21495v1, 2025-12-25:** a deterministic fusion
stage followed by optional diffusion restoration. Its authors recommend the
deterministic stage alone for scientific imaging. Deterministic evaluation uses
PSNR/SSIM; generative evaluation uses BRISQUE/PIQE and acknowledges that
perceptual enhancement need not reduce pixel error. Training stacks are
synthesized from images and depth maps. These statements were checked in
sectionsI andIV-A of the [primary paper](https://arxiv.org/html/2512.21495v1).

**ARGUED implication:** generative sharpness is not a substitute for this
program's actual-output truth and temporal-noise controls. The deterministic
stage remains a plausible later external comparator. This read establishes
neither its superiority nor inferiority on our CFA/deep-stack population.

**Araujo, Ponce and Mairal, arXiv2311.17846:** the primary abstract describes
94 high-resolution RAW bursts, commercial-software pseudo-ground-truth and
qualitative noise-tolerance results. This is an applicable comparison lead,
with supervision distinct from independent truth. The existing report's broader
full-text review is not repeated here. [Primary abstract](https://arxiv.org/abs/2311.17846).

**UDD, Liu et al., SSRN5390897, posted2025-08-13:** the abstract proposes
unsupervised diffusion with noise-aware conditioning and a fusion enhancement
module. Only the [author preprint abstract](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5390897)
was available in this check; the journal-page request failed. Its claimed noise
robustness is an author claim, with RAW/deep-stack transfer and independent truth
performance **UNVERIFIED here**. Do not infer a deployment or calibration result
from the abstract.

## Scheduling decision

**ARGUED:** keep the small production admission experiment next. These reads do
not justify replacing the architecture, training a model, importing an unknown
license, or weakening the benchmark. A future external comparison must commission
the actual program, common geometry and output interpretation before scoring it.
