# First-stage learned selection: executed, direct output rejected

2026-09-25. **MEASURED**: the frozen three-source pilot completed normally in
4.625s of bounded-process wall time. This includes startup, input validation,
five model calls and output writing; it is not a whole-stack speed measurement.
Peak allocated CUDA memory was126,810,112bytes. The warmed primary forward
call took0.00446s including its finite-logit observer. The first call took0.497s.
These operational timings do not support a488-source throughput claim.

The pinned checkpoint loaded safely and completely into the unchanged float32
network. Duplicate/constant fidelity and mixed-source mapping controls passed;
both mapping mutations failed as intended. Original and reversed source order
produced identical grayscale, selected RGB16 and mapped-back indices. Finite
pre-argmax logits were observed on all four primary calls. Removing that observer
left the primary map and image bit-identical. The output copies original RGB16
vectors; no generated image content or source blending was introduced.

**ROOT AND INDEPENDENT VISUAL VERDICT**: the candidate
contains the near donor112 fan tips and the far donor152 slanted strands, but
conspicuous patch boundaries appear across its smooth surround. These are visible
inside the crop, not just its outer MHC blend ring. This direct output is
unacceptable, so no full-stack render or production integration is earned.
The independent review also read back the saved TIFF and verified exact source
selection and display quantization; see `independent-results.md`.
The full488 baseline also contains additional loops and intermediate-focus
detail absent from the three supplied sources; that coverage difference cannot
be attributed to model failure. No SOTA claim follows either observation.

The native384 results, integer maps, complete input/checkpoint hashes, call costs,
ICC and development bindings are in `pilot-1/receipt.json`. `candidate.png` is a
diagnostic crop, not a complete stack deliverable. Native crops were viewed with
no resizing; no fine-detail conclusion uses an overview. The outer two RGB
pixels can contain the earlier MHC blend ring, and cropped network context
remains different from whole-image context.

Commands actually run from the workspace with Python3.12:

```text
python -I -B -X faulthandler experiments/stackmff-v4-evaluation/pilot.py fetch --out experiments/stackmff-v4-evaluation/upstream-1
python -I -B -X faulthandler experiments/stackmff-v4-evaluation/pilot.py fetch --out experiments/stackmff-v4-evaluation/upstream-2
python -I -B -X faulthandler experiments/stackmff-v4-evaluation/run.py --out experiments/stackmff-v4-evaluation/job-1 -- experiments/stackmff-v4-evaluation/pilot.py run --upstream experiments/stackmff-v4-evaluation/upstream-2 --out experiments/stackmff-v4-evaluation/pilot-1
```

The first fetch failed at the sandbox network boundary and retains its refusal.
The separately approved public-download retry verified all four pinned Git
blobs. No package installation, training, diffusion, additional model or
ImageNet weight download occurred. External research downloads are ignored by
Git and are not included in the shipped application. The independent source
review preceded inference; its result interpretation is recorded separately.
