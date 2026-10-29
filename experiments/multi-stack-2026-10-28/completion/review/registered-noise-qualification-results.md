# Registered source-only temporal qualification

MEASURED,2026-10-28. The real-noise outcome remains active. This stage qualifies original-sample signal stability before measuring candidate noise; it has not measured delivered noise or claimed an RGB benefit.

The root implemented [registered-noise-qualification.rs](registered-noise-qualification.rs), linked against the exactly recorded frozen13 default CLI/core libraries. It uses the production bounded RegionSampler, saved native HDR geometry, current original-u16 cache, explicit optical profile, calibrated exposure gains and the existing injected sensor noise model. One original is gathered at a time. It never constructs an aligned source volume or decodes RAWs. Each128-quad region contains nine fixed32-quad subtiles. The four regions come from the previously frozen gray-ramp, QR, low-contrast dots and adverse-flare witnesses; no result-derived relocation occurred.

The actual qualification function is exercised on flat noise first, followed by illumination drift, translated2-D texture and changing blur. Initial build02/run01 rejected too many known flat controls:16/72 accepted. The two-frame validation maximum had been compared to0.5 raw-sample sigma despite a5x5 box and five-frame guide mean predicting a95th-percentile null near0.546. That failed commissioning receipt is retained. The revised0.65 bound includes finite-spatial-sample margin; all72 flat tiles pass, and all72 cases of each adverse stimulus refuse. The source-only real qualification uses original-sample model sigma. A full-frame finest-band transfer factor is recorded separately; it is not reused as the variance of the spatially smoothed local guide.

Registered20-step and8-step focus spans still qualify0/36 complete four-component tiles. This is narrower than a conclusion that no useful repeats exist: small regions retain changing texture, structure, or focus response, and the noise model itself has not been validated by these observations. No measurement originals were loaded by either stage. All failures remain in outputs/multi-stack/completion/registered-noise-qualification-02 and03. Exact source bytes for builds03/04 are archived with their verified build hashes; build01 was an API-arity compile failure and build02 the failed flat commission.

A subsequent fixed census uses six windows beginning at12,20,28,36,44,52. Each window has five even-ordinal guide originals, two validation originals at offsets1/5, and two proposed measurement originals at offsets3/7. Across this census, measurement ordinals are globally3 modulo4 and disjoint from all guides/validation; each same-index long-exposure partner is offset62 in the saved session census. Existing geometry and photometry remain frozen, and qualification is conditional on them. Some photons were used in earlier, failed source-only investigations, so these are not globally unseen captures. The current algorithm does not read the measurement photons or output variance during qualification.

The exact per-window/per-component accounting is in [registered-noise-qualification-summary.json](registered-noise-qualification-summary.json). It finds mostly red-component support in the gray field and two blue-component supports in the adverse-flare region. Green and full-RGB qualifications remain absent. These component masks must remain explicit in any subsequent assay; red support cannot become an RGB noise claim. Two temporal samples per window are also not a large independent temporal replicate population.

Commands actually run, with full command, executable hash, host load, process resources and exit status in each run-command receipt:

```powershell
python experiments/multi-stack-2026-10-28/completion/mosaic/build-native-replay.py --fingerprint target/release/.fingerprint/strehl-cli-d1b5ff31056b7cf3/lib-strehl_cli.json --out outputs/multi-stack/completion/registered-noise-build-05 --source experiments/multi-stack-2026-10-28/completion/review/registered-noise-qualification.rs --bind-source crates/strehl-cli/src/session-reconstruction-sampling.rs --bind-source crates/strehl-cli/src/session-sampling.rs
```

For each base12,20,28,36,44,52, the executed program was:

```text
registered-noise-build-05/registered-noise-qualification.exe hdr-precision-03 hdr-source-cache-current experiments/multi-stack-2026-10-28/review/hdr-roi-mapped-frozen.json registered-noise-window-BASE-01 BASE
```

All abbreviated artifact paths above are under outputs/multi-stack/completion; the receipts contain full arguments. Every census run used4 workers, a2GiB limit, zero RAW decodes and about144MB sampled private memory, and completed in4.57–4.64s while other work ran. These are capability observations, not isolated timings. Executable SHA256 is cc877020463fedd51078a1b4fe06df1acd8a0e8a40223041711b5ff458aa9579. The source archive is in registered-noise-build-05.

Next is a separately commissioned actual-consumer paired-output assay on the frozen eligible components, with signal-transfer and motion/blur counterexamples, explicit two-sample/window uncertainty, and comparison to both exposures. A source qualification, interpolation beta or weighted-mean formula is insufficient to close the real delivered-noise outcome.
