# Guarded shader interface refusal

MEASURED: build-native-4, source555e6a50f4ab6195304bd578b6b5ffe8a8b2933d,
completed139.875 wall seconds with fresh compilation. CLI SHA256
1cd646ee397cd46d4573883585efe7e3337ef0ef7b67195399ad342ddc675d88;
test executable c75285b1c5bc0ca4915c3a98442e45c4f74e854cf8ff9ed1e3dfa450cdd8588e.

Command actually run:
~~~powershell
python -I -B experiments/native-pyramid-profile/build.py --gpu-gather --output-dir experiments/native-gpu-gather/build-native-4
python -I -B experiments/native-gpu-gather/run-device.py
~~~

Run-device-2 passes all192 literal coefficient predicates and the independently
expected minimum-subnormal cancellation witness. Hardware admission succeeds
under the guarded policy. Naga parses the GLSL, but its IR validator refuses
the writeonly Plans storage buffer with StorageAddressSpaceWriteOnlyNotSupported.
The four paired image cases, original37+4 descriptors, original18 images and
all native renders remain unexecuted. This is a compiler-interface refusal,
not an image mismatch, GPU speed result, or failure of the coefficient proof.

The process cost0.515wall/0.265625 child CPU seconds, with terminal accounting,
no execution error/cleanup issue and preserved Rust test exit101.
Report SHA2568bdc4b12d8c8691fc457ad676351b1168fb8e7f09bed8c1c8d2981f35901866c.
Predicate success does not change the overall CONTROL_FAILED status.

Prospective narrow repair: remove only the GLSL writeonly qualifier so the
plan storage interface is read/write, matching the existing wgpu writable
buffer layout and Naga's supported storage address space. No read operation,
formula, precision mode, fixture, bar or population changes. The original
and strict f32 image shader hashes remain mandatory. Freeze a new source
revision and use build-native-5/run-device-3; keep this failure intact.
