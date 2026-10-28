# Unchanged-green residual follow-on closed

MEASURED by root, read back2026-10-26 from outputs/raw-quality-2026-10-26/cfa-residual-control.log. The named test align_cmd::cfa_residual_tests::unchanged_green_residual_falsifier ran on the rebuilt release CLI test executable strehl_cli-264609018c3d479f.exe. Root owns the full invocation/build environment; this child did not execute Cargo. The log shows Compiling strehl-cli, release build1m56s, and one passing mechanics test in0.16s. Passing the Rust assertions is not a quality pass.

Flat controls ran first: empirical/independent expected variance ratios1.013393 at1000DN and1.014309 at4096DN. The fixed neutral0.30cycles/native-pixel,73degree,pull1 witness scored1152 measured-green output sites:

| Arm | Green-site RMSE, DN |
| --- | ---: |
| Prior MHC/Catmull gather | 35.00527951919751 |
| Direct cubic green | 67.08867011440522 |
| Direct green with perfect R/B oracle | 67.08867011440522 |

Direct/prior ratio is1.916530050206073. The perfect-R/B oracle leaves the measured-green values bit-identical through final MHC. The emitted decision is UNCHANGED_GREEN_EXTENSION_CANNOT_REPAIR_THIS_FAILED_GREEN_WITNESS. This exceeds the fixed1.05 scheduling kill bar; close this unchanged-green color-residual mechanism without implementation, another sweep, or a full photograph. R/B improvement cannot rescue this identified green defect or the unchanged green merge guide. This does not refute all colour-difference or original-CFA reconstruction methods.

This is a retrospective generated counterexample, not a photographic result. No quality improvement, full-stack output, or SOTA progress is claimed. Completed sampler/control sources remain unchanged.
