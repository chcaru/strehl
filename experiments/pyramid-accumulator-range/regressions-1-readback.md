# Root-run accumulator controls: results and scope

MEASURED by root, reviewed from retained `garnet-spatial-trace/regressions-1/{results.json,process.log,process.json,invocation.json}`. The exact invocation was `garnet-spatial-trace/build-2/core-tests.exe pyramid::accumulator_range_independent::independent_ --nocapture --test-threads=1`. Build2 contains fresh `Compiling strehl-core` and `Compiling strehl-cli` lines. Build1 remains retained: it found the test author's wrong `crate::Levels` import; root corrected it mechanically to `crate::noise::Levels`. Executed test source SHA256 is `e13029746a45f7baac018e976e88ddfc6176d01f46f0cbd99694f37b0f29d6ee`.

Four tests ran, producing the registered five case observations. Exit101 records three failing safety tests and one passing flat/midtone test. The job completed normally without cleanup errors. This is a confirmed arithmetic defect, not a passing quality screen.

| Case | Nonfinite numerator | Nonfinite denominator | Nonfinite pre-hull | Nonfinite final | Maximum final difference from f64 reference, DN |
| --- | ---: | ---: | ---: | ---: | ---: |
| Flat | 0 | 0 | 0 | 0 | 0 |
| Midtone | 0 | 0 | 0 | 0 | 0.00012207031 |
| Distinct high-DN pair, variance4 | 262143 | 0 | 262143 | 0 | 305.50977 |
| Identical high-DN pair, variance4 | 262143 | 0 | 262143 | 0 | 0 |
| Distinct high-DN pair, ISO100 profile variance | 65534 | 0 | 65534 | 0 | 0.001953125 |

Every high-DN failure is at the preregistered assertion that a finite source/weight must not produce a nonfinite weighted numerator. The independent emulation of the legacy f32 sum reports the same counts. Individual weights remain finite (maximum5.5406225e34), as do coefficients (maximum8320.3125DN). The identical-source image identity check passes before its internal-state assertion fails, directly establishing the final-hull masking failure. The profile-noise fixture also fails; its outcome was intentionally not prescribed, and the tiny final image error does not clear the bad internal state.

These controls share actual decomposition/weights and re-choose accumulator precision. They establish overflow in this actual consumer and that final-image finiteness/identity can hide it. They do not yet establish the cause or spatial extent of the photographed garnet rectangles, evaluate focus selection, or validate the camera calibration. The real-stack census is the separate transfer check.

## Runner source review

Reviewed frozen `garnet-spatial-trace/run.py` SHA256 `982a320750c5c6f5e94f9bfe87cb279ea93c573c5b6ad077c6282f71e7bef88b`. It binds source files and retained executables, requires fresh core/CLI builds, confines output directories, uses bounded jobs with sanitized environment, runs the actual full current183-source adapter, and retains its historical baseline pixel assertion. The independent read of the actual on/off `bindings.json` files confirms identical source lists, recipe and executable, with opposite observer flags. No observer run was executed by this reviewer.

No blocker found for the current recorded runs. After their freeze is released, harden two future-run checks: require exactly four named tests and all five unique expected case records before declaring a regression success; compare on/off recipe and source bindings explicitly as well as the executable. The current regression artifact already contains all four tests/five cases, and the current on/off bindings already match those additional comparisons. A red regression remains an explicitly recorded failure, never a quality-admission pass.
