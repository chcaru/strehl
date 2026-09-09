# Independent strict-SPIR-V source review

Source-only review for the fixed 18 controls; no reviewer build, shader execution or new numerical measurement.
Run 2 remains a recorded exact-equivalence failure: one R (26,2) output in case 3 is 3478 on CPU versus 3477 on GPU, with CPU pre-round value 3477.5. All coverage/literal-quantizer/descriptor-mutant/observer controls passed; this does not identify contraction as the cause.

The helper accepts only the embedded owned WGSL. It parses and validates that module with Naga, fixes three compute entrypoints and six binding/access declarations, and emits SPIR-V 1.0 with explicit Restrict index/buffer policies.
Installed Naga 30.0.1 source confirms Options::default enables force_loop_bounding and emit_int_div_checks; the report wording is supported by that pinned dependency.
The patch scans instruction lengths/opcodes and header, rejects existing fast-math/NoContraction and fused Fma, and targets unique in-bound f32 arithmetic result IDs.
Annotations are inserted before the first type. Their targets/counts/location are checked; deleting exactly those annotations must restore the original word stream byte-for-byte. Kernel operands, bounds code, IDs and binding layout remain unchanged by this patch.
Original and decorated modules are reparsed through Naga's SPIR-V frontend and its IR validator. That frontend is separate from the emitter but part of the same implementation; it ignores NoContraction, so its result is never re-emitted.
This is Naga validation plus a structural annotation/removal check, NOT SPIR-V Tools/spirv-val validation. The helper states that limit; no spirv-val result exists.
The unsafe passthrough is confined to the private helper and these generated words. Device creation requires discrete Vulkan hardware and PASSTHROUGH_SHADERS; no external shader/path input reaches it.
Khronos defines NoContraction to prohibit contraction and reassociation, but decorating a module alone does not prove CPU equivalence or cure any already transformed operation. The unchanged exact controls remain decisive.

The optional undecorated case 3 uses the same fixed input and CPU comparison, after dropping the primary GPU object. Errors/panics are retained separately; it neither gates nor rescues the primary 18 predicate.
Before attributing a difference to decorations, require matching original_sha256, matching decorated_sha256/operation counts, primary submitted_sha256=decorated_sha256, diagnostic submitted_sha256=original_sha256, and the same adapter/backend.
A strict pass with a reproducing undecorated mismatch supports a decoration effect on this consumer. If undecorated does not reproduce run2, the original route's cause remains unresolved; do not turn that into a mandatory diagnostic failure.
No remaining source-review blocker identified at the following held hashes. Runtime validation and numerical acceptance are still root-owned and prospective.

SHA-256: strict-spirv.rs: 93156f03740dd6e6b5de8ccbe524a6cab96e6b5321d8e5d960ebff8446361415; lib.rs: 3e1af4d6fe5c8879610061036da0543102790f9ff252166dd2ed5cb8b4358479; independent-tests.rs: 43036526435b7774fc9609f0872c27e25107838016831c600a1084f65ef4747d; unchanged gather.wgsl: dbf900189081c839f67d103a555d27d9ec4a8165a62f0f609b63573c440cbcd0.
References: [Khronos NoContraction specification](https://registry.khronos.org/SPIR-V/specs/unified1/SPIRV.html#_decoration) and [wgpu 30.0.1 passthrough safety contract](https://docs.rs/wgpu/30.0.1/wgpu/struct.Device.html#method.create_shader_module_passthrough).
