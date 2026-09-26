# GMFF restoration stage: not ready for a quick pinned comparison

2026-09-25. **NO-GO on current release readiness, not an image-quality verdict.**
No model download, installation, training or inference was attempted. Root
expanded this investigation to stage2 read-only readiness after stage1's
independently observed switching seams. The ordinary official release does not
currently provide a verified, immutable pair of restoration checkpoints.

**Available official interface.** At GMFF commit
`d104b3f51fc3933c7dbb2da27a21816b574914f3`, the
[README](https://github.com/Xinzhe99/GMFF/blob/d104b3f51fc3933c7dbb2da27a21816b574914f3/README.md)
names `inference_stage2.py`, `IFControlNet.pt`, and
`v2-1_512-ema-pruned.ckpt`. Its invocation takes a folder of stage1 fused images,
not the source stack or its index map. Settings shown are upscale1, versiongmff,
spaced sampler,50steps, captionernone, empty positive prompt, a quality/blur/noise
negative prompt, CFG4, CUDA andfp32. Therefore the documented route restores an
already fused image; it cannot directly check proposed detail against omitted
donor pixels. Exact tensor API, actual stochastic initialization/seed, native384
padding/resizing, full-size tiling/context, and checkpoint loading safety remain
**UNVERIFIED** because the implementation read was refused below. No source
inspection or runtime claim is inferred from the command-line example.

**Release availability.** A successful complete recursive Git-tree metadata
read at that commit reports `truncated=false`; the only checkpoint is
`weights/stackmffv4.pth`. Stage2 entrypoint metadata exists:12,326bytes, Git blob
`9259788520949463688933f58c89841865c9aedb`. `requirements.txt` is706bytes, blob
`f4b011bf07977b2c808a3be2eb2c1b77d05ac71d`; its exact dependency contents were
not read. The README's official model bundle is a
[Baidu share](https://pan.baidu.com/s/19KNHIfqrV054C-T623P9LA), access code `cite`.
No stage2 checkpoint byte size, content hash or immutable release pin was
verified. The share was not accessible through the ordinary web read. The
official Stability-AI StableDiffusion repository returned404, and the official
SD2.1-base model-card URL returned401. These observations establish unavailable
verification on this route, not that the files no longer exist. No accounts,
login workarounds, alternative mirrors or large downloads were pursued.

**Licence provenance.** GMFF declares MIT in its README; no separate licence
file was found in the previously inspected complete tree. Its named upstream
projects declare [DiffBIR Apache-2.0](https://github.com/XPixelGroup/DiffBIR/blob/main/LICENSE)
and [ControlNet Apache-2.0](https://github.com/lllyasviel/ControlNet/blob/main/LICENSE).
[CompVis latent-diffusion](https://github.com/CompVis/latent-diffusion/blob/main/LICENSE)
declares MIT. The separate [CompVis Stable Diffusion model licence](https://github.com/CompVis/stable-diffusion/blob/main/LICENSE)
is CreativeML Open RAIL-M; this is **not** verification of the unavailable SD2.1
checkpoint's licence or a blanket MIT grant for weights. Exact IFControlNet
weight provenance/terms, SD2.1 weight terms and the transitive runtime dependency
licences are unresolved. No GPL or third-party implementation was read.

**Approval-review record.** The attempted read-only public text request for
`requirements.txt` and `inference_stage2.py` was rejected before execution:
the reviewer treated diffusion-stage implementation as outside the earlier
stage1-only scope. One same-action retry quoted root's newly expanded scope;
it was rejected again because that expansion was treated as assistant text,
not user authorization. No alternate mechanism bypassed either rejection.
This blocks exact implementation inspection separately from missing reproducible
weight identities. These are automatic approval-review decisions, not a claim
that the user's SOTA request forbids research on generative restoration.

**Decision.** A paired source-fidelity experiment is conceivable only after
release identity and execution safety are resolved: unchanged pretrained
restoration of the fixed fusion plus clean-donor and flat/known-detail controls,
fixed seed/settings, and independent rejection of invented/lost strands. Such
controls could falsify fidelity; a smoother picture cannot establish it. There
is no defensible native384 or complete-image timing/memory route to promise
from current evidence. Close this readiness check; do not spend time on package
setup, access recovery or an unpinned model as the next quality intervention.
