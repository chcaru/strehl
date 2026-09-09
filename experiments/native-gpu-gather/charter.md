# Native GPU gather — first implementation allocation

Decision: test the current RAW reconstruction/gather as a GPU workload.
The retired M7 ring-focus result does not measure this consumer. In the newer
native-parallel-writeback run, gather took 3.85993 s / 34.60% of one
11.156 s native109 render; Probe separately took 28.42%. These are historical
wall intervals from that run, not a new profile or a projected speedup.

Prototype boundary: one active u16 RGGB frame in, current signed-black/WB
Malvar reconstruction, gear-resolved CA/geometry, Catmull sampling, inverse WB
and existing u16 writeback out. A standalone optional experiment first; no
production default, decoder, merge, noise calibration or reduction change.
Do not retain a full aligned stack. Intermediate image arithmetic stays f32.
GREEN_ONLY must preserve unconsumed R/B sites and its two-site coverage count.

Geometry remains on the CPU initially: actual f64 support/floor decisions
become exact source cells and f32 fractions in bounded row strips. CPU-produced
inverse WB is passed verbatim. Charge this preparation and transfer explicitly
before making any eventual speed claim. No silent f32-geometry substitution.
Eligibility is Malvar plus Catmull only; unsupported modes refuse or retain CPU.

Reuse the permissive M7 wgpu host facilities, replacing its retired kernels and
whole-stack allocation. Use existing core CPU functions as the oracle, with a
minimal separately reviewed bridge to the actual CLI boundary when needed.
The independent design fixes tiny cases, phase/coverage/rounding witnesses
and live wrong-coordinate/phase/control mutations. Initial consumed u16 and
coverage equivalence is exact; a failure records its specific operands.
An implementation bug may be repaired with the fixed controls unchanged;
numerical non-equivalence cannot be relabelled a pass by relaxing tolerances.

Root owns source freeze, compile and execution. No numerical run, native RAW
decode or timing campaign is authorized by this source-draft allocation.
A subsequent finite control invocation needs the finished independent fixture,
source review and existing process limits, not another measurement framework.
Full-render timing follows only useful actual-consumer equivalence and includes
startup, packing, transfer, synchronization, readback and final output writing.

Owners: implementation agent writes the isolated prototype; design agent owns
independent fixtures; verifier challenges numerical conventions and oracle
choices; root checks integration and runs the work. SOTA remains unproven.
