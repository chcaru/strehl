# Source multiplicity in the pinned learned comparator

2026-10-27. Source-only supporting audit; no numerical release.

Question: does the exact pinned V3 architecture preserve its output when every
source is duplicated equally, and how does repeating only a blurred source
change attention and final probability normalization? This asks about the new
external learned comparator, not about the existing native pyramid merge.
No actual-weevil softness attribution follows from a symbolic example.

Root ran `python -B scripts/research.py search 'source-count dilution' --limit 6`
and `python -B experiments/ORCH-drift-check/prior_art.py 'source-count dilution'
'duplicate source' 'StackMFF multiplicity'`, both exit zero. The mechanical
search found no exact matches; the unified search surfaced V-DILUTE. Root read
that report's verdict and commissioning. It rejects dilution in the old native
299-frame pyramid, whose noise gate suppresses almost all fine-band competitors.
Do not reopen that claim or transfer a different model's behavior to it.

The pinned MIT V3 model and its source hashes are in the adjacent
[current comparator](../stackmff-v3-current/brief.md). Its f32 two-scale default
full-weevil observation is still running unchanged. The existing generated
screen contains an all299 constant check and a five-source structured check;
those do not by themselves establish focus discrimination for a deep stack.

Owner cfa-residual: read only permitted pinned inference code and retained
reports. Write `source-audit.md` here. Derive equal and unequal duplication
behavior through the actual inter-source attention and final fusion. Identify
any positional, source normalization, pooling, clipping or grouping operation
that invalidates an intuitive invariance. State a falsifier and one small known
positive/null fixture if a future numerical question is warranted. Avoid a
temperature, source-subset or parameter sweep recommendation without photographic
evidence. No implementation, image/RAW reads, GPU job, model alteration or new
quality claim is authorized by this source audit.

Root selects any next action only after the complete current photograph and
independent review. A possible mechanism is not a demonstrated cause.
