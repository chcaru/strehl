# Independent review of the current baseline reference

2026-09-26. **ARGUED: accept the saved same-build historical-tone TIFF as a new
exact baseline reference for the bounded cost/full observation.** Keep the first
cost run refused. Do not widen an epsilon, describe the old RGB16 reference as
identical, or change the learned model, photographic bars, geometry or tone.

**VERIFIED independently:** command run:
`C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe -I -B
experiments/cross-scale-band-guide/independent-baseline-check.py`.
It completed in1.488s, reading only the two saved TIFFs. It examined every one
of95,745,120 RGB16 channel samples in4612x6920x3, using257-row blocks rather
than selected ROIs. Full results and reproducible input/script hashes are in
`baseline-reference-check.json`. No RAW decode, image edit, rebuild or candidate
was involved.

The complete difference list is below; coordinates are zero-based output-native.

| x | y | Channel | Prior | Current |
| --- | --- | --- | --- | --- |
| 2997 | 1057 | B | 39509 | 39510 |
| 3651 | 1610 | B | 40730 | 40731 |
| 2209 | 3074 | G | 31891 | 31892 |
| 1780 | 3510 | R | 23805 | 23806 |

Every other channel sample is identical. Maximum absolute difference is one
16-bit code. Both complete images produce the identical rounded RGB8 hash
`9da659c7f1725880b51eea067fa706652fae8348c42023521828baa576e7e0ee`
under `(u16+128)//257`. ICC bytes are identical, SHA256
`238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b`.
Thus the existing RGB8 registration/view coordinate reference is unchanged.

Prior reference: `../parallel-cfa-wavelet/full-1/output/baseline.tiff`, file SHA
`b7617f42537487fbecf9d88e47bf99b571ee7f6faeae2ccd9b34ba619995decb`,
RGB16-LE SHA
`2a19cd9b7236a13bf90e81b87e85b1058e071aa19f4a5af82b97f453687d0dda`.

New reference: `full-cost-1/output/baseline-historical-tone.tiff`, file SHA
`de1e5dccc0a0c92a4d1f3c93cee6109fb0ea123dbae990a1759b92203d4a70ef`,
RGB16-LE SHA
`e870e3ec57f9d2819fee58d049f5de839c1e05584929afccbefc2b00dc9253b9`.
Each TIFF is191,495,352 bytes. The new reference exists before any learned
candidate was rendered; it was not selected to improve the candidate comparison.

Source review of commit`3fe71e351f62a8cef9cc0ecb4c3d1547e9b2fd5e`
confirms the production SoftPower numerator changed to accumulate
`w*(L/65536)` and restore after denominator division, with an explicit warning
that tiny-product underflow prevents arbitrary bit identity. The source author's
old-build binding identifies an earlier version. This provides a concrete
arithmetic-version difference; it does **not** independently attribute these four
specific output codes to that change. That causal question remains unproven.

Proceed only with the new reference's exact file/pixel hashes pinned and its
historical-tone comparison required to repeat exactly. Preserve current pinned
baseline rewriting, exact full RAW canonical pass1/pass2 CFA/TIFF comparisons,
terminal Mean/input bounds, complete source coverage and matched candidate
development. Generated literal observer-off checks retain their own scope;
the two instrumented RAW passes must not be described as a new literal
observer-off RAW test. Any new mismatch refuses rather than silently selecting
another reference. This decision changes the reference version, not numerical
tolerances or the pending photographic quality decision.
