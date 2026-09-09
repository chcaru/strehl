# Independent results — exact GPU gather controls

VERIFIED from saved run-3 records: all 18 fixed primary cases pass on NVIDIA GeForce RTX 5090/Vulkan, with zero consumed-u16, coverage or outside-storage mismatches. No reviewer numerical execution was performed.
The passing population contains 59,504 consumed codes, including explicitly uncovered sites; this is an operator-equivalence count, not a photographic-quality sample count.
All 25 shader quantizer operands pass. Case4 supplies 2,990 actual half ties; case5 supplies 114 negative and 1,449 upper-clamped excursions, and the green-only case retains its corresponding live excursions.
The source-address, green-phase and coverage destroyers change 1,490, 1,360 and 1,500 codes respectively; the last also changes 1,500 coverage bits. The comparison demonstrably rejects these faults.
Both ordinary/actual-observer/sentinel-observer complete-storage hashes match: RGB b90b508b783ae3fb4ea4c82386ae5ddce88d5290eed1aeab40f0a84f9826c6c8; green 7e35c41dd1e66b434a3462cd2b99b6167da36b596f2339754ea384a20127cb8f.

The strict module applies 30 NoContraction decorations: 8 FAdd, 17 FMul, 5 FSub. Both arms report original SPIR-V SHA256 41658a89bd9b17c73b0f452b48bde689679e4ecc50774872ebfff0171cdb6560 and decorated SHA256 a7dce2107ce7713ac4d9cd961dd44e303bd69b37c2d2ca7029f20aa1f131de9d; submitted hashes select the intended arm.
The separate undecorated case3 reproduces run2's sole R(26,2) mismatch: CPU 3478 versus GPU 3477, CPU pre-round operand 3477.5. Strict case3 is exact; descriptor, coverage and adapter agree.
This controlled contrast supports an effect of the NoContraction restrictions on this generated module/input. It does not distinguish contraction from reassociation, identify a particular instruction, prove a driver defect, or establish cross-device floating-point equivalence. The diagnostic never enters or rescues primary acceptance.
Naga WGSL/IR and SPIR-V frontend/IR validation plus structural decoration/removal identity completed through the actual constructor. This remains distinct from SPIR-V Tools validation: no spirv-val execution is claimed.

Bindings verified: all 21 build6 source entries match; fresh compilation logged both GPU library and strehl-cli. Executed revision afa545a493f7beb7750dc758689099e5702d4d7d, test executable SHA256 1c85c95cd83201307030817c570c04b56a825d63c31d97d8311db842114de7e8.
Against the source reviewed in strict-review.md, the only normalized helper change is max_storage_buffer_binding_size u32 to u64, plus line endings. The shader arithmetic/control inputs remain unchanged; current helper SHA256 a904c1017c051e3285390a5e714e797720cab6a150a27e15c1aefc3a3145a65e.
Run3 exited0 with no intervention or cleanup errors, terminal accounting, 0.500 child CPU seconds, 0.891 wall seconds, and 613,158,912 bytes peak Job commit. These are complete control-process costs, not kernel timing or a speed comparison.
Build6 separately cost 113.687 wall seconds and 224.421875 child CPU seconds; prior failed builds/runs remain separate preserved costs, not erased by this pass.
Reported binding limit 2,147,483,644 bytes and buffer limit 4,294,967,295 bytes admit the proposed 395,592,192-byte native RGB buffer by size. This is capacity admission only; no native allocation, RAW decode, actual merge integration, complete TIFF comparison, performance gain or SOTA claim follows.
Decision: advance the strict prototype to the already-planned actual consumer integration with exact controls retained. No production default promotion is justified by these tiny generated cases alone.

Primary result SHA256 b9b15325198bd035e797511bef2ae4486fe695b5c0628d90304d4c53cb75c661 (14,099 bytes); process receipt SHA256 40235e641f566af69000d9fbc50702aea73ae84441d2714249479b6c49b19159; build invocation SHA256 166a4760f1dc314c7b906e94fe93ec622f50531a5cc1647d8bac81a4e60c872a.
