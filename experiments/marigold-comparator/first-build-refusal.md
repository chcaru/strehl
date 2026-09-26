# First wrapper refusal, preserved

MEASURED, 2026-09-26. `run.py build` compiles the new example successfully in
32.563 seconds and copies the executable, then refuses its immutable-input
check. Exactly one captured binding changed: independent-review.md grew from
3867 to 3879 bytes. The reviewer confirms twelve readability spaces were added
after the draft had been exposed for binding. No Rust source or runner changed.

Captured review SHA256:
391ca20fda4f73d36af77e57872dacabb676fa8aa5025eb17540eb230831bcce

Final review SHA256:
16b19666a49b58d6b23aa5702ff4d1fc45ba2408ba4fb9b327a5951aed14c9f9

The root's prematurely issued `run.py develop` invocation also refuses that
same binding, before creating a development stage or reading any capture. Both
wrapper errors are preserved in the conversation; run-1 retains the actual
compiler log/process receipt and original source manifest. It has no validated
executable.json and will not be used for development.

The reviewer has ceased editing the pre-run file. Root will use a fresh run-2
build with unchanged code and the final frozen note. This is a build-input
repair, not a vendor retry, quality-threshold change, or retrospective rewrite
of the original manifest. All later result reports must use separate files.
