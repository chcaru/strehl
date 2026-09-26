# Independent fixed source-strip review

VERIFIED / VISUALLY REVIEWED, 2026-09-25. Extraction is valid; the proposed causal discriminator is **inconclusive**. These observations do not identify a second surface, establish correct native geometry, or license another width/degree treatment. The rejected Gaussian and intercept photographs remain rejected. Follow the memo's stop branch for this chip family.

I read `extract.py`, the actual reused stage mapping/sampling functions, the saved controls and receipt, then viewed all 14 source PNGs and all six corresponding native output crops. No source was selected by image content, no crop was recentered, and no additional image analysis or render was run for this review.

## Address and display audit

The delivered-to-source mapping adds the native crop offset (266,178) once, rotates/scales around (3516,2344), and doubles the map's quad translation. It preserves the pinned map's actual f64 values, including the near-identity reference149. The original source-order/developer records bind ordinal k to TIFF k+1 and the original identity. All 14 selected complete TIFFs were freshly content-hashed; this is not a fresh hash audit of all 299 originals. No RAW was read.

The exact prescribed sets are retained:

| Witness | Delivered 128-square core | Source ordinals inspected | Native crops inspected |
| --- | --- | --- | --- |
| Surface scratches | (5048,1448,128,128) | 194,200,206,213,219,225,231 | Current, Gaussian, intercept |
| Upper-left contact grid | (240,528,128,128) | 124,130,136,143,149,155,162 | Current, Gaussian, intercept |

Each source core is the central `[32:160,32:160]` of the original 192-square mapped support, using the unchanged proxy sampler. Float32 supports and cores are preserved. Native RGB16 crops are direct, unresampled slices at those same delivered coordinates. The PNG writer applies no new transfer function or per-image normalization, embeds the existing ICC, and checks channel order and every RGB16 code through an independent codec.

The pre-execution display amendment permits fixed [0,1] saturation only for PNG display; it does not modify the float masters. Scratch supports/cores have no out-of-range values. Contact cores have respectively 581,1008,1179,680,0,365,197 out-of-range scalar channels. At source143 the core range is approximately -0.12649 to 1.11440. These are cubic interpolation excursions in already developed RGB, **not measurements of original sensor clipping**. They limit interpretation of bright outlines; float preservation does not make a saturated display diagnostic of their exact shape.

## Visible observations and decision

The scratch core contains the recognizable lower diagonal scratch and an upper connected fine branch. The prescribed centre213 and neighbour206 visibly resolve connected detail that is weaker in the Gaussian/intercept crops. The fixed outer samples are more diffuse. Current retains substantially more fine variation than either candidate. This establishes that the sampled window is not simply devoid of the relevant subject detail. It does not establish the memo's stronger condition of stable mapped relative placement: the scratch trace, colour lobes and fine marks change with defocus, and the seven small proxy crops do not isolate the cause of that change. I therefore do not convert this into an exclusion of all wrong-front or gather explanations.

The contact core contains recognizable repeated vertical contacts and the connecting subdivision at the right. Across the prescribed sources, the tops, bottoms and junction contours visibly move downward/change location; even the relatively defined136 and143 views do not establish stationary outlines. Both the contact and neighbouring structure participate. Blur, demosaicing, chromatic response and display saturation complicate contour identity. This violates the stable-landmark premise needed to call the remaining candidate softness an averaging-only failure. It is evidence of **apparent registered contour movement**, not a measurement of true geometric displacement. Current's broad bright duplicates/spread and the candidates' softer outlines remain visible, but do not settle that attribution.

Neither witness supplies stable evidence that one identical fine branch resolves only on an off-centre flank while neighbouring material resolves at the centre. A second-surface claim is unsupported. The source TIFFs are CA-off, toned and individually demosaiced, whereas the native stack uses CA-on CFA gather followed by one final demosaic. This proxy/native difference remains an independent obstacle to a radiance counterfactual.

The mechanically successful extraction thus reaches the preregistered ambiguous-cause branch. No source ranking, expanded range, local shift fit, bandwidth rescue or photographic admission follows. Root's `chip-focus-intercept/native-results.md` agrees with the prior independent full-output rejection; no result correction is needed there. My earlier photographic report's command was corrected separately to the actual `reconciled-run.py` invocation, without changing its verdict.

## Evidence

MEASURED command recorded in `run-1/process.json` (root-commissioned bounded execution, exit0, 2.375s):

```text
C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe -I -B -X faulthandler C:\dev\blog\death-of-software\projects\strehl\experiments\chip-source-support\extract.py extract --out C:\dev\blog\death-of-software\projects\strehl\experiments\chip-source-support\run-1\output
```

The saved three stage controls pass addressing/filter arithmetic and their wrong-address destroyers; they do not certify focus or photographic quality. Receipt SHA256: `d67cea37de6f5958c42301851d03c99a47b37dd26fb7c97ae09873cec030fd24`. Extractor SHA256: `5f4cc046a754083fc3f5a063212aec973b46eb259e399d9d2a3c3d9f957031e5`. Process receipt SHA256: `abe83f084bebbc20e043f2d424e0cf350066048e62fd39fb33d0c265a22d32af`.
