# Independent saved-colour-error interpretation

MEASURED by root in `colour-error-1`; percentages below are DERIVED from its verified mean-square allocations. All six outputs match their frozen total chroma scores, and the coordinate-group oracle and conservation controls pass. Every phase uses the same4096 supported pixels. No fitting or source changes were performed by this reviewer.

**The added layered Cauchy error is predominantly within native2×2 blocks in both colour coordinates, consistently across the four tested bases.** Its own within2 share is80.23–81.21% for R-G and83.68–85.34% for B-G. Original-Huber visibility-1 shares are44.21–47.92% and52.11–57.30%; shot-prior shares are48.67–54.92% and55.63–62.80%. These within-arm percentages alone would not establish where the regression lies, so compare absolute energies as well.

Layered total MSE rises from[4489.52,4571.72] to[12244.07,22241.77] DN²: Cauchy adds **[7754.55,17670.05] DN²** over visibility-1. The within2 increases are7759–7959 and16159–16589 DN². Their shares of that added error are:

| Basis origin x,y | R-G | B-G | Both coordinates pooled |
|---|---:|---:|---:|
| 0,0 | 102.64% | 91.85% | 95.14% |
| 1,0 | 100.06% | 91.45% | 94.07% |
| 0,1 | 100.95% | 93.88% | 96.04% |
| 1,1 | 100.24% | 91.52% | 94.18% |

These are **differences of squared-error energies**, not energies of the candidate-minus-reference image. Values above100% are possible because other components improve: R-G common4 AC falls by561–711 DN². B-G common4 AC changes sign by phase (-123 to+213 DN²), while both coordinates' middle-scale errors rise. Against shot-prior instead, total added error is[7637.40,18055.50] DN² and within2 still accounts for **91.69–93.54% pooled**. The fine-scale conclusion is not manufactured by choosing only the original-Huber baseline.

Uniform colour bias is not the cause indicated by this accounting. Layered signed means move from[-2.091,-2.527] DN in visibility-1 to[-1.406,-.351] in Cauchy. Squared DC falls from[4.373,6.388] to[1.976,.123] DN² and constitutes only.0161%/.00055% of Cauchy's coordinate totals. Common4 AC is spatially varying error and must not be relabelled DC. It remains nonzero even though it is much smaller than the fine contribution.

The flat controls give a different allocation. Cauchy's fine share is only12.11–15.10% R-G and14.02–16.91% B-G, close to visibility-1's11.97–14.95%/13.88–16.76%; common4 AC is the largest component. Its modest added flat MSE[1.340,1.386] DN² is spread across scales, with only19.47–22.76% pooled within2. Shot-prior has substantially larger flat totals[88.84,77.75] versus Cauchy's[65.78,62.58], yet its fine shares remain14.31–18.68% across coordinates/phases. Thus the dramatic fine allocation is specific to the structured Cauchy error here, not an inevitable description of every noisy output or every rejected prior.

This licenses only a spatial-scale description of the saved error. Four dependent circular partitions include artificial boundary neighbours and are not all16 possible4×4 origins. Stability over these four bases strengthens the bounded allocation statement; it is not independent replication. Fine errors can arise from real edge misreconstruction, colour coupling, poorly constrained modes or unfinished optimization. No forward sensitivity was measured, so CFA aliasing, an optical nullspace, and a particular prior mechanism remain unproved. Cauchy's existing colour rejection and nonstationarity remain unchanged; neither smoothing nor a new reconstruction is admitted.

Scored receipt SHA256: `33cb5f37fd617c805b0c4d1c5889414cb8ad4f471fc6b20ba8e290bc213b52f3`. Source: `4043b4b52c06904084832cd54603fb1e4a086fd3f8930808f4aad391741ed906`; independent controls: `b6322d22e8f727309c1a91cf1490af4a23071c58d95f8b4d1c6810b3e6e0acda`. Original arm/source/score hashes remain in the receipt.
