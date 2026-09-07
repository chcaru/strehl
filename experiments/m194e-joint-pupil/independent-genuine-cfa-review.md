# M194e genuine CFA verification

2026-09-07. **PASS_CFA_CONVERSION_AND_PROVENANCE**, `fixture_only=false`.
All five genuine64×48 CFA files,15,360 samples total, match the independent
exact conversion oracle. Expected-CFA electron arrays match exactly; original
scalar, indicator and numerical-receipt copies retain their admitted bytes and
relative hierarchy. Source and input bindings remain unchanged.

This admits noiseless CFA conversion and recorded provenance of the already
admitted scalar geometric model. It does not establish camera calibration,
diffraction, a production merge, image quality or SOTA. The three earlier
incomplete float campaigns and all earlier component failures remain preserved.

## External authority and unchanged reader

Root supplied both actual hashes after independent complete-float admission:

| Input | SHA-256 |
| --- | --- |
| `cfa-emission-1/manifest.json` | `f47c2b8720560fe9dbd777eeed3281ce2531f1f2287f5c88ef7b51a083d03299` |
| `independent-full-comparison-1/float-commission.json` | `4bd57b896be0b68c42fb1384a468a4f29cc54139a18a046a678dd97bad408217` |
| Complete-float comparison result | `00a6a877005bfc15c33d583f70e4ef6d4f4fb334667ebc00ae61f84e0e20f42f` |
| Frozen final reader | `189802f34de22b901f0d403c410dc2bfc67d529e9f97abe65ccaefc4d707d2a9` |
| Its39-check current control result | `e73ded3f0d3c0d8d76a590a77c3855ea7f2f119097616f64e9a1de0806677fc4` |

The reader ran unchanged on these externally supplied inputs. It checked the
terminal emission receipt, actual original bundle, all15 original numerical
receipts/scalars/indicators, source/design/control bindings and complete
independent evidence population. It then read all five emitted expected-CFA
arrays and raw CFA payloads, along with preserved primary inputs and the frozen
refined reference arrays. It did not invent or substitute a fixture-only gate.
The valid/current private controls and actual genuine-CLI fixture refusals are
retained in [the amendment4 refresh](independent-amendment4-refresh.md).

```powershell
python -B -X faulthandler -X pycache_prefix=experiments/m194e-joint-pupil/work/independent-cfa-verification-cache-1 experiments/m194e-joint-pupil/independent-verify-cfa.py --manifest experiments/m194e-joint-pupil/cfa-emission-1/manifest.json --manifest-sha256 f47c2b8720560fe9dbd777eeed3281ce2531f1f2287f5c88ef7b51a083d03299 --float-commission experiments/m194e-joint-pupil/independent-full-comparison-1/float-commission.json --float-commission-sha256 4bd57b896be0b68c42fb1384a468a4f29cc54139a18a046a678dd97bad408217 --reader-controls experiments/m194e-joint-pupil/independent-final-cfa-controls-5/result.json --reader-controls-sha256 e73ded3f0d3c0d8d76a590a77c3855ea7f2f119097616f64e9a1de0806677fc4 --output experiments/m194e-joint-pupil/independent-cfa-verification-1 *> experiments/m194e-joint-pupil/independent-cfa-verification-1.log
```

Exit0 on the first genuine attempt, with a new cache/output directory. No
source, numerical threshold, reference or reader amendment followed the run.
Exact interpreter/arguments, source snapshots and the complete file ledger
are retained with the result.

## Exact conversion and approximate-reference rounding

The source scalar is in electrons. RGGB site factors are `.75,1,1,.6`;
expected-CFA electrons include those factors. The code is ties-to-even rounding
of `512 + .25*expected_e`, with unrounded and rounded white15360 excluded.
There is no WB, noise draw or clipping in this conversion. Each actual CFA
payload is exactly6144 bytes of little-endian u16.

| Original frame | CFA SHA-256 | Maximum primary/reference discrepancy, e | RMS, e | Sites within registered rounding allowance |
| --- | --- | ---: | ---: | ---: |
| 0 | `3b0b3f176940ce975c738d5f4c39731ea01543f8d77b7f98b3336be33c9c33ab` | 3.266733983764425e-6 | 6.267123774829234e-8 | 3 |
| 1 | `351f8f0e8b68a2fd3c3090c157fe9b7b2226cef101a55b450fec0c1bba52fe9a` | 8.865863492246717e-7 | 2.8745967822536792e-8 | 9 |
| 2 | `115f976db91f728b690847dea31be5b800161f75f8814609033015daa9f1119a` | 1.2419945960573386e-4 | 2.2448767439374392e-6 | 5 |
| 3 | `5cf67654e2fd29d75b740ccdd8c26b795f19ca590709ceb775cbabd747776494` | 1.0451567504787818e-6 | 2.6064737138923185e-8 | 4 |
| 4 | `cc075248bcb95d2cf02e47fc441bb0af45b2a26c7cf76eb96fbd74c259fa6b0f` | 7.908056431915611e-8 | 2.384262758341516e-9 | 3 |

Each row uses all3072 primary scalar samples against that frame's already
frozen refined independent reference. The reported worst primary discrepancy
and largest frame RMS are below the unchanged.004/.0008-electron limits.
These rows do not replace Zeno's separate all15-array and refinement admission.

The approximate reference happens to produce identical rounded codes for all
15,360 samples. This is an observed secondary comparison, not the exact
conversion authority and not proof that arbitrary allowed reference errors
cannot cross a rounding tie. There are24 sites within the registered
half-integer allowances:4 red,14 green,6 blue. All actual observed code
differences, including those outside the allowance, are zero. The earlier
private control deliberately produced192 reference-code differences per frame
within its allowed margins, proving this separation is live.

## Genuine gate and next consumer

| Output | SHA-256 |
| --- | --- |
| `independent-cfa-verification-1/result.json` | `8901be629a789d2959482baed15bef3e8cf23ba5f13418f66afdfb9fbf8bacdd` |
| `independent-cfa-verification-1/cfa-commission.json` | `706462ad18a5a3846cadd99e1ef24d6b92b77e064df2e34cbe72e45907fc06a6` |
| Verification raw log | `95f94c42e27a041e0f9a80c2d6e30a2e7cc2016a825f6ffc890e9d9043843573` |

The genuine gate is `m194e-cfa-commission-v1`, status PASS, sample_count15360.
It binds the external manifest and float authority and the exact relative
`result.json` above. A later production bridge can consume this existing gate
and its result/source closure; it must retain the distinct M194e input meaning.
The five64×48 CFA arrays are ready for that separately registered integration.
They do not inherit three-band/noisy quality coverage from M194b/d, and no
production TIFF was generated by this verification.
