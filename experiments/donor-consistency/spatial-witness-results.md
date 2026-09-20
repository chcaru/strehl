# The visible residual was outside full replacement

MEASURED: the actual mask at output-native(3080,2212), located after the failed
photograph, is0.010998. Its3x3-quad neighbourhood spans0..0.336698. The earlier
fixed fan point(3102,2203) has mask1 throughout its3x3 neighbourhood. Those
points describe different image content. The complete coverage map and actual
gathered-source photograph are essential evidence, not just the point numbers.

At the post-failure point's3x3 patch, G1 retained baseline AC is5404.989DN,
masked donor AC10.349DN, shared-minus-source base44.584DN and candidate hull
correction0. The actual gathered donor33 is visibly compact at that location.
The source/crop audit found no large address error between the old source
preview and actual gather; the error was choosing support for the visible
defect. Do not reinterpret the old full-weight point as a test of this tail.
These are signed accounting values, not detail/noise scores or ownership.

The whole old spatial trial still fails. This finding does not turn it into a
pass or establish that automatic source assignment works. A separately
specified corrected-address oracle can test local headroom; any such trial
is explicitly post-failure and hand-labelled, with a complete photograph and
nearby-detail check required. The earlier no-mask-tuning rule protects the old
trial's verdict. It does not justify treating a demonstrated wrong target as
the correct experiment forever. No radius, feather, donor or operator sweep
is licensed by this correction.

VERIFIED: observer off/on produces byte-identical complete baseline,
candidate and late-control TIFFs. All three RGB16 outputs also exactly match
the preceding spatial-full-1 results. The original RAW metadata and held map
remain unchanged. Five independent generated controls pass, including both
hull directions, actual-source decomposition, crop phase and observer neutrality.
The full witness accounting closes within0.004639DN under the fixed0.02DN bar.
The witness reports actual source hashes and exact delivered post-hull samples.

Commands executed using Python312 `-I -B` (and `-X faulthandler` for full/analysis):

```
python experiments/donor-consistency/run.py build --out experiments/donor-consistency/build-5
python experiments/donor-consistency/run.py controls --build experiments/donor-consistency/build-5 --out experiments/donor-consistency/controls-5
python experiments/donor-consistency/run.py full --build experiments/donor-consistency/build-5 --screen experiments/donor-consistency/controls-5 --out experiments/donor-consistency/spatial-off-2 --spatial
python experiments/donor-consistency/run.py full --build experiments/donor-consistency/build-5 --screen experiments/donor-consistency/controls-5 --out experiments/donor-consistency/spatial-on-2 --spatial --witness
python experiments/donor-consistency/verify-attribution-pair.py --off experiments/donor-consistency/spatial-off-2 --on experiments/donor-consistency/spatial-on-2 --spatial-witness
python experiments/donor-consistency/spatial-witness-analysis.py --witness experiments/donor-consistency/spatial-on-2/witness --out experiments/donor-consistency/spatial-witness-analysis-1
```

Fresh core/CLI build162.344s; controls0.531s; complete off35.297s/on38.641s;
analysis4.088s. Operational costs only, not a speed ranking or alignment timing.
Witness receipt SHA256:
`45dee5d6ca1498337dbc88eef009406e964733b673f78c509791b9c17e5047ac`.
Full numerical tables, source previews and2D fields are retained in
`spatial-witness-analysis-1`, with independent review beside this report.
