# Independent source review

**Source decision: no blocking defect found; admit fresh compilation and the
independent controls. Photographic execution still depends on those controls
and the exact baseline guard.** This reviewer ran no builds, image experiments
or RAW decodes and edited no implementation source.

Reviewed frozen SHA256 bindings:

- `core-bridge.rs`: `7326f08951a939763313f80ae511bdfc22247089eaf8e6317216930c69c158f0`
- `implementation.rs`: `4ff2eab275082e874212702e792b6b6f057c196a14c24a4cdcbf0fabc81a9b36`
- `full-stack.rs`: `39f46f632fb4ed57e6c7c4b4cb189d252122548960c61750eb13d67acb6795e3`

The bridge guards SoftPower, mean fallback/base, InputRange, HardFloor and
zero mean-coarse modes. Its baseline coefficient resolution matches production
`BandMerge::finish`: positive denominators use numerator/denominator; otherwise
the full-frame unweighted sum uses the same reciprocal frame count. Donor
replacement occurs after that resolution. A covered coefficient therefore
cannot return to the all-frame mean through a hidden fallback. Exact zero
coverage adds no arithmetic; a wholly empty mask calls actual finish.

Mask fields use the actual production Gaussian reduction, not Laplacian bands.
Overlap is counted; a sum above one divides all memberships by the same total.
Coverage is capped consistently with the intended convex combination. The same
memberships and source indices apply to all four deliberately unaltered colour
planes. The terminal base is never donor-accumulated or mixed. Reconstruction
uses actual Pyramid collapse followed by the same per-pixel original-input
minimum/maximum bound as the guarded production mode. No per-level hull is
silently substituted. The independent controls must establish numerical parity;
the reviewer also requested collapse of the resolved baseline plus its hull
against actual finish, since the zero-mask shortcut alone skips that resolver.

Geometry is explicit: prescribed masks are in the held output-native gauge,
evaluated at the shared quad centre(2x+0.5,2y+0.5), origin(0,0). They are not
evaluated at one selected CFA phase. The full adapter retains original
crop[28,19,3460,2306] quads and full-domain pyramid context. No extra sensor
offset is added to an already output-local mask. The map hash, complete70-frame
sequence, active geometry, original black/white levels, normalized WB bits,
matrix and CA profile are checked. Its inherited twelve-pull support guard is
stricter than this four-plane experiment requires; it does not invent coverage.

The decisive consumer link is direct: after each actual `BandWorker::fold`,
indices28/33/25 contribute exactly that worker's current `planes` to the focused
accumulator;69 contributes to all three late regions. Thus donor values use
the baseline's actual gather, including GPU-coordinate rounding when the root
runner enables it. There is no separate CPU regather or alternate source
development. Donor plane hashes are taken before and after accumulation, and
original active-u16 hashes and source metadata are checked. One current source
and accumulated masked coefficients are retained, not a source-image volume.

Baseline accumulation keeps the canonical four chunks18/18/18/16 and the
existing first-move/subsequent-absorb order. Both donor arms use that same final
baseline object. All three writers take the same four-plane MHC development,
held WB/matrix and tone. The decoded RGB16 baseline must match historical hash
`2a19cd9b7236a13bf90e81b87e85b1058e071aa19f4a5af82b97f453687d0dda`
before candidate or late TIFFs are written. The runner additionally compares
decoded arrays with the independently file-hash-bound historical baseline;
the truthful TIFF Software tag may differ. Actual runtime success is not yet
claimed by this source review.

Interpretation remains limited. Fixed donor labels and masks are external
diagnostic choices. Gaussian reduction and collapse can affect pixels outside
the original capsule; unchanged final output there is not promised. Original
InputRange limiting may alter the reconstructed intervention and must remain
part of the photographic judgment. Inspect entire frozen windows, mask
transitions, compact cores and the competing structure, retaining the late69
control. A shorter fan obtained by erasing a genuine facet or introducing a
transition is a failure. This source review neither approves an automatic depth
estimator nor establishes photographic quality.
