# M189 repeat-pair attack result

Status: **REPEAT CROSS-STATISTIC DOES NOT SEPARATE RE-NOISED PROVENANCE**

Source freeze: commit `2d312ff6`

No capture was opened.

## Derivation

Let two completed observations be

\[
Y_1=T+\epsilon_1,\qquad
Y_2=T+\epsilon_2,
\]

where the noise fields are independent and follow the calibrated PTC law.
Then

\[
E[Y_1Y_2^*]=|T|^2,\qquad
\tfrac12E|Y_1-Y_2|^2=P_\epsilon,
\]

and

\[
\rho=\frac{|T|^2}{|T|^2+P_\epsilon}.
\]

None of these expressions contains the provenance of \(T\).

- In the genuine world, \(T=H'O\) is a better optical image.
- In the attack world, \(T=K\hat\mu\) is a deterministic
  denoised-then-sharpened estimate.

Fresh re-noise is independent in both worlds. It disappears from cross-power
and appears in repeat-difference power in exactly the same way as genuine
temporal sensor noise.

If a separately processed denoiser has

\[
D(X_i)=m+u_i,
\]

where \(m=E[D(X_i)\mid O]\) is its repeatable component and \(u_i\) is its
realization-dependent residual, cross-power credits \(|Km|^2\). The residual
\(Ku_i\) merely joins the uncorrelated noise term. Deterministic edge halos,
prior-driven textures, and other repeatable manufactured structure are
therefore classified as signal.

“Suspiciously high” coherence is not a safe discriminator. A genuine
high-SNR optical observation can have the same coherence.

## Executable finite witness

`repeat_attack_witness.py` constructs:

1. a positive deterministic mean formed by denoising and sharpening;
2. two independent signal-dependent PTC noise fields;
3. world G, which labels that mean as optically delivered; and
4. world R, which labels the same mean as rendered.

The two repeat arrays are byte-identical across worlds. The measured output is:

```text
a_bytes_equal=True
b_bytes_equal=True
max_abs_summary_difference=0
cross_power=6356407177.43
difference_noise_power=1778.18247864
coherence=0.998914239588
PASS: identical repeat observations retain opposite provenance labels
```

The cross-power, repeat-difference power, and coherence are exactly equal.
Changing the label cannot change any statistic of the completed repeat pair.

## Ruling

A repeat-pair cross-statistic does **not** close the adaptive re-noise attack.
It establishes repeatability, not optical provenance.

The missing observation is authenticated ancestry between output residuals and
the actual input photon-noise realizations. That would require the input RAWs,
a frozen renderer and its declared weights/warps, and a pipeline-specific
input-to-output residual test. It is not available to an output-only
comparator statistic.

