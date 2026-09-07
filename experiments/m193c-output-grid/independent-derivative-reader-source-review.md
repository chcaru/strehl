# Derivative reader: independent root source review

**SOURCE REVIEW ONLY.** Root inspected Curie's private/native reader and TIFF
parser, the separate Zeno derivative producer, the owned development writer,
and the native parent interface. No decoder, private fixture, pixel comparison
or RAW hash was executed by this review. Actual outcomes remain pending.

Reviewed final reader: 61,341 bytes,
`8c571654667f8ef66520aedfd1bddceb991c8a86d1a7355a4ed21cf2ba85eced`.
Parser: 8,144 bytes,
`9acceb498568967bb02ce01389441da09de7502f3a51faebbed8fed61943a5ae`.
Reader preregistration: 10,711 bytes,
`bf8a6c2a13b109fb8e5cb8e3c1a9f1ce47931ded220de909118636645bd8a990`.
These pins precede any execution release. Earlier author draft descriptions do
not supersede the final source or supply a measured pass.

## Rechosen calculations and actual consumer

The private oracle evaluates signed CFA samples, white balance and MHC in
rational arithmetic. It compares an explicit affine expression at 54 interior
sites against the independent stencil calculation. The second field contains
below-black samples and above-white values, and all 660 sites are compared.
Final RGB quantization is separate from interpolation. The source preserves
negative values through MHC; premature black clipping must cause a fixed
1/256 normalized change at the declared neighbouring site before its pixel
rejection counts. Delaying white balance likewise has an explicit nonzero
pixel witness. These checks can reject the specific ordering mistakes; they
do not prove a physical colour model or real-scene image quality.

The parser retains the previous strict classic RGB16 tag policy but permits
the declared native dimensions and streams a canonical little-endian digest
over every strip. The private controls include both file byte orders, a width
the old parser refuses, malformed fields, extent changes and an actual altered
pixel. The private materialization limit remains small; native mode does not
allocate a second full RGB array. The owned writer still allocates its own RGB
output, so this is not a claim that the entire operation is allocation-free.

Native decoding consumes a bounded, already hashed snapshot buffer. RawPy's
public API accepts a binary file object; its image view must be copied before
the context closes. The source does that, and the private lifetime fixture
poisons the borrowed backing after exit while checking the owned copy. The
reader obtains CFA indices at full-buffer coordinates including the visible
margins, then compares only the active payload and each active row. These
choices follow the [RawPy API](https://letmaik.github.io/rawpy/api/rawpy.RawPy.html)
and [binary-input contract](https://letmaik.github.io/rawpy/api/index.html),
read during this review. No linked decoder implementation source was opened.

Black/white agreement uses the actual resolved scalar values and all consumed
CFA channels. Missing per-channel white metadata is not converted into a claim
of metadata presence. White-balance agreement normalizes by the declared local
green channel and retains the fixed tolerance. Neither shared calibration
constants nor agreement between two decoders proves physical calibration.
Native TIFF checks authenticate full payload and dimensions; they do not
independently reconstruct every native MHC pixel or grant registration coverage.

## Findings repaired before execution

1. **False acceptance inside the refusal helper.** Its own failed-expectation
   exception was caught as if raised by the subject. For identifiers such as
   `tiff-compression`, that exception contained the expected substring and
   could mark an accepted malformed file as PASS. The repaired helper catches
   only the subject call; normal return with an expected refusal fails outside
   the handler. A first, metadata-only tripwire deliberately returns normally
   under that matching identifier and requires a failed control record. There
   are now 41 independent controls and the unchanged 32 source controls.
   No additional production TIFF or numerical tolerance was introduced.
2. **Impossible native metadata allowance.** Copying every compiled source
   would consume 4,721,882 bytes for build 2's 119 sources alone, exceeding the
   unchanged 4 MiB per-frame metadata limit. That total was computed from the
   actual build record before any native run. Only four small reader/specification
   sources are now copied; the complete source map remains bound and rechecked.
3. **Publication bytes were not checked.** Successful writes now require the
   actual returned length and persisted hash. Finalization rehashes written
   artifacts, including the terminal record, and late failure revokes success.
   A failed negative replacement still returns nonzero and preserves its cause.
4. **Launch interface mismatch.** The reader now consumes the actual enclosing
   stage record, binds its argv to the observed argv, and binds log pathname,
   digest and length to the observed log. It no longer expects an unproduced
   phase/executable shape. The separate native parent has an explicit reviewed
   invocation-object amendment; it checks `orig_argv`, runtime and source map.
5. **Padding null scope.** Changing discarded padding in the independent array
   constructor is an arithmetic layout null. It is labelled accordingly. The
   producer's separate actual padding control is the relevant pipeline witness;
   the independent constructor identity cannot substitute for it.

Root reread these changes in the final pinned sources. Source inspection is
not an executed commission: all 41 controls must still pass their actual
expected paths, including the normal-returning-subject tripwire, before either
private TIFF is admitted. The enclosing owner supplies complete process and
artifact accounting; local samples do not replenish the overall allowance.

Disposition: ready for the separately frozen private experiment after the
enclosing owner is independently reviewed. Native execution additionally
requires the admitted private result and its own frozen runtime/command plan.
