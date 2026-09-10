# Independent scheduling source review

Source-only: no build, GPU/CPU control execution, RAW decode or render by this reviewer. No remaining source blocker found for execution-4.md.
Serial32 and Parallel256 share exactly the same per-point CFA channel choice, UNCONSUMED sentinel, f64 pull expression, plan_at call and invalid-descriptor predicate. No image floating-point reduction is introduced.
Parallel256 assigns disjoint complete rows through par_chunks_mut(width). Each global y is y_start+row; the synchronous for_each completes before the single independent mutator call, validation and GPU upload. Validation reduces only a boolean, so short-circuit order cannot change coordinates or output.
The plan vector starts at width*min(256,height). Truncation is safe because row counts remain constant until the final strip, then decrease once; there is no later larger strip requiring regrowth. Every retained descriptor is overwritten before the mutator.
Uniform row count, upload length, dispatch word count, both readback lengths and destination slice all use the current rows value. Stale capacity beyond a short final strip is not dispatched/read/copied. Full native height 4688 will exercise an 80-row last strip.
The fixed tiny cases are at most 50 rows, so they exercise parallel row filling but do not independently commission multiple 256-row strips. The already-allocated exact native 112 comparison supplies that missing extent coverage before 109 timing; no new fixture is needed.
Rayon 1.12.0 matches the workspace's existing locked package; no ThreadPool or second worker pool is created. The existing GPU context mutex and per-frame buffer lifetime remain unchanged.
CPU-only dispatch remains default-off and does not select a GPU schedule. Explicit GPU requests parse serial/parallel and retain Serial32 as a same-binary reference; schedule reporting does not change the primary control predicate.
WGSL, strict-SPIR-V transformation, source packing and per-pixel quantization are unchanged. The controls diff adds schedule receipt fields only; inputs and exact gates remain fixed.

Execution 4 appropriately runs fixed controls first, then CPU/Serial32/Parallel256 native 112 identity, then conditional 109 CPU/GPU/GPU/CPU with logs off. The optimization combines row parallelism and larger transfers; a resulting gain cannot be assigned to either change alone, and 256 is not a measured optimum.
The new schedule label is a small logging change, so the phrase 'unchanged logging code' in execution 4 should mean unchanged observer behavior apart from that label. The planned native exact-output check remains required; earlier observer identity is not a new-schedule timing-overhead measurement.

Reviewed SHA256: lib.rs b72c135dd21db80d04271bc6fcd42421bde19e6fde036121979ae6f5a1ed49cf; integration.rs 7c00c0175825c3ec73ef8bee8aea5eaafd9a8af1e5bc8cfc00feb90f52dc2d54; independent-tests.rs 9ebd1a970b89781314db5349b68cd07df0c7e0bfb25f56dc57471721e93975e3.
Unchanged shader SHA256 dbf900189081c839f67d103a555d27d9ec4a8165a62f0f609b63573c440cbcd0; strict helper a904c1017c051e3285390a5e714e797720cab6a150a27e15c1aefc3a3145a65e. Execution 4 SHA256 2f52e6da8eb49878766e87ea5dbe0936232cb11b3e63a862968b169b2bf7f1e4.
