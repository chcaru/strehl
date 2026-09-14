Both mean arms retain the later joint-inputs arithmetic: signal multiplied by
WB and then the rounded f32 reciprocal of range. The matched-source observer
instead evaluates signal times WB divided by range. This changes 6,195 of
153,664 measured CFA samples by floating-point rounding; it is not a decoding
or CFA-parity discrepancy.

The earlier joint-raw-samples-2-independent.json check proved exact retained RAW
decoding and exact reconstruction of the matched-source observer's division
normalization. It did not prove bit equality of the later joint-inputs rounded
reciprocal arithmetic. Its coordinate and raw-sample checks remain applicable.

Attempt1 preserved the joint arithmetic but incorrectly demanded bit equality
of known samples across these two normalization expressions; it stopped before
writing means. Attempt2 preserves the same image arithmetic and separately
compares identical normalization. All153,664 measured sites then match exactly.
The M95 SciPy MHC port versus actual Rust MHC has maximum f32 difference
7.152557373046875e-7 and RMS3.693522496581018e-8 under identical normalization.
The product developer reproduces the held MHC TIFF exactly. No RAW or joint
solver run was repeated to resolve this arithmetic distinction.
