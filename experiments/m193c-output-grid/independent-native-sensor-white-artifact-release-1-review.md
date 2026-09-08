# Independent read of the actual artifact-parent release

Root reviewed the preparer source independently, pinned its final22431-byte
version at `2e46a73af2381ca86878a07f57ec3269a955d3a8937a027e4de83e11f6bc0829`,
and invoked it once with the reviewed parent/spec, actual white1 audit and
explicit source/review/root metadata hashes. It returned actual exit0 and
`PREPARED_METADATA_ONLY`. No subject or image operation ran in preparation.

Actual release:67113 bytes, SHA256
`ad8b391f54d3fd10843a75e4515a8344b5e2b903145d5f256c0248f7758e95ec`.
Preparation:24137 bytes, SHA256
`a12f20f7a014223f3732e50e5d99330c40204389faecdc1d7fdb1036326f5c69`.

The independent metadata read actually ran from the repository root:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B experiments/m193c-output-grid/work/read-native-sensor-white-artifact-release-1.py --release-sha256 ad8b391f54d3fd10843a75e4515a8344b5e2b903145d5f256c0248f7758e95ec --preparation-sha256 a12f20f7a014223f3732e50e5d99330c40204389faecdc1d7fdb1036326f5c69
```

It returned exit0 and `PASS_METADATA_RELEASE_READ_ONLY`:280 distinct actual
files,153 sources,145 inputs, exact parent/nine-reader commands and17 planned
new children. All150 prior sources and118 inputs remain bound. The old parent
refusal and successful first reader are separate preserved records. The sole
primary reuse remains original native1's first primary; no prior reader result
is substituted for a new reader.

Carry is50.46875 CPU seconds,45.1272058 wall seconds,244506315 file bytes and
7677264 metadata bytes, including the additional one-MiB reservation. The
actual inventory is167955 bytes. Inventory plus actual preparation,128-KiB
release allowance and192-KiB future allowance totals519772 bytes, below1048576.
The actual release fits its allowance. The future scope explicitly includes
the forthcoming independent actual-audit source/report and root metadata.
These are conservative reservations, not measured future scientific work.

The three administrative documents remain absent from scientific inputs and
sources; only their positive extent growth is charged. Exact old-reader,
runtime, producer, private gate and reuse bindings are unchanged. Original0
must again pass fresh full-plan identity and independent reading. All eight
later frames remain unvisited until the released parent actually reaches them.

VERIFIED by source and actual metadata inspection: no release blocker found.
Root may commit this package and invoke its sole parent command with the
actual release SHA. The new artifact controls have not yet run, and this
review provides no nine-frame, coverage, calibration or quality admission.
