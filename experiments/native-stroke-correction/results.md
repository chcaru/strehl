# Targeted RAW correction: visible local improvement

2026-09-09. **MEASURED: the nominated sensor-coordinate correction substantially reduces the dark background stroke in the full105frame coffee-bean RAW render.** A faint residual pattern remains. The three fixed front-texture, central-crack and outer-edge512x512 regions are exactly identical in allRGB16 samples. This is a useful local photographic improvement and causal evidence that the nominated source footprint contributes to the stroke. It does not establish physical dust, automatic detection, true radiance recovery or SOTA.

This is a per-stack experimental sidecar using the existing pre-warp correction path. No production algorithm/default was changed. Current noise propagation omits the spatial correction gain; the map must remain experimental pending that work. See independent-results.md for the separate review.

## What changed in the actual photograph

![Before above, corrected below, same original pixels](C:/dev/blog/death-of-software/projects/strehl/experiments/native-stroke-correction/view-1/stroke.png)

Top: saved baseline. Bottom: corrected. Each320x120 crop is at delivered-output(x150,y1490); the pair is320x240. RGB16 is rounded by division257 toRGB8 identically on both, with no resize, registration, tone adjustment or sharpening. Root inspected the same direct crop as the independent reviewer. The image is deliberately small to preserve original sampling.

![Clean control before above and corrected below](C:/dev/blog/death-of-software/projects/strehl/experiments/native-stroke-correction/view-1/clean.png)

The nearby clean crop(x150,y1300,w320,h120) shows no visible change. It is not mathematically identical: RGB16 differences range-3..+5DN with mean absolute0.8355DN. Demosaic/pyramid/tone may spread output changes beyond the source footprint, so exact outside-mask TIFF identity was not promised. The three distant fixed512x512 detail controls are each exactly unchanged across786,432RGB16 values; this establishes preservation of those regions, not all possible subjects.

## Original RAW admission and intervention

Source1c5d3a165f10902b7b71b530d63c913f2f7b63af implements only a small saved-patch proposer and controls. Proposal evidence9ce8d3c629c5842e2d0c56d5ca75289c21e2a390 records the admitted map. Commands actually run from the repository:

~~~powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B experiments/native-stroke-correction/run.py propose
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B experiments/native-stroke-correction/run.py render
~~~

The fixed manualnomination is active-native centre(414,1630), radius32; illumination is fitted only in annulus48..80, with an affine primary and independently chosen quadratic stress. One cosine-squared shape and one attenuation amplitude are fitted on originals0+104;26/52/78 are excluded from shadow fitting, though allfive were previously viewed. No automatic detector, width search or newRAW decode exists in the proposer.

The fitted amplitude is0.0552549335. All24heldout phase/model rows pass the fixed error/absolute-mean/no-bright-core checks after actualu16-style writeback. Their model-relative supportRMSE ratios are0.40782..0.58266 and their correctedcoremedians remain negative(-0.008322..-0.001567). Those are local fitted-background residuals, not ground-truth image quality or temporal noise. The affine/quadratic alternatives bound one nuisance; they do not prove that either background is truth.

Independent arithmetic controls recover a known stationary input and refuse clean affine/constant/quadratic illumination, a scene-following feature, doubled correction, a changedheldout and a shallow singleCFAphase. The realclean and copied-clean moving-feature placebos both give positive proposed amplitudes and are correctly refused. This is stronger than relying on negativefit refusal alone. Originalu16 samples outside807nominatedquads stay exact in every savedpatch correction; there are no new white-level skips.

The map is currentv2, coordsactive,807sparsequads spanningquadx191..222/y799..830. It changes no embeddedcamera profile. Maximumgain1.05841208. The format's covered446x1662 prefix encloses this sparse footprint; provenance explicitly denies full-flat calibration of that prefix. MapSHA73c64de36ff15ee7b91018624d03851c1449b3081a4dd54f5a64f727242e6098.

Unchanged production validation independently reads eightfulloriginals(indices0,15,30,45,59,74,89,104), confirms1/1site atquad(207,815), reports depth-3.991% versus map-3.984%, p0.0025 andpresence1.00, andrescales by1.002. These are its actual reported values, not a new statistical calibration. Its amplitude is therefore not heldout from thoseeightframes. Across105loads, the existingcorrector changes315,132sensels;79,691of84,735examineddustquads change,5,044do not,0clip and0areoutside.

## Whole render and limits

The full corrected native run completed in51.782seconds wall,303CPU-seconds, with2,839,121,920bytes peakJobcommit. The savedbaseline was50.063seconds; this single pair is not an overhead benchmark or competitive speed ranking. Both reuse the same105frame reference52alignmentmap. No alignment solve time is included. The sameheldCLI,105originals,roundedfullres gather,greenprobe,parallelwriteback,pyramidsettings,sRGB/Crop andsourcecolour metadata are used; only defectsettings andfreshoutputpath differ. Printedtone remains black0.02005,white1.16592,contrast0.55 at the logger's precision; no full-precisiontone identity is inferred.

Fullimage:6784x4524RGB16 sRGB,184,149,970filebytes. FileSHAd568f12b84cab063df45319faa5f7d0f9993dba7fb8936ae64ccb795baea5960. Decodedpixels184,144,896bytes,SHAd13d98ac4fcbaf6c772a32c157042480bae3e004df1b8fa973c37dc5796f8fca. Exactcommands,environment overrides/cleaning,source/inputbindings,terminalaccounting andcorrectionlog are preserved under render-1. All210previouslylistedoriginalRAW/developedTIFF metadatarecords remain unchanged; this is not a wholecorpus hashing claim.

The physical variance limitation is substantive: if Y=d*S, the existing injectedmodelk*S+r² should propagate tod*k*Y+d²*r². CallingtheoriginalmodelatY givesk*Y+r² andmissesbothfactors. The syntheticnoiseprobe also lacks thatspatialgain. Do not repair it by scalingitspositivepedestal, whichwouldcountthe deterministicmapshape asnoise. No gain/noiseconstants were fitted here; defaultpromotion requires the actualnoise consumer to carry correctionvariance and appropriate independentcontrols.

## Decision

Retain the map and corrected photograph as an experimental, stack-specific result. Close this exactone-render intervention; no further support/amplitude/preset tuning. The visiblecontribution finding is stronger than sourcepersistence alone, while the remainingnoise limitation prevents a generalproductpromotion. Next implementation work should repair propagationof known correctiongain through the currentsharednoise/probe path before automaticuse. Continue prioritizing realRAWquality andfullrenderspeed; SOTAquality andfaircomparative speed remainunproven.
