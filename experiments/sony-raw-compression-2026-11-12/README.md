# Sony RAW compression experiment

Read [results.md](results.md) first. This is a source-inclusive local research
prototype, not an update to the running camera controller. It does not trigger
exposures. Windows analysis uses Python 3.12 and the pinned dependencies in
`requirements.txt`. Pi transport uses Python's standard library, system Zstd
and the included Rust predictor; it needs no NumPy or RAW decoder on the Pi.

The package preserves repository-relative paths. Extract it to an empty folder
and run commands from that folder. The public source RAWs (about 2.46 GB) are
not included; `fetch-samples.py` downloads the files offered by the named author.
The public download inventories and native builds are under
`outputs/sony-raw-compression-2026-11-12/` in the package. Do not use Python's
`-O` option: this research harness uses assertions as validation gates.

## PC controls and comparisons

```powershell
python -m pip install -r experiments/sony-raw-compression-2026-11-12/requirements.txt
python experiments/sony-raw-compression-2026-11-12/advanced.py controls
python experiments/sony-raw-compression-2026-11-12/wire.py controls
python experiments/sony-raw-compression-2026-11-12/extra-controls.py
python experiments/sony-raw-compression-2026-11-12/fetch-samples.py
python experiments/sony-raw-compression-2026-11-12/bench.py --suite spatial
python experiments/sony-raw-compression-2026-11-12/bench.py --suite temporal
python experiments/sony-raw-compression-2026-11-12/advanced.py spatial
python experiments/sony-raw-compression-2026-11-12/advanced.py temporal
python experiments/sony-raw-compression-2026-11-12/entropy.py
python experiments/sony-raw-compression-2026-11-12/video-bench.py
```

Redirect each command's stdout to a distinct JSONL receipt if rerunning; capture
`$LASTEXITCODE` immediately and require zero. `video-bench.py` locates the tested
WinGet FFmpeg installation and invokes its binary; FFmpeg is not bundled.
The already-compressed camera fallback test reads three existing ARWs in
`D:\StrehlCaptures`; it is optional and those private files are not packaged.

The original broad `bench.py` spatial/temporal sweep used the preserved v1
native build. The later advanced, AEC, Pi and wire tests used v3. See the
preserved source snapshots/build receipts when comparing historical timings.
Current source defaults to v3; the byte-reconstruction requirement is unchanged.

## Building the Rust predictor

There are no third-party Rust crates in `predict.rs`.

```powershell
rustc --edition 2021 --crate-type cdylib -C opt-level=3 -C target-cpu=native experiments/sony-raw-compression-2026-11-12/predict.rs -o outputs/sony-raw-compression-2026-11-12/predict-v3.dll
```

On Linux ARM64, compile the same source as `libpredict.so`. The measured build
was cross-compiled in Debian WSL using Rust 1.98.0:

```text
rustc --edition 2021 --crate-type cdylib --target aarch64-unknown-linux-gnu -C linker=aarch64-linux-gnu-gcc -C opt-level=3 predict.rs -o libpredict.so
```

The packaged Windows DLL was built for the measurement PC's native CPU. Rebuild
on another Windows CPU if needed. `wire.py` accepts `STREHL_PREDICT_LIBRARY` to
select another native-library path. The DLL/shared object are this experiment's
own reversible predictor; no camera SDK or RAW decoder is bundled.

## Repeating the Wi-Fi test after EDUP arrives

The Pi runners refer to this workspace's existing SSH identity and known-hosts
file under `outputs/pi-capture-2026-11-11/private/`. Neither is packaged. They
are convenience runners for the already provisioned Pi, not installers for a
different machine. The Pi camera service remains running and is not controlled
by these scripts. Run only while no stack is active, so the test does not compete
for its RAM/CPU/network.

`run-pi.py` copies two public ARWs to `/run/strehl-compression-20261112/` and the
shared object to `/home/strehl/strehl-compression-probe/`. The helper creates the
owned tmpfs-backed directory if needed, checks that swap is disabled, and refuses
an active camera session. RAWs are not copied to the Pi's SD filesystem. The
code directory contains only code. The public RAM
copies may need to be uploaded again after the Pi reboots or final cleanup.

```powershell
python experiments/sony-raw-compression-2026-11-12/run-pi.py --prepare-only
python experiments/sony-raw-compression-2026-11-12/network-bench.py --label edup-first > outputs/sony-raw-compression-2026-11-12/network-edup-first.jsonl
```

Use a fresh label on each run. Each replay performs six transfers in alternating
order, reconstructs each original ARW, fsyncs, renames and independently verifies
the saved file's SHA-256. It writes about 738 MB of **new test output on the PC**.
It does not put those test outputs in the configured production capture folder.
The link test uses SSH, not the production HTTP endpoint. `run-pi.py` writes the
same exploratory `pi-bench-v3.jsonl` output name; the original receipt is frozen
under this directory's `evidence/`, and the original source is also preserved.

## Actual commands and artifacts

The commands above were run with the default flags shown. Successful stdout
receipts are preserved under `evidence/`; `summarize.py` re-hashes inputs and
recomputes the aggregate table. Additional actual commands were:

```powershell
python experiments/sony-raw-compression-2026-11-12/current-camera-bench.py
python experiments/sony-raw-compression-2026-11-12/resource-bench.py
python experiments/sony-raw-compression-2026-11-12/summarize.py
```

`network-bench.py` originally ran without a label and saved to
`outputs/sony-raw-compression-2026-11-12/network-roundtrips/`. A subsequent change
adds labels to avoid overwriting receipts on the next adapter test; its measured
version is retained in `outputs/.../measured-source/`.

No RAWs, embedded photographs, private SSH material, Wi-Fi credentials, pairing
keys, Sony SDK files, or Python codec binary dependencies are in the ZIP.
The project's MIT/Apache-2.0 notices apply to this experiment's original code.
Dependencies and FFmpeg retain their own licenses and are installed separately.
