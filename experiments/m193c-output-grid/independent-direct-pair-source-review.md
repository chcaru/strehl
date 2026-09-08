# M193c direct-pair branch — independent source review

VERIFIED source correspondence; no remaining source blocker in the held candidate below. This is a prospective implementation/control review. I did not import or execute the runner, decoder, feature extractor, matcher, controls, plan generator, or process helper, and did not open image payloads. No direct-pair result or alignment accuracy is admitted by this review.

| Reviewed artifact | Bytes | SHA256 |
| --- | ---: | --- |
| `direct-pair-run.py` | 24,373 | `fbf89076ae3e8069ab717796818a6c0a2417637cd29973d533ceefdd1fd82782` |
| `direct-pair-preregister.md` | 8,093 | `d49b65fe2406ea387df9ae7caf0717599387aa98c973cdabc09562d5083dc95c` |
| `work/prepare-direct-pair-plan-1.py` | 3,761 | `dda095413592a1f7a754cfaa1d7bb08658a3d5bd011d56e430439514daf0f91a` |
| `work/direct-pair-prior-work-1.json` | 104 | `e0c9eb506b6755013e8fe98b61ae4535aaa7e05e2cb1875cdd8e507fc07412ff` |

Paths are relative to `experiments/m193c-output-grid/`. Both Python sources passed stdlib AST parsing only. The final exact file sizes and digests above were read from disk.

## Rechosen pair and interpretation boundaries

I independently derived **23**, rather than merely accepting the general ceiling of 25: the 20 local span-1/2/4 pairs plus eight local5 star pairs share five edges. The code's sorted unordered union matches the literal list. Every star call retains reference5/source-other, including lower-index sources; other calls use lower reference/higher source. In particular, the observed failed reference5/source8 call remains present in its original direction. The source's pair expression handles both sides of the star correctly. Local rung spans correspond to original gaps13/26/52, not adjacent RAWs.

The held matcher confirms why direction matters: nearest-neighbor ratio filtering and the ordered reference/source coordinates/descriptors enter the match digest that determines the calibration/holdout split. Reversing a pair is not an equivalent replicate. Reference local5/original65 is also distinct from consumer anchor local4/original52. The graph uses the latter for connection reporting, calculates bridges by removing each accepted edge, and marks a node's cycle participation only through a nonbridge incident edge. Thus a cycle in another component or elsewhere along a tree tail does not qualify that node.

The authority boundary requires the actual coverage parent refusal, independent saved-outcome audit, exact result/release/outer/console/exit associations, unchanged executed sources/inputs, eight actual upstream controls, complete ordering, and the first reference65/source104 exception with seven unvisited inputs. It cannot treat a decoding/resource refusal as this registration branch. Its historical pair comparison affects `interpretation_eligible`; a changed result retains the observations but explicitly stops topology interpretation. Reproducing the exception supports reproducibility, not its causal explanation.

## Decoder, observations and controls

The new entry authenticates the opened ordinary TIFF's identity, bounded extent, selected stable metadata and SHA256, then passes those same bytes to the unchanged `decode_input_tiff`. It writes no TIFF/snapshot. The blob's local lifetime ends on decoder return before feature extraction; each real RGB is released after its feature call. Later retained-file rehashing is additional read work inside the same budget, not another decode or snapshot. Nine bounded FeatureSets and small coordinate/digest records remain. The previous near-8-GiB peak does not prove this new lifetime arrangement fits; an actual memory refusal remains admissible evidence of an incomplete campaign.

The observer delegates the original matcher once, returns the same match-list object, and restores the original symbol in `finally`. Its diagnostics use that actual ordered list, preserving the alternating split. Accepted holdout bounds describe sampled landmark support. They do not establish dense frame support or native ground truth. No second matcher pass is used to obtain those diagnostics.

The seven controls are bounded to six small matcher calls, five private feature extractions, and six successful private decoder entries; the wrong-SHA entry must never decode. Two distinct nonidentity fixture maps are checked against their own frozen Q32/count/RMS/guard expectations. The swap destroyer uses the same acceptance predicate as those positives and has distinct expected maps. Identity does not supply direction power. Existing frozen gauge controls remain upstream evidence for sign/order/native-factor arithmetic, not placement truth.

Off/count/placebo compare canonical signature bytes by SHA256 as well as structured transform/metrics/guard/error equality. Count must actually retain 256 matches. The complementary refusal checks the named scientific code; arbitrary exceptions are not substituted. The repaired blob control wraps the actual unchanged decoder with a private counter: wrong SHA must yield the exact authentication error and zero entries, while restoration must yield exactly one entry and the fixed small shape. The wrapper is restored in `finally`. None of these outcomes has yet been measured for this runner.

## Concrete findings closed before execution

The first reviewed candidate kept control rows local until the whole control function returned. A failed assertion would therefore erase its actual control evidence from the terminal result. The final source appends each row into the live result and saves it before asserting; successful-prefix and failed rows survive subsequent refusal.

The original entry authenticated the plan, and the worker request, without retaining those records for final checks. Both roles now add the actual plan FileRef to their file ledger; the worker also adds its actual request. Final file checks therefore cover these entries through publication, alongside source, prior-work, authority and consumed-file bindings.

The initial parent serialized its entire inherited child environment. The final source records only the four explicit thread settings and removed variable names; the full environment is used only to launch the child. The SHA control's initial eventual-error-only predicate was also strengthened with the zero/one actual decoder-entry witnesses described above. These changes add no matcher call, image population, control ID, or scientific threshold. The author's separate correction uses the existing bounded authenticated raw reader for saved exit/console bytes.

## Budget, process and preparation scope

The required carry is **368.203125 CPU s / 402.6725757 conservative wall s / 3,947,560,798 file bytes / 22,360,152 metadata bytes**. The runner checks the audited coverage final work and conservative outer wall plus the nonrefundable **20 CPU s / 30 wall s / 1 MiB** preparation addition. The old snapshot reservation is retained; it is not refunded because coverage refused early.

The new whole diagnostic is bounded by **300 CPU s / 480 wall s / 8 MiB new files and metadata**, inside the original **1,200 CPU s / 1,800 wall s / 4 GiB files / 128 MiB metadata** limits. The encompassing child additionally retains its existing **240-wall-second / 8-GiB committed-memory / at-most-1-MiB-log** bounds, with actual remaining parent CPU deducted. The worker's request records accrued setup but does not add it a second time. Parent process CPU plus terminal Job CPU owns the final total; missing terminal accounting cannot authorize completion. A cap refusal must remain incomplete, not evidence that unvisited edges failed scientifically.

The compact metadata-only generator preserves the executed 165-source map, adds the new held source/spec/reviews and its own source, binds actual coverage/audit/carry records, and emits the exact parent/worker commands under fresh `direct-pair-1` paths. The verified second read supplies the actual JSON parse bytes. It does not import helpers or open TIFF/RAW payloads. Its 20-CPU/30-wall checks and bounded plan fit the existing preparation reservation; no separate preparer campaign or changed global cap is introduced. Root still owns checking the actual generated plan and freezing its exact command/digest before invocation.

This experiment can deliver a complete table of direct-edge support and scientific refusals. It does not chain maps, solve a global track, construct an overlap denominator, qualify common-merge TIFFs, or satisfy the separate 0.1-pixel product mapping criterion. Any later placement claim needs independently held-out per-frame evidence in the named consumer gauge.
