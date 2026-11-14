# Lossless RAW destination storage

Question: retain the production CFA/Zstd transfer bytes on the receiving PC,
default on, without compromising exact recovery, acknowledgements or RAW import.

Prior work: `sony-raw-compression-2026-11-12`, `sony-transport-2026-11-12`, and
`sony-a7cr-2026-11-13`. Research search and mechanical prior-art search were run
with `RAW compression archive`; the retained experiments supply the relevant
implementation and measured hardware evidence. This is storage qualification,
not an image-quality experiment or SYNTHESIS fold.

Scope: one shared bounded codec, a self-contained `.ARW.straw` container with
original length and SHA-256, receiver configuration and UI, exact ARW restoration,
and automatic import through Strehl's RAW decoder and discovery paths. Preserve
all existing captures. Old registered runs keep plain-ARW storage; a setting
change applies only to new runs. No Pi transport/protocol change is required.

Controls, exercised before performance conclusions: wrong checksum, truncation,
oversized headers, trailing bytes, corrupt stored duplicate, conflicting file,
old configuration/index migration, retries after lost acknowledgement, settings
toggle during a registered run and restart. Positive control: a genuine A7CR
pixel-shift RAW, byte-exact restore and complete decoded-CFA comparison with its
original. Identity transfer and compression-off are the null arms.

Bounded qualification: existing A7CR files read-only; separate test destinations;
at most one new four-shot physical group. No long soak or independent research
review claimed. Record actual commands, source/build hashes, timings, receipt
sizes and host environment. Finish with deployed default-on receiver and visible
UI checks, no active test stack or pending Pi transfer.
