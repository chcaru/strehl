# Signed RAW whole-path smoke

MEASURED on2026-09-09. Source6318ae3b, commandd88bba62. Actual invocation: selected Python312 `-I -B experiments/native-signed-black/run-smoke.py`. The earlier `-I -S -B` invocation exited1 before creating an output directory or launching a child: the existing Job helper imports tifffile, which -S hides. The ordinary isolated invocation retains installed libraries and succeeded. No source correction or scientific rerun was needed.

Fresh target compilation printed Compiling for strehl-core, strehl-cli, strehl-raw and strehl-plugin. Build wall60.422s, owned Job CPU111.0625s. Existing helper performed its recorded compile-only owned descendant cleanup after Cargo zero exit and pipe EOF. Debug costs, not product performance.

The exact copied test executable ran the ignored signed_cfa_whole_path_smoke with STREHL_SIGNED_BLACK=0 then1, RAYON_NUM_THREADS=4, remaining STREHL/RAYON and numerical thread overrides cleared as recorded. Both exit0; wall0.422/0.172s and owned Job CPU0.28125/0.34375s. Two consumer calls per invocation, four total, three generated padded u16 frames per call. No original RAW or warp traversed.

The signed negative case actually consumed36864 negative CFA values and asserts every collapsed sample is -8 within1e-4; the baseline asserts zero. The positive companion asserts8 in both arms. Saved collapsed_constant is the asserted expected value, not a separately computed mean. Both negative-output and positive-output whole TIFF pairs are byte-identical, each74331bytes. The writer still clips negative values. This verifies transport and writer consistency for these constants; it does not measure noise, image quality or speed.

Eight remaining consumer calls are allocated to four baseline/signed comparisons: zero/dim regions, nonnegative focus-varying structure, spatial noisy flat, and low-signal focus-varying texture/depth. Actual f32 outputs and TIFFs will be independently scored. No default promotion or sensor gain change.
