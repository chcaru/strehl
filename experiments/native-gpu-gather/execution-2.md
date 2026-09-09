# Explicit shader arithmetic — bounded repair

Run2 executed all18 primary cases on RTX5090/Vulkan. One R code in synthetic-CA
case3 differed by1; the CPU pre-round value is exactly3477.5. All coverage,
literal quantizer, live descriptor mutations and CPU observer hash arms pass.
This establishes a numerical mismatch, not contraction as its cause.

Implement validated owned WGSL to SPIRV, preserving bounds checks and applying
NoContraction to relevant float operations. Require explicit Vulkan and shader
passthrough support. Check SPIRV instruction/result/annotation structure,
decoration completeness, and removal of the added decorations restoring the
original words. Refuse fused Fma or fast-math escapes. No untrusted shader input.

Build5/run3 keep the previous compile/run ceilings and all18 primary inputs and
exact pass criteria. Add one separate undecorated SAME-generated-SPIRV case3
diagnostic to distinguish compilation-route change from decoration. It is not
required to reproduce the oldroute mismatch and cannot rescue a primary failure.
If it does not reproduce, a successful strict result is a repair, not causal
proof of the original failure. Preserve original receipts and all new hashes.

Source review and committed source precede execution. No native RAW decode,
timing campaign, arithmetic tolerance relaxation or production default change.

Build5 found the new adapter-report field used u32 while wgpu30 reports its
storage-binding limit as u64. Preserve that exact u64 type, rebuild as build6,
and use it for the unchanged run3. No shader arithmetic or input changes.
