# Fixed shared chromatic source evidence

Frozen before implementation/execution, 2026-09-25. Root owns builds and runs;
opal_headroom owns the operator, trace_review independently chooses controls.
Generated original-u16 sources only. No full adapter, RAW read, new dependency,
production default, strength sweep or SOTA claim is authorized here.

## Prior record and hypothesis

Mechanical prior-art commands and the proposal are recorded in
`../quality-september25/next-colour-evidence-brief.md`. Read BUILD-CHROMA,
M107-chroma, M-PHASE0-LCA, BUILD-HIGHLIGHT and V-GREEN: real colour-focus
differences do not establish the cause of a particular fringe; clipping and
output MHC coupling are distinct mechanisms. Preserve rb-own-guide's flat and
delivered-green failures, rb-residual-full's stronger photographic fringes,
green-match-rgb's retained fans, and real-source-contributions' inadequate
marigold witness. Shared-finest/Potts and prior colour transforms stay closed.

One untested hypothesis: a neutral veiling reflection can win green-band
evidence although coloured underlying texture identifies a better source.
Use colour differences to choose one common source mixture, while retaining
the complete measured CFA coefficients. No highlight radiance is subtracted.
This assumes the proposed illumination direction is useful; WB, metals,
iridescence, clipping and colour-dependent PSFs can invalidate that premise.

## Exact fixed operator

For each consumed source, use existing `phase_packed_rgb::gather_patch` on the
complete bounded generated active source, with the existing MHC, Catmull-Rom,
coverage, WB undo and rounded-DN rules. Its first four slots must be bit-exact
against the actual GPU known-four consumer on the original AND every probe
draw. Refuse on mismatch. The twelve slots supply R,G,B at each of the four
native sites of a quad; no different-site CFA subtraction is permitted.

Use gains `[wb[0]/wb[1],1,wb[2]/wb[1]]` only for evidence. At each native site
form `R*gain_R-G` and `B*gain_B-G`. Average each difference across the four
sites in fixed site order (R site,G1 site,G2 site,B site) with factor0.25.
Build the two ordinary Laplacian pyramids. At each AC band compute
`E=smooth5(L_RG²)+smooth5(L_BG²)` using the current production kernel.

Reuse exactly the existing rb-own-guide content-derived sixteen source seeds,
boundary-cfa-wavelet original injected per-site variances and noisy_source.
Each pair is independently gathered/projected through the same operator.
For each colour-difference band, accumulate `(L_a-L_b)²/(2*8)` then smooth5;
sum the two results and multiply by the unchanged gate. Project BEFORE squaring:
do not add marginal colour variances or discard covariance from shared green,
MHC, rounding and spatial sampling. Eight pairs estimate the operator's noise;
they neither validate camera calibration nor calibrate a probability/F test.

Pass E/F through existing `rb_own_guide_diagnostic::fields_from_energy` with
the unchanged exponent ramp, hard floor and significance settings. In a first
pass OR the positive chromatic-weight sites over all sources separately per
band. In pass two, at k>=1 use this source's chromatic weight where any source
was admitted; otherwise retain this source's canonical weight exactly. Use
one shared field for all four ORIGINAL consumed CFA planes. The finest band0,
terminal mean, every fallback sum and input bounds remain bit-exact. No band
borrows another band's ownership. No source-index distance is used as depth.

Off and forced-no-chroma modes execute identical observation/probe work but
retain canonical fields. Every repeated signal, floor and weight hash must
match. No source-count-sized aligned image/weight volume is retained. The
small adapter uses the current one-chunk generated consumer and final MHC;
pinned development is mandatory in a later separately reviewed full adapter.

## Controls and failure meaning

The independent reviewer chooses known-scene cases, exercising flat noise
first, real neutral detail, coloured glints, weak warm-WB colour, competing
depths, all CFA phases, and detail/colour destroyers. No claim of unchanged
delivered green follows merely from CFA state. Score actual final RGB.

A potential positive contains recoverable coloured texture at one depth and
an additive illuminant-coloured blurred highlight at another, with the blur
spreading into a frozen texture region. The high-spread source must actually
make canonical output worse there; a signed positive spill is not guaranteed
by composition. If the canonical mixture cancels it or the truth region has
no positive spill, record the positive as unexercised and make no benefit
claim. Do not require an impossible sign as an assertion that prevents saving
the remaining screen, and do not tune the plant after inspecting this rule.

Projection arithmetic has an exact co-sited common-mode null and a nonzero
coloured-texture positive. An independently generated RAW neutral-veil control
must separately expose rounding/phase/optical departures; exact invariance is
not promised through MHC and rounded gathers. Wrong-site subtraction and
independent-colour-noise substitutes must be distinguishable controls.

Off/no-admission output identity, held-state equality, original-source hashes,
all probe first-four identities, live candidate weights and active destroyers
are mechanical requirements. Photographic admission is false until the whole
screen and its independent interpretation are reviewed. A useful result must
lower truth error AND retain genuine colour/detail; dimmer or smoother alone
does not establish quality. Failure closes this fixed rule without a sweep.
