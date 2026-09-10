# Coordinate extension refusal and cheaper compiler preflight

MEASURED: build-native-5 completed139.234wall seconds from
4a1974e8f7c74386e3499be977fc585383c88880 with fresh compilation. CLI SHA256
3558816d6eebcb4a8b81e68d4160ce0fb99338c2d8656abb7c7689d4f2d66ac0;
test executable2913e873f19e14407c0cabf5d3bcac702a6c29cd8119a7bda935bde9e3d150b1.
Actual commands:
~~~powershell
python -I -B experiments/native-pyramid-profile/build.py --gpu-gather --output-dir experiments/native-gpu-gather/build-native-5
python -I -B experiments/native-gpu-gather/run-device.py
~~~

Run-device-3 again passes192 guard predicates and the subnormal witness.
Original GLSL/IR and emitted SPIR-V parse/IR validation now complete, but the
additive compiler adapter refuses an unexpected existing extension. The run
does not record its name; do not present the name inferred below as a captured
runtime field. No coordinate dispatch or image pair occurs. The later37+4,
18 and native groups remain unexecuted. Status remains CONTROL_FAILED.

Test process0.500wall/0.21875CPU seconds; terminal accounting/normal owned
process cleanup, exit101. Report SHA256
fcd268f5016999ddfd5da2f9346a8f828ed68ac3b987a3f9ae64ce2165e4d0ac.

DERIVED from independently inspected installed Naga30 writer.rs3707-3710:
version<1.3 plus storage buffers causes
SPV_KHR_storage_buffer_storage_class emission. This fixed owned module uses
version1.0/storage buffers. The narrow repair accepts exactly that canonical
original extension in its proper section, preserving it and adding the
separate float-controls extension after it. Other/duplicate/malformed
extensions remain errors. The next actual report must retain original names.
No formula, control, precision or image shader changes.

The repeated full-CLI links are an avoidable development cost. Add one small
constructor-only example and a bounded preflight before another full build.
It tests shader generation/validation and GPU pipeline creation, no descriptor
or image dispatch. It cannot replace the fixed equivalence controls.
On preflight success, build-native-6/run-device-4 repeat the unchanged guarded
control sequence before any native TIFF. Preserve every preceding failure.
