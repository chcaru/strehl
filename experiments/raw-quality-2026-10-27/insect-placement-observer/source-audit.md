# Independent CLI / adapter source audit

2026-10-27. SOURCE REVIEW only by the core observer author, independently of
the CLI / adapter author. No RAW decode, compile, numerical control or actual
alignment was executed by this reviewer. No source blocker found in this
checkpoint; execution remains conditional on the root-run mechanical controls.

Reviewed bindings:

- `crates/strehl-cli/src/align_cmd.rs`:
  `e39b7915306f2e899d856e09f1d2fa0cb2ff3e4a8abd83bbaf0f4ac267af15df`
- `adapter.rs`:
  `741766134465da8912c5868c111db2e2368b4cd6c712a7752150ccd14b33c365`

`measure_edges_traced` preserves the existing parallel pair iteration and
returned `filter_map` edge order. The added ordinal is used only for receipt
ordering. Missing reference/moving pyramid or plane receives an explicit
unavailable reason. Core failures are captured before the existing `.ok()?`
edge admission. The collector runs once per attempted pair after its ordinary
progress completion. No NCC, fit or residual is recalculated for export.

The enabled branch calls the same core observed implementation; the ordinary
branch still calls `align_pair`. Actual similarity, RMS, used count and lever
populate the edge. The normal measured-component, cycle-floor, global solve,
heldout calculation and warp assembly are shared through
`finish_measured_map`; the experiment does not implement another solver.

The adapter pins all 299 ordered original file identities, executable, config
and held map. It decodes the ordinary green guides once, hashes them before
and after, and records the actual deep configuration, reference149, spans and
Catmull map. Its four additional off-only fits rebuild small pyramids from
already decoded guides and compare against the corresponding retained on
result. This is four extra pair fits, not another complete alignment or decode.

All stage/tile float fields are serialized with original bits and a finite
number or null. Refusal reasons, unavailable data, uncomputed masks, failed
later passes and the selected previous-good pass remain distinguishable. The
2340 records are sorted by pair ordinal only after measurement. Trace storage
and JSONL bounds reject incomplete export; they do not produce a successful
truncated population. The isolated output path and `STREHL_WARPMAP` are checked
before any map write. Original, guide and bound-input preservation is checked
again before the successful receipt.

The map comparison is correctly descriptive: a different historical map does
not become an observer failure by itself, while four-pair bit inequality or
changed input bytes makes the mechanical result fail. Historical exactness
would show consistency with that pinned map, not physical correctness. Input
guide hashes establish nonperturbation, not independent commissioning of
green-guide construction. The separately owned coordinate/phase controls must
test that construction and the fitting-centre convention.

The receipt has no placement or photographic-quality admission. It preserves
actual refusals and does not nominate focused truth by NCC peak or survivor
RMS. The later crossed-support/defocus identifiability question remains open;
successful tracing alone does not justify a richer warp or a new full render.
