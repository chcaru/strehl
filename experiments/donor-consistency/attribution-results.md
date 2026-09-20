# Immutable RAW coefficient attribution

The independent decision is in `attribution-result-review.md`: the persistent
dark tail retains a large positive contribution from coarse baseline bands;
focused donor33 supplies negative detail that only partly cancels it. The
mean clamp correction at the fixed tail is exactly zero. This licenses one
different reconstruction-order counterfactual, not another parameter sweep
of the rejected recipe, an automatic selector, or a SOTA claim.

Root executed these commands after independently authored controls and source
review, using Python3.12 from the repository root:

```
python -I -B experiments/donor-consistency/run.py build --out experiments/donor-consistency/build-3
python -I -B experiments/donor-consistency/run.py controls --build experiments/donor-consistency/build-3 --out experiments/donor-consistency/controls-3
python -I -B -X faulthandler experiments/donor-consistency/run.py full --build experiments/donor-consistency/build-3 --screen experiments/donor-consistency/controls-3 --out experiments/donor-consistency/full-off-2
python -I -B -X faulthandler experiments/donor-consistency/run.py full --build experiments/donor-consistency/build-3 --screen experiments/donor-consistency/controls-3 --out experiments/donor-consistency/full-on-2 --observe
python -I -B experiments/donor-consistency/verify-attribution-pair.py --off experiments/donor-consistency/full-off-2 --on experiments/donor-consistency/full-on-2
python -I -B -X faulthandler experiments/donor-consistency/attribution-analysis.py --input experiments/donor-consistency/full-on-2/attribution --output experiments/donor-consistency/attribution-analysis-1
```

MEASURED: fresh core/CLI build149.875s; three controls pass in0.406s child wall.
Independent field maximum disagreement0.00012207DN, signed reconstruction
0.00076163DN. The deliberately false expanded-mask times expanded-image shortcut
differs by5.28393DN; actual clamp excursions reach607.757DN. Live signed
cancellation, all four planes, odd/even crop origins and output hashes pass.
These controls commission accounting, not photographic quality.

| Complete70-frame job | Wall seconds | User+kernel CPU seconds | Peak job committed bytes |
| --- | ---: | ---: | ---: |
| Observer off |35.094|118.09375|4247232512|
| Observer on |39.203|128.890625|4218724352|

These are single operational receipts, not a repeated timing comparison or
memory-use ranking. Both consume the held alignment and render all three arms.
Original metadata, consumed CFA source hashes and map identity remain bound.

VERIFIED: all three complete same-build TIFFs are byte-identical off/on. Their
RGB16 samples also equal the original full-1 triplet, whose Software metadata
identifies the preceding build. Complete images already shown to the user
therefore remain the actual observer subjects; no new improvement is implied.

| Arm | Complete RGB16 pixel SHA256 |
| --- | --- |
| baseline |2a19cd9b7236a13bf90e81b87e85b1058e071aa19f4a5af82b97f453687d0dda|
| candidate |0f7ef99afb7bbe8e29a2ec1971da64ad3fc31beea175838bca8feb3f749ef585|
| late69 |114e3a17436b4469a6478717ea869683b7c121c4cacc073e84a7e11a91c75adc|

Independent Python reconstruction checks pass on all signed fields: maximum
mixed window error0.0038681DN (<0.02), hull closure0.0001221DN (<0.003), and36
shared field artifacts exactly equal between candidate/late. All seven bands,
terminal base, actual pre/post-hull arrays and signed correction were included.

MEASURED at the frozen dark-fan3x3-quad neighbourhood: G1 retained AC is1890.19DN,
focused donor AC is-307.49DN, and final hull correction is0DN. The retained
positive contribution is predominantly levels4–6. This is signed linear
accounting; it does not define photon ownership or desired radiance. Raw means
and independently selected local-reference contrasts are both retained, because
the reference itself is clamped. Its correction must not be attributed to the
tail. The facet mean also warns against a false quality score: it gets brighter
at the fixed point while its photographed extensions become narrower.

NEXT: keep the three masks, donors, band count, base, geometry and development
fixed; reconstruct complete donor AC before applying the finest mask at output
quads. `reconstruction-design.md` fixes arithmetic and seam/detail failure
conditions. The original recipe stays closed. Any apparent gain must survive
independent review of the complete new triplet before automatic source work.
