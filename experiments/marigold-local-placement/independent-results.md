# Independent decision on fixed marigold placement

2026-09-25. **VERIFIED refusal of this fixed local fit recipe before rendering.**
The saved result is `STOP_ANY_FIT_FAILED`, with `full_pair_admitted=false`.
The all-eight admission rule was fixed before execution and correctly stops
this trial. There is no candidate photograph or photographic quality verdict.

I read the staged source/anchor-decode evidence, the unchanged registrar's
generated controls, every saved real fit, both process records and the final
completion. The result SHA256 is
`2dd4ee4d6b6b783d6d0e383d9945a90a196714352e62038cfdeea95a64a21ebd`.
No fit was recomputed or new source/crop selected. Exact commands are retained
in `stage-1/process.json` and `fit-1/process.json`: `stage-fit.py stage-child`
and `fit-child`, under Python3.12 with `-I -B -X faulthandler` and the bound
output/staging paths. Both processes completed successfully, in 5.765 and
2.453 seconds respectively; these are operational costs, not speed benchmarks.

| Source ordinal | Held-out RMSE after/before | Fixed decision |
| --- | --- | --- |
| 108 | 1.0331183813 | Refuse |
| 109 | 1.0039720757 | Refuse |
| 110 | 1.0016939947 | Refuse |
| 111 | 1.0125536006 | Refuse |
| 112 | 1.0000000000 | Exact-zero local anchor |
| 113 | 0.8379381300 | Individual fit admits |
| 114 | 0.8879453624 | Individual fit admits |
| 115 | 0.8327728107 | Individual fit admits |
| 116 | 0.8328826667 | Individual fit admits |

All eight non-anchor fits converge, stay off the ±4 source-native-pixel bounds,
and have positive nuisance gains. Actual source support gaps remain positive
(minimum 4.700455755 native pixels after the complete 11.02-pixel footprint).
Thus the refusal is neither optimizer failure nor insufficient source support:
four fits fail the required held-out decrease. The anchor has zero displacement
and approximately 4.4e-16 held-out residual. Its independent original-u16 patch
decode differs at zero sensels; that second-decode result covers anchor112,
not all nine originals. Initial source content hashes and unchanged sizes/mtimes
are recorded; this is not a second full-content audit of every source.

The generated known-shift, mild-blur/shift and blur-only controls pass, with
translation errors below 0.00078 source-native pixels against the unchanged
0.05-pixel bar and live wrong-sign destroyers. Those controls commission this
sampler/fit, not real-image defocus invariance. All real samples stay in global
reference244 coordinates even though local anchor112 supplies the guide.
No nuisance intensity gains or offsets were applied to RAW radiance.

The causal limit matters: increased held-out guide error is not proof that the
proposed displacement would worsen the photograph, nor that the original map
is correct. The low-pass guide can mix motion, defocus, occlusion, sampling and
photometric differences. The improvement in ordinals113–116 does not identify
physical motion either. The two small failures near ratio1 still fail the
prospective strict rule; no uncertainty claim or later tolerance is used to
reverse that decision.

Do not retain only the favorable four neighbors, choose another anchor, shift
the fan support, widen the search, or add a blur term from this result. The
five-point marigold trace remains inadequate as geometric truth. The earlier
modest chip gain and both photographic star-sand nulls are unchanged evidence.
This one marigold intervention is closed before full-render configuration or
baseline/candidate jobs; no SOTA, artifact-removal or capture-limit claim follows.
