# Independent complete-chip photographic review

2026-09-25. **VERIFIED visual verdict: reject this candidate.** The shared full-AC source field contracts some broad soft spill and makes contact edges more emphatic, but introduces conspicuous patchy colour and tone, broken transitions and bright fragments. This is a useful negative observation, not an image-quality improvement or a production candidate.

## Admitted comparison

The root-executed `run.py full` observation completed in 293.110 s wall time. `run-1/completion.json`, `run-1/output/receipt.json` and `views-1/completion.json` identify all 299 sources, reference 149, current 6500x4332 native output, crop `[133,89,3250,2166]`, and the existing seven frozen native regions. The baseline RGB16 and ICC equal current production; baseline and candidate use the same actual resolved tone, with exact baseline pinned rewrite. Repeated gathered planes, source bindings and replay passed. This review does not infer photographic truth from those mechanical checks.

Baseline RGB16 SHA256: `fbeeda70e45be91086e5d6400b642054df908a87ae4021815ad493940960298c`.

Candidate TIFF SHA256: `586bca35508800e88e2553e62a039b4b75dd78a0a02f2cf6ed78b3702a4a84bb`; candidate RGB16 SHA256: `aceeec36203c63baa69031e99befaaa6e6037fe6747b515e49700cf814c198db`.

The complete `baseline-overview.png` and `candidate-overview.png` were viewed first for orientation. Then all 25 prescribed native pairs were viewed without resampling: the 384-pixel rail target and four 256-pixel tiles from each remaining region. The same RGB16-to-8-bit conversion and ICC apply to both arms. No difference image, new crop search or sharpness score was used.

## Independent visual findings

| Frozen region | Native pairs inspected | Finding |
| --- | --- | --- |
| Rail crossing | `[1098,958,384,384]` | Bright rail/contact edges become harder, but large irregular yellow/green islands appear inside formerly smooth areas. Multiple coloured edge tracks remain. The new patch boundaries are not acceptable reconstruction. |
| Upper colour | x=1036/1292, y=196/452 | Dark compartments acquire flat purple/brown/green patches and abrupt boundaries. The broad orange divider becomes mottled. More emphatic fine structure does not offset the damaged surface transitions. |
| Central stipple | x=2976/3232, y=1306/1562 | The stippled interior largely survives, while dark adjoining contact faces gain large coloured islands and broken contours. Parallel coloured edge tracks persist. |
| Lower array | x=566/822, y=2796/3052 | Repeating cell boundaries remain legible, but horizontal orange rails gain bright dash-like fragments and mottled interiors. Dark cells acquire granular/patchy structure. This does not establish recovered real detail. |
| Lower colour | x=4666/4922, y=3016/3272 | Some broad green spill near the contact is reduced. It is replaced by strongly visible maroon/green patches and discontinuous tones on the surrounding smooth and shadowed surfaces. All four tiles show the tradeoff. |
| Surface scratches | x=4856/5112, y=1256/1512 | Fine scratches mostly remain, but the smooth green surface gains mottling and coloured islands around several scratches. Keeping the scratches is a protection check, not a quality gain. |
| Upper-left contact grid | x=48/304, y=336/592 | Broad soft plumes contract around several contacts, but bright yellow-green patchwork, granular contact faces and duplicated coloured outlines remain or become more emphatic. The formerly smooth yellow outer strip becomes visibly blotchy. |

The complete view also exposes the patchiness across the orange/red substrate and shadowed regions. This is not a subtle regression limited to an incidental crop. The fixed native targets confirm it while also showing that some soft boundary spill was affected: the candidate is active, but the tradeoff is wrong.

## Program disposition

Do not promote, transfer to other photographs, or sweep this unchanged field's penalties/activation to rescue it. Its older generated qualification remains false, including the previously measured focused-glint and fine-structure damage; the capacity controls reproduced that old screen exactly. The separately authorized chip observation changed scheduling scope only and did not erase those failures. This full photograph adds direct evidence of unacceptable colour/tone discontinuities on the current consumer. It neither proves capture/geometry is sufficient nor identifies the cause of every baseline ghost or occlusion halo.

The full outputs remain available at `views-1/baseline-full.jpg`, `views-1/candidate-full.jpg` and `run-1/output/{baseline,candidate}.tiff`. They should be shown as a rejected experiment if presented to the user, never labelled an improvement.
