# Workstream C — Competitive & Open-Source Landscape

Research date: 2026-08-22. Every URL in this document was actually fetched during this session unless
explicitly marked "could not confirm". Labels: **VERIFIED** (fetched primary source, factual),
**VENDOR-CLAIM** (vendor's own marketing/doc, unverified independently),
**PRACTITIONER-REPORT** (a named user's stated experience, not independently reproduced).

---

## 0. Executive answers (detail and citations follow)

| Question | Answer |
|---|---|
| Is any tool RAW-native / Bayer-domain? | **No. Not one.** Both Zerene and Helicon explicitly document that they demosaic before aligning. Helicon's "RAW-in-DNG-out" is a *late-development* mode, not Bayer-domain. See §5. |
| Realistic performance bar | Fusion math is **not** the bottleneck. Helicon's own benchmark: 987–1,956 MP/s on GPU, 356 MP/s on a 12-core CPU, for the *fusion kernel alone*. End-to-end practitioner reports are 100–1000× worse. See §6. |
| Hard licensing traps | `rawler`/`rawloader` (LGPL-2.1), `imagepipe` (LGPL-3.0), enfuse/enblend (GPL-2.0), align_image_stack (GPL-2.0+), EPFL EDF (GPL-3.0), ChimpStackr (GPL-3.0), ShineStacker (LGPL-3.0). See §8. |
| Names already taken | `z-stackr*` (7 crates), `stackaroni`, `focus-stack`, `focusstack`, `ChimpStackr`, `shinestacker`, `millefeuille`, `Picolay`, `deptheos`. See §4.3. |

---

## 1. Commercial tools

### 1.1 Summary table

| Tool | Vendor | Price (VERIFIED) | Algorithms | GPU | RAW in | Retouch brush |
|---|---|---|---|---|---|---|
| Zerene Stacker | Zerene Systems | Pro **$289**, Prosumer **$189**, Personal **$89**, Student **$39** — perpetual, "no periodic charges" | PMax (pyramid), DMap (depth map) | No (multi-core CPU only) | **No** — user must pre-convert | Yes (best-in-class) |
| Helicon Focus | Helicon Soft | Lite **$30/yr or $115** life; Pro **$55/yr or $200** life; Premium **$65/yr or $240** life | Method A (contrast-weighted average), B (depth map), C (pyramid) | **Yes — OpenCL, Pro+ only** | Yes (demosaics internally via Adobe DNG Converter) | Yes |
| Photoshop Auto-Blend Layers | Adobe | Subscription (price could not confirm) | Undocumented; behaves as feature-point align + masked blend | n/a | **No** — operates on pixel layers | No (falls back to manual masking) |
| Affinity Photo Focus Merge | Canva (ex-Serif) | **Free forever** as of the 2025 "all-new Affinity" | Undocumented | n/a | Yes (develops internally) | Yes ("sources" brush) |
| Capture One | Capture One A/S | Subscription/perpetual (amounts could not confirm) | **None — no native focus stacking** | n/a | n/a | n/a |

Sources: <https://zerenesystems.com/cms/stacker/docs/purchasing> · <https://www.heliconsoft.com/helicon-focus-versions-licensing/> ·
<https://web.archive.org/web/20230603190115/https://helpx.adobe.com/photoshop/using/combine-images-auto-blend-layers.html> ·
<https://www.canva.com/newsroom/news/all-new-affinity/> · <https://support.captureone.com/hc/en-us/articles/360002538538>

### 1.2 Zerene Stacker — algorithms, per the vendor

**VERIFIED**, <https://zerenesystems.com/cms/stacker/docs/faqlist> (verbatim):

> "PMax is a "pyramid" method. It is very good at finding and preserving detail even in low contrast or slightly
> blurred areas. It's also very good at handling overlapping structures like mats of hair and crisscrossing bristles,
> nicely avoiding the loss-of-detail halos typical of other stacking programs. **But PMax tends to increase noise and
> contrast, it can alter colors somewhat, and it's liable to produce fuzzy "inversion halos" around strongly
> contrasting objects.**
>
> DMap is a "depth map" method. It does a better job keeping the original smoothness and colors, **but it's not as
> good at finding and preserving detail.**
>
> The two methods complement each other... For particularly challenging subjects like bugs and flowers shot through
> microscope objectives, **neither method is ideal by itself.** In that case the best results are obtained by using
> human judgment and the retouching tool to combine the best aspects of both algorithms."

This is the single most important admission in the entire landscape: **the vendor states outright that on hard
subjects neither of its two algorithms is adequate alone, and that the fix is a human with a brush.**

DMap workflow is explicitly human-in-the-loop. **VERIFIED**, <https://zerenesystems.com/cms/stacker/docs/howtouseit>:

> "With default settings, DMap processing is broken into three big steps: Computation... **Human judgment: the user
> interactively sets a "contrast threshold"** that separates significant detail from irrelevant noise... Computation."

And on parameters (**VERIFIED**, same page):

> "The very best values for these parameters must be determined by experiment, since they depend on many factors
> such as magnification, lighting, camera, and lens settings in addition to the type of subject. **In particularly
> troublesome cases, it can be helpful to run DMap two or more times with different parameter settings, and combine
> those results with retouching.**"

Alignment: Zerene **does** correct magnification. **VERIFIED**, faqlist:
> "Does Zerene Stacker correct for changes in magnification as I focus? Yes, it surely does... The software doesn't
> care what the cause is for magnification changes; it just corrects for all of them."

DMap requires ordered frames; PMax does not but benefits. **VERIFIED**, faqlist:
> "For DMap, it's definitely best if the frames are processed in order... If they're out of order, then the result may
> still look OK at first glance but it's almost certainly degraded. Often there will be obvious artifacts like nasty halos."

Memory: **VENDOR-CLAIM**, <https://zerenesystems.com/cms/stacker> — "at least 100 megabytes of DRAM per each
1 megapixel of image size... We recommend... up to around 200 megabytes of DRAM per each 1 megapixel."
For 33 MP that is 3.3–6.6 GB *regardless of stack depth*.

### 1.3 Helicon Focus — algorithms, per the vendor

**VERIFIED**, <https://www.heliconsoft.com/helicon-focus-main-parameters/> (verbatim):

> "**Method A** computes the weight for each pixel based on its contrast, after which all the pixels from all the
> source images are averaged according to their weights.
> **Method B** finds the source image where the sharpest pixel is located and creates a "depth map" from this
> information. This method requires that the images be shot in consecutive order from front to back or vice versa.
> **Method C** uses a pyramid approach to image representation. It gives good results in complex cases (intersecting
> objects, edges, deep stacks) **but increases contrast and glare**."

Vendor admits parameter tuning is unavoidable and that halo is the price of detail (**VERIFIED**, same page):

> "Radius is the most important parameter for processing. **We mostly advise you to try different values.**"
> "If your image has fine details and thin lines, as most images do, a low radius level (3-5) will probably yield the
> best results, **although you will probably get more noise and a halo effect. So you'll need to try to find a balance.**"
> "All images are different and **there is no strict rule about which radius will work better.**"

And on method choice: "there is no strict rule as to which method will work better in any particular case.
**So we suggest you try all three of them.**"

**Note the pattern.** Both vendors' own documentation reduces to: *try things until it looks right.* There is no
automatic, subject-adaptive selection in either product.

### 1.4 Photoshop Auto-Blend Layers

**VERIFIED** (Wayback capture of Adobe help, text unchanged across 2015/2018/2023 captures),
<https://web.archive.org/web/20230603190115/https://helpx.adobe.com/photoshop/using/combine-images-auto-blend-layers.html>:

> "Use the Auto-Blend Layers command to stitch or combine images with smooth transitions in the final composite image.
> Auto-Blend Layers applies layer masks as needed to each layer to mask out over or underexposed areas or content
> differences. **Auto-Blend layers is available only for RGB or Grayscale images.** It does not work with Smart Objects,
> video layers, 3D layers, or background layers."
> "you can blend multiple images of a scene with different areas in focus to achieve a composite image with an extended
> depth of field."

Adobe publishes **no algorithm description whatsoever**. Confirms it is layer-based, i.e. post-demosaic.
Live page is now a JS SPA at `/photoshop/desktop/create-masks/blend-images/create-a-composite-with-extended-depth-of-field.html`
that renders no text to a fetcher.

### 1.5 Capture One — no native focus stacking

**VERIFIED**, <https://support.captureone.com/hc/en-us/articles/360002538538>:
> "When capturing image sequences destined for focus stacking, you can use Capture One to select the appropriate
> sequence and then export the images to the dedicated focus stacking application, **Helicon Focus® by Helicon Soft Ltd.**"

Confirmed by Helicon's own plugin page (**VERIFIED**, <https://www.heliconsoft.com/capture-one-plugin/>):
"Helicon Focus is a standalone application, but it also includes a plugin for integration with Capture One...
Export formats: DNG, JPG or TIFF." Note the round-trip constraint: *"The result will not be imported back into
Capture One until Helicon Focus is closed after saving the result."*

**Lightroom Classic likewise has no focus stacking** (merge features are Panorama and HDR only) — could not confirm
a positive statement; no Adobe help article for LrC focus stacking exists, all candidate URLs 404.

### 1.6 Practitioner complaints (PRACTITIONER-REPORT unless noted)

Primary venue is photomacrography.net, where `rjlittlefield` = **Rik Littlefield, the author of Zerene Stacker**.
His criticisms of his own product are therefore unusually credible.

| # | Topic | Verbatim quote | Source |
|---|---|---|---|
| 1 | PMax halos are structural | "PMax is relentless about preserving apparent detail, and **in featureless regions near sharp detail it's almost guaranteed to produce some sort of halo**." — Littlefield | <https://www.photomacrography.net/forum/viewtopic.php?f=8&t=48579> |
| 2 | PMax halos, concrete | "Using PMax there are some obvious halos around the digits of the watch face." — Littlefield | same |
| 3 | PMax noise/echoes | "ZS PMax was doing its usual tricks of **increasing noise and giving echos and halos everywhere** there was motion or hard-edged OOF blurs." — Littlefield | <https://www.photomacrography.net/forum/viewtopic.php?t=14810> |
| 4 | PMax halos on speculars | "ZS PMax has introduced fuzzy white halos around the brightest facets. **This is common behavior for PMax** with this sort of subject." — Littlefield | <https://www.photomacrography.net/forum/viewtopic.php?f=27&t=9333> |
| 5 | Color mismanagement | "I also know of multiple fine art photographers who have had similar issues with **Zerene mismanaging colors on high-density files**." — John Koerner | <https://www.photomacrography.net/forum/viewtopic.php?f=8&t=14947> |
| 6 | DMap blotches (VENDOR doc) | "One common mistake is to leave the contrast threshold set too low... The result can be **an ugly mess of blotches**." | <https://zerenesystems.com/cms/stacker/docs/tutorials/tutorial003> |
| 7 | DMap fails on smooth areas | "There isn't much detail in that petal, but whatever I do, Dmap can't get all that there is... **The petal becomes an area of red fog.**" — user ChrisR. Littlefield confirms: "typical appearance when DMap can't find actual detail and is **making nearly random decisions based on pixel noise**" | <https://www.photomacrography.net/forum/viewtopic.php?f=8&t=9173> |
| 8 | DMap threshold unusable | User Leon documents CT = 0.2, 10, 20, 30, 40 all producing identical "dark smudges in white spaces, and ghosting around the edges"; only CT = 50 (250× default) clears it | <https://www.photomacrography.net/forum/viewtopic.php?f=8&t=34245> |
| 9 | Depth-map halos are inherent | "Depth map methods by themselves (**DMap in Zerene Stacker, Method B in Helicon Focus**) are prone to producing what I call **'loss of detail' halos**, in which background detail near a foreground edge is completely lost because **the depth map does not slew quickly enough** from foreground to background." — Littlefield | <https://www.photomacrography.net/forum/viewtopic.php?f=28&t=31282> |
| 10 | Helicon mush; bristles vanish | "In favor of Zerene Stacker, it gives cleaner images (**less halo & stacking mush**), especially for deep high magnification stacks." / "In the HF image, **some of the big bristles are simply missing**, and the rest of them look like they've been greased back against the cuticle... This is **a fundamental characteristic of the 3D surface approach** used by HF." — Littlefield, May 2011 | <https://www.photomacrography.net/forum/viewtopic.php?f=8&t=13302> |
| 11 | Helicon support | "I have tried posting emails to the Support area for Helicon, but **receive no response. Does anyone know if the company still exists?**" — user ret1rd, Sep 11 2017 | <https://www.photomacrography.net/forum/viewtopic.php?f=28&t=35295> |
| 12 | PS errors of omission | "Photoshop makes what I call **'errors of omission'**, leaving blurred areas that were sharp in some source images... you would have had **pretty large loss-of-detail halos** around each of those foreground elements." — Littlefield | <https://www.photomacrography.net/forum/viewtopic.php?f=27&t=34749> |
| 13 | PS has no controls | "The bad thing about PS is that **it doesn't have any controls in any case**, so if what it does is not what you want, **you're pushed all the way back to manual retouching**... it becomes **wildly impractical** with some kinds of work we do here." — Littlefield | <https://www.photomacrography.net/forum/viewtopic.php?t=14810> |
| 14 | PS alignment fails on macro | "Photoshop seems to be using a **feature-points** method of alignment, which is typical for panorama registration... in these high mag stacks, **most of the frame is full of featureless blur**. Often the only thing that's in focus are the shafts of bristles. Those doesn't have recognizable features on two axes, only one. As a result, **the feature-finder passes by those areas** and instead locks onto strong features located elsewhere." — Littlefield | same |
| 15 | PS capacity limit | "I'm impressed that you even were able to stack that many images in PS. **My system fails around 35.**" — user elf (Littlefield notes deep stacks generate ~40 GB of read/write in PS) | same |
| 16 | Retouching is a chore | "I simply start working my way through the stack, replacing any soft areas... Finally... I may have to do a bit of clone stamping to eliminate any foreground halos found on background elements. Suffice it to say **it's a pain in the butt!**" — user jessica | <https://www.photomacrography.net/forum/viewtopic.php?f=27&t=34547> |
| 17 | Even the author retouches heavily | "This is... mastered from DMap with **extensive retouching from PMax of the whole stack, from PMax of selected slabs, and from some individual source images**." — Littlefield, on his own 125-frame beetle stack | <https://www.photomacrography.net/forum/viewtopic.php?f=27&t=47713> |
| 18 | Retouching still not enough | "I frequently hear from **perfectionist users that they prefer to do final cleanup in Photoshop**, to take advantage of its vast collection of tools." — Littlefield | <https://www.photomacrography.net/forum/viewtopic.php?f=8&t=49811> |
| 19 | Alignment misled at high mag | "at 10X and above, sometimes **the alignment process gets misled** by how image features change" — Littlefield | <https://www.photomacrography.net/forum/viewtopic.php?f=14&t=49681> |
| 20 | Non-telecentric scale error | "the change in scale amounts to **12 pixels in the 4752 pixels** across the width of the whole frame" — Littlefield, on telecentricity limits | <https://www.photomacrography.net/forum/viewtopic.php?f=8&t=39724> |
| 21 | Field work fails | "**even the slightest movement of the air will make some shots unusable** for focus stacking, even to not getting anything worth using sometimes... **the failure rate was very high**" — user Keith, 15 yrs experience | <https://www.photomacrography.net/forum/viewtopic.php?f=26&t=49541> |
| 22 | RAW round trip is friction | "yes **the raw stacking is a drain on time**, and I only feel like the advantage is a much larger file at the end for cropping purposes." — user 1of1snowflakes | <https://www.photomacrography.net/forum/viewtopic.php?f=27&t=40324> |
| 23 | Users want Bayer-domain | "I used Photoshop CS6 to batch extract blue channels from tiffs, but I'm obviously using **debayered input files and believe 'made up' values** (derived from the red and green pixels in the bayer matrix) **are reducing the quality/accuracy** of the blue channel." — diatom microscopy user | <https://www.photomacrography.net/forum/viewtopic.php?f=8&t=30928> |

**Gaps:** Reddit JSON endpoints returned HTTP 403 on all attempts; DuckDuckGo HTML search bot-blocked; DPReview
forums behind a CAPTCHA wall; `heliconsoft.com/forum/` returned 403; `extreme-macro.co.uk` DNS failure. **No Reddit
or DPReview practitioner quotes could be obtained.** The complaint set above is therefore skewed toward
photomacrography.net (high-magnification specialists) and may under-represent field-macro/naturalist workflows.

---

## 2. Open source

| Project | License | Lang | Last push | Stars | Algorithm | GPU | RAW |
|---|---|---|---|---|---|---|---|
| [PetteriAimonen/focus-stack](https://github.com/PetteriAimonen/focus-stack) | **MIT** | C++ | 2026-01-11 | 658 | Complex wavelet (Forster 2004) | **OpenCL** | No |
| [cmcguinness/focusstack](https://github.com/cmcguinness/focusstack) | Apache-2.0 | Python | 2024-04-26 | 185 | Laplacian sharpness pick | No | No |
| [noah-peeters/ChimpStackr](https://github.com/noah-peeters/ChimpStackr) | **GPL-3.0** | Python | 2026-06-22 | 170 | Laplacian pyramid / depth map / weighted avg | No | Yes (rawpy) |
| [lucalista/shinestacker](https://github.com/lucalista/shinestacker) | **LGPL-3.0** | Python | 2026-08-22 | 164 | Laplacian pyramid | No | Yes (rawpy) |
| [bznick98/Focus_Stacking](https://github.com/bznick98/Focus_Stacking) | none | Python | 2023-09-04 | 55 | — | No | No |
| [Biomedical-Imaging-Group/EDF](https://github.com/Biomedical-Imaging-Group/EDF-Extended-Depth-of-Field) | **GPL-3.0** | Java | 2024-10-03 | 21 | Complex wavelet (Forster 2004) | No | No |
| [iwanders/focus_stacking](https://github.com/iwanders/focus_stacking) | MIT | C++ | 2020-11-28 | 8 | — | No | No |
| [suitable-name/z-stackr](https://github.com/suitable-name/z-stackr) | **MIT** | **Rust** | 2026-07-08 | 1 | Lap. pyramid / guided-filter / multigrid / neural | **wgpu** | Yes (rawler) |
| [nschroeter/stackaroni](https://github.com/nschroeter/stackaroni) | **MIT** | **Rust** | 2026-08-21 | 0 | Phase corr + Laplacian energy + guided filter + Lap. pyramid | No | No (16-bit TIFF) |
| Hugin `align_image_stack` | **GPL-2.0+** | C++ | rel. 2025.0.1, Dec 2025 | SF | SIFT keypoints → optimize position/yaw/pitch/roll/scale → remap. **Align only, no fusion.** | No | No |
| enblend / **enfuse** | **GPL-2.0** | C++ | ~2016, unmaintained | SF | Mertens–Kautz–Van Reeth exposure fusion on Gaussian/Laplacian pyramids; `--contrast-weight` repurposes it for focus | No | No |
| Picolay | Freeware, **non-commercial**, closed source | — | 2026-05-20 (active!) | — | Max variance | No | No |
| CombineZP / CombineZM | Freeware, closed source | — | ~2012, abandoned | — | Proprietary wavelet/pyramid | No | No |
| macrofusion | could not confirm | GTK | ~2013, gone | — | GUI over align_image_stack + enfuse | No | No |

Sources: GitHub REST `/repos/{o}/{r}` and `/repos/{o}/{r}/license` for each; <https://hugin.sourceforge.io/download/>;
<https://sourceforge.net/projects/enblend/>; <https://picolay.de/about.htm>; <https://wiki.panotools.org/Align_image_stack>.

### 2.1 focus-stack is the technical benchmark to beat in OSS

**VERIFIED**, <https://github.com/PetteriAimonen/focus-stack/blob/master/docs/Algorithms.md>. Pipeline:

1. **Align** — OpenCV `findTransformECC`, low-res first, then exposure/WB least-squares match on a few thousand
   sampled pixels, then high-res geometric align. *Neighbour-to-neighbour by default*, because "In a deep stack the
   extreme images are often very blurry and cannot be successfully aligned to the center of the stack."
2. **Grayscale** — **PCA** to pick the channel combination with largest variance. (Clever; most tools use fixed luma.)
3. **Complex wavelet transform**, merged in batches.
4. **Merge** — Forster et al. 2004: max-|coefficient| per position, then "filtering... to select the majority pixel
   among spatial neighbours and among horizontal/vertical/diagonal subbands."
5. **Wavelet denoise** — threshold + scale.
6. **Color reassignment** — picks a real color from the stack matching the merged grayscale, so "all output pixels are
   of a value that actually exists in at least one stack image, avoiding artefacts from color interpolation."

Its own README admits the same class of failure as the commercials (**VERIFIED**, Algorithms.md):
> "Currently the merge algorithm has some trouble with **halo effects**, where the blurred version of a high-contrast
> feature is selected at a position that should otherwise have flat color. **The color reassignment tends to make these
> artefacts more visible**, as there isn't a good match for the blurred color at that pixel position."

Memory (**VERIFIED**, README): "approximately 100 MB of RAM is required per 1 megapixel of input image resolution...
total number of images in stack does not significantly affect memory usage." Same figure as Zerene.
Notably it processes in **batches** (`--batchsize=8`) — a genuinely good architectural idea we should match or beat.

### 2.2 Rust prior art — two projects, both very new

**`z-stackr`** (MIT, 7 published crates, 1 GitHub star, last push 2026-07-08) is the closest thing to what we are
proposing and is worth studying as a *design* reference (MIT, so reading is safe). Per its README (**VENDOR-CLAIM**,
<https://raw.githubusercontent.com/suitable-name/z-stackr/main/README.md>): four fusion modes (Apex = Laplacian
pyramid; Relief = guided filter or multigrid depth solver; Strata = guided-filter soft blend; Neural = `FocusMergeNet`
on Burn), LKT coarse-to-fine alignment with optional AKAZE+RANSAC seed, `std::simd`/AVX-512, out-of-core tiling,
PyO3 bindings, Slint GUI, **experimental wgpu compute-shader path** covering Apex fusion, warp, Strata saliency and
Relief's guided-filter and multigrid hot loops.

**Critically, it is NOT Bayer-domain.** Its README states RAW is handled by `rawler` — "RAW container/Bayer-pattern
decode plus **its own default demosaic/white-balance/gamma develop pipeline**". It demosaics up front like everyone
else. It also publishes **no timings**.

**`stackaroni`** (MIT, 0 stars, last push 2026-08-21): phase correlation (Kuglin & Hines / Reddy & Chatterji) with
log-polar scale estimate → windowed Laplacian energy → guided filter (He/Sun/Tang) weight refinement → Laplacian
pyramid fusion (Burt & Adelson, Burt & Kolczynski selection). 16-bit TIFF only, no GPU, no RAW. Self-described:
"It works and is in use, but it is one person's tool."

**Assessment: there is no established Rust incumbent.** Both projects are <2 months to ~7 weeks old at time of
research, have 0–1 stars, and neither is Bayer-domain. The field is genuinely open. But **the obvious names are gone.**

### 2.3 crates.io search record

Queries run against `https://crates.io/api/v1/crates?q=<q>&per_page=8` on 2026-08-22:

| Query | Relevant hits |
|---|---|
| `focus-stack` | z-stackr-{pipeline,algo,align,nn,gui,core,cli} — **all 7 taken** |
| `focus_stacking` | none relevant (crabcamera, paneru, jj-gt … keyword collisions) |
| `image-fusion` | **zero results** |
| `exposure-fusion` | **zero results** |
| `wavelet-fusion` | **zero results** |
| `laplacian-pyramid` | z-stackr-algo only |
| `image-stacking` | `imcombiners` (astronomy IRAF imcombine parity) |
| `rawler` | rawler 0.7.2, zenraw 0.2.0, limbus 0.0.0 |

**Could not confirm absence** of a focus-stacking crate under some unrelated name — crates.io full-text search is
fuzzy and returned heavy noise. But the search space above is well covered. Notably `image-fusion`,
`exposure-fusion` and `wavelet-fusion` are **all unclaimed**.

---

## 3. Adjacent tooling

| Project | License | Lang | Focus stacking? | Notes |
|---|---|---|---|---|
| darktable | **GPL-3.0** | C + OpenCL | **No** — full `src/iop` module list enumerated via GitHub API, no focus-blend module | 12,971★, rel. 5.6.0 (2026-06-21). Reference for OpenCL-accelerated scene-referred pipeline. |
| RawTherapee | **GPL-3.0** | C++ | No | 4,124★. AMaZE / LMMSE / IGV demosaic are the reference implementations. |
| ART | likely GPL-3.0 (derivative of RawTherapee; could not confirm license file — Bitbucket tree not fetchable) | C++ | No | <https://bitbucket.org/agriggio/art/raw/master/README.md> |
| Filmulator | **GPL-3.0** | C++/QML | No | 756★. Depends on libraw. |
| LibRaw | **LGPL-2.1 OR CDDL-1.0** (your choice) | C++ | n/a | <https://www.libraw.org/about>. rel. 0.22.2 (2026-07-16). |
| dcraw | public domain except a GPL-2 "RESTRICTED" path | C | n/a | **Dead.** LibRaw: "support for dcraw.c was reduced to a minimum in 2015, and **completely ceased in 2018**." |
| DNGLab / rawler | **LGPL-2.1** | **Rust** | n/a | 658★, v0.7.2. Self-described "alpha state" but actively maintained. |

### 3.1 Sony A7C II support in rawler — CONFIRMED

**VERIFIED**, <https://github.com/dnglab/dnglab/blob/main/SUPPORTED_CAMERAS.md>: row `SONY | ILCE-7CM2 | ✅ Yes | all`.
Our exact reference body is supported, all modes. Also confirmed: ILCE-7CR, ILCE-7M4, ILCE-7RM5, ILCE-9M3, ILCE-1M2.

### 3.2 Rust RAW/imaging crates

| Crate | Ver | License | Updated | Downloads | Pure Rust |
|---|---|---|---|---|---|
| `rawloader` | 0.37.2 | **LGPL-2.1** | 2026-08-15 | 312,423 | Yes |
| `imagepipe` | 0.5.1 | **LGPL-3.0-only** | 2026-08-15 | 116,948 | Yes |
| `rawler` | 0.7.2 | **LGPL-2.1** | 2026-02-26 | 107,720 | Yes |
| `libraw-rs` | 0.0.4 | MIT/Apache-2.0 (bindings only) | **2021-02-02 — stale** | 49,011 | No (FFI) |
| `zune-image` | 0.5.0 | MIT OR Apache-2.0 OR Zlib | 2026-01-24 | 85,451 | Yes (no RAW) |
| `image` | 0.25.10 | MIT OR Apache-2.0 | 2026-03-10 | 172M | Yes (no RAW) |

**This is the single biggest architectural constraint on the project.** Every viable pure-Rust RAW decoder is LGPL.

> **SUPERSEDED — see [§F1.1](#f11--the-licensing-trap-i-was-too-cautious-correcting-myself).** Follow-up research
> established that LGPL-2.1 §6(a)/(d) are satisfied trivially by an open-source project, and that 11 permissively
> licensed Rust crates already depend on `rawler`/`rawloader`. This is a minor compliance chore, not an
> architectural constraint. Use `rawler`.

### 3.3 Microscopy / industrial EDOF

Zerene's own origin is this world. Differences worth stealing from: calibrated piezo z-drives (0.05–5 µm steps) mean
**alignment is often unnecessary**; PSF-based deconvolution rather than pure sharpness-picking (Zeiss ZEN EFI,
Leica LAS X, Nikon NIS-Elements — **could not confirm** algorithm details, all vendor pages are marketing-only);
outputs include a topography/depth map as a first-class product, not an afterthought.
Industrial machine-vision EDOF frequently avoids bracketing entirely via **wavefront coding** (cubic phase mask +
computational deconvolution, after Dowski & Cathey 1995) to get all-in-focus from a *single* exposure.
Not directly applicable to a Sony body, but the depth-map-as-product idea is.

---

## 4. Workflow reality

### 4.1 Capture

Sony A7C II has capable in-camera focus bracketing. **VERIFIED**,
<https://helpguide.sony.net/ilc/2360/v1/en/contents/211h_focus_bracket.html> (manual 5-054-865-15(3), ILCE-7CM2):

- **Step Width 1–10**; **Number of Shots 2–299**.
- "The [Step Width] value is a **relative** value, and the focus interval varies depending on shooting conditions such
  as the aperture of the lens and the initial focus position. **It is recommended that you take a test shot** to find
  the appropriate focus width."
- "If the camera or lens moves while shooting with the focus bracket, focus stacking may not be successful."

The step width being *relative and uncalibrated* is a real opportunity: **the camera does not tell you the actual
focus distance per frame.** A tool with a lens optical model could infer it.

Ring vs rail — **VERIFIED**, <https://zerenesystems.com/cms/stacker/docs/troubleshooting/ringversusrail>:
"The short answer is that it's usually better to use the ring." Rails cause magnification change ("zoom-burst"
background artifact); focus rings keep magnification near-constant. Rails remain necessary above ~1× / on bellows.

Step size — **VERIFIED**, <https://zerenesystems.com/cms/stacker/docs/tables/macromicrodof>,
DOF = (0.0022 × N² × (m+1)²) / m². At 1:1, f/8 → ~0.52 mm; at 2×, f/8 → ~0.14 mm; at 5×, f/8 → ~0.046 mm.
Zerene notes "Many people like to use about **0.7 times** the values given in these tables."
Recommended empirical method: shoot far too finely, then process with "stack every N'th frame" for N = 1,2,3,4… and
find the largest N without focus banding. **That is a manual search a good tool should automate.**

Reference workload sanity check: 20–60 frames is a *shallow-to-moderate* stack by this community's standards. 100–300
is routine at high magnification; the vendor forum has 728-frame mosaic projects.

### 4.2 The RAW round trip

**VERIFIED**, Zerene FAQ: "To process any format of raw files, including DNG, takes two separate steps. First you
convert the raw files to some standard RGB format, typically TIFF, and then you stack the TIFF files. For highest
quality, we recommend converting raw files to **16-bit TIFF**... adjust colors and curves, do highlight recovery, and
apply basic noise reduction, **so that the TIFF files going into Zerene Stacker look as much as possible like what you
eventually want in the end.** (If you're using PMax, then it's usually a good idea to **leave the contrast a little low
because PMax tends to increase that**.)"

Read that last parenthesis again. **The vendor is telling users to pre-distort their tone curve to compensate for a
known algorithm defect.** That is the workflow pain in one sentence.

Lightroom plugin (Pro-only) exports **16-bit TIFF in AdobeRGB** by default and "will not work with Adobe's cloud-based
product that is now named simply 'Lightroom'" (**VERIFIED**, <https://zerenesystems.com/cms/stacker/docs/workingwithlightroom>).

So the real-world pipeline is: ARW → (Lr/C1 develop) → 16-bit TIFF ×N on disk → stacker → TIFF → back to Lr/C1 → export.
For 60 × 33 MP that is roughly **12 GB of intermediate TIFFs** written and read for a single stack.

### 4.3 Retouching — essential, or a workaround?

**It is a workaround, and both vendors quietly admit it.** Zerene's docs say plainly that on hard subjects "neither
method is ideal by itself" and the fix is "human judgment and the retouching tool". Littlefield needed "extensive
retouching" on his own 125-frame stack (#17). Users still escape to Photoshop afterward (#18). Helicon markets
"truly unique retouching brushes" as a headline *feature*.

Nuance for our design: the retouch brush is genuinely valuable as an **escape hatch and as a trust mechanism** — it
lets a user fix the one thing the algorithm got wrong without redoing everything. We should ship one. But the volume
of retouching currently required is a measure of algorithmic failure, not of feature richness. **"Slabbing"**
(<https://zerenesystems.com/cms/stacker/docs/slabbing>) exists specifically to make retouching tractable on deep
stacks by reducing the number of candidate source frames from ~200 to ~15 — a workaround for a workaround.

---

## 5. Is anything RAW-native / Bayer-domain? **No.**

| Tool | Claim | Evidence |
|---|---|---|
| Zerene Stacker | Explicitly not | "**no stacking software really works directly with raw files.** The structure of data in a typical raw image file, one value per photosite with color implied by a mosaic Bayer filter pattern, is **fundamentally incompatible with the image alignment process** that is required for stacking." — <https://zerenesystems.com/cms/stacker/docs/faqlist> |
| Helicon Focus | RAW *ingest*, but demosaics before aligning | "To align source images Helicon Focus needs to scale, shift and sometimes rotate images. To do this, **source images should be converted from original raw sensor data to so called interpolated RGB image. This process is also called demosaicing or debayering.** Helicon Focus uses **Adobe DNG Converter** to demosaic raw images." — <https://www.heliconsoft.com/raw-in-dng-out/> |
| Photoshop | No | Auto-Blend operates on RGB/Grayscale *layers* |
| Affinity | RAW ingest, develops internally first | could not confirm from official docs (affinity.help 403, no Wayback captures) |
| z-stackr (Rust) | RAW ingest, demosaics via rawler develop pipeline | README, §2.2 above |
| ChimpStackr / ShineStacker | RAW ingest via rawpy → LibRaw demosaic | their READMEs |

**Helicon's "RAW-in-DNG-out" is the closest anyone has come, and it is not Bayer-domain.** What it actually does is
defer *white balance and highlight clipping* to after stacking, by keeping raw data around and re-developing on the
fly for display, then emitting a **linear DNG** (already demosaiced — "linear DNG files are big, roughly of the same
size as 16 bit per channel TIFF files"). Genuinely useful, and worth matching; but the fusion still happens on
interpolated RGB.

**The stated objection is real and must be answered, not ignored.** Littlefield's argument (#23 thread,
<https://www.photomacrography.net/forum/viewtopic.php?f=8&t=13302&p=84898>) is:
> "if you shift or scale by anything other than exact multiples of 2 pixels, the colors get messed up... featureless
> intense blue turns into featureless intense red."

This is correct *if* you naively resample the CFA plane as a single image. It is not an argument against
Bayer-domain focus *measurement*, nor against per-CFA-plane warping, nor against fusing in a demosaic-agnostic
representation and demosaicing once at the end. **This is precisely the gap.** No shipping tool has tried it, and the
most authoritative voice in the field has publicly declared it impossible — which is exactly the sort of claim that
is worth testing carefully, and exactly the sort of differentiation that is defensible if it works.

Search record for "could not confirm" purposes: queries `focus stacking language:Rust`, `image fusion language:Rust`,
`focus stacking`, `focus-stacking`, `extended depth of field` on the GitHub search API; crates.io queries in §2.3;
plus Zerene FAQ, Helicon feature pages, and the photomacrography.net Bayer thread. **No tool claiming Bayer-domain
focus stacking was found in any of these.**

---

## 6. The performance bar

### 6.1 Helicon's own published benchmark — the most useful number available

**VERIFIED**, <https://heliconsoft.com/helicon_focus_benchmark/view.php>. Conditions stated on the page:
> "Stack: **100 in-memory images, method B.** Images: **5616x3744, 16 bits per channel, 3 channels.**
> Performance is calculated in **Megapixels per second** (5616*3744*100/1000000/time)"

| Hardware | MP/s |
|---|---|
| AMD RX 6800 XT + Ryzen 9 5900X | **1,956** |
| RTX 3090 + Threadripper 3960X | 1,422 |
| RTX 3090 | 987 |
| RTX 3060 + Ryzen 9 3950X | 963 |
| RTX 2080 Ti | 903 |
| GTX 1080 Ti | 657 |
| **CPU only:** Ryzen 9 5900X (12c) | **356** |
| CPU: Ryzen 9 3900X (12c) | 276 |
| CPU: i7-9800X (8c) | 205 |
| CPU: i7-10750H (6c) | 169 |

**Read the conditions carefully: "in-memory images".** This benchmark excludes file I/O, RAW decode, and
almost certainly alignment. It measures the **fusion kernel throughput only**. Label: **VENDOR-CLAIM**, and a
best-case one.

**What this implies for our reference workload** (arithmetic, mine):

| Workload | Total MP | @1,956 MP/s | @987 MP/s | @356 MP/s (CPU) |
|---|---|---|---|---|
| 33 frames × 33 MP | 1,089 | 0.6 s | 1.1 s | 3.1 s |
| 60 frames × 33 MP | 1,980 | 1.0 s | 2.0 s | 5.6 s |

**Conclusion: pyramid/depth-map fusion of a 60×33 MP stack is a ~1–6 second problem.** Anything materially slower is
spending its time on I/O, decode, alignment, or a bad implementation — not on the fusion mathematics.

### 6.2 End-to-end practitioner timings (PRACTITIONER-REPORT)

These are *wall-clock, whole-application* numbers on old hardware and are 2–3 orders of magnitude off §6.1.

| Report | Numbers | Source |
|---|---|---|
| ZS vs HF, same stack | "a time ratio of over 5 to 1 — **46 minutes for ZS versus 9 minutes for HF**" | <https://www.photomacrography.net/forum/viewtopic.php?f=8&t=7084> |
| Littlefield's own bench, 2.4 GHz Core 2 Quad, HF 4.75.5 | "**4:02 for ZS PMax** versus **2:24 for HF Method A** and an additional **3:51 for HF Method B**" | same |
| ChrisR, stereo stack, older machine | "**30 seconds per frame, x 147 images per stack, x 5 'views'**" → overnight. Littlefield: "30 seconds per frame is huge... my Core 2 Q6600 does **6 megapixel images at 100% in 3 seconds per frame**" | <https://www.photomacrography.net/forum/viewtopic.php?f=28&t=7644> |
| Photoshop CS5, deep stacks | "**taking forever** to process them and making more errors than Zerene" — J. Koerner. Littlefield notes ~**40 GB read/write** for a deep PS stack | <https://www.photomacrography.net/forum/viewtopic.php?f=8&t=14947>, <https://www.photomacrography.net/forum/viewtopic.php?t=14810> |

Littlefield's "6 MP in 3 s/frame" on a Q6600 = **2 MP/s** end-to-end for Zerene, circa 2009 hardware.
These are old machines; I **could not find** any published Zerene or Helicon end-to-end timing on modern hardware with
40+ MP files. That is a genuine gap — searched photomacrography.net for stacking-speed threads and found nothing
recent and quantitative.

### 6.3 Setting the bar

*Context, not a finding: the prior C++/OpenCV project achieved ~90 s for a 33-frame 33 MP stack on an RTX 5090,
mostly CPU-bound. That is ~12 MP/s end-to-end — i.e. ~30× slower than Helicon's CPU-only fusion kernel and ~160×
slower than its GPU kernel.*

A defensible target, given §6.1: **60 frames × 33 MP end-to-end (ARW decode → align → fuse → 16-bit output) in
under 15 s on a modern GPU**, with fusion itself in the low single-digit seconds. That is ~130 MP/s end-to-end —
still well below Helicon's fusion-only kernel throughput, so it leaves generous budget for decode and alignment,
and it would be roughly 7× faster than the prior project. Being "faster than Helicon" is *not* the hard part;
Helicon's fusion is already near-instant. **The differentiator is doing the whole pipeline — including RAW decode
and robust alignment — at that speed, and being better at the same time.**

---

## 7. Universal weaknesses, ranked

Ranked by how much a working macro photographer would actually care.

| # | Weakness | Why it matters | Evidence |
|---|---|---|---|
| **1** | **No tool gets hard subjects right automatically; retouching is mandatory.** Every product ships a manual brush because its algorithms fail predictably. | This is the dominant time cost in the workflow — tens of minutes per image. It is the whole ballgame. | Zerene FAQ: "neither method is ideal by itself"; #16, #17, #18 |
| **2** | **Halos are structural in every algorithm, and each family fails differently.** Pyramid/PMax/Method C → bright inversion halos, contrast and noise gain, color shift. Depth-map/DMap/Method B → loss-of-detail halos where the map "does not slew quickly enough", plus blotching on smooth regions. | Halos are what forces the retouching in #1. Users must currently run *both* algorithm families and hand-blend the results. **An algorithm that gets both right, or an automatic per-region arbiter between them, is the single largest quality win available.** | Zerene FAQ (both quotes); Helicon: Method C "increases contrast and glare"; #1–#4, #6–#9 |
| **3** | **Every tool demands manual parameter tuning with no good defaults, and provides no way to know if you got it right.** DMap contrast threshold, estimation/smoothing radius, Helicon radius and smoothing, method A/B/C choice. | Guess-and-recheck loops on 33 MP files. Both vendors literally say "try them all". No tool reports confidence or flags regions it is unsure about. | Helicon: "we suggest you try all three of them", "no strict rule"; Zerene: "must be determined by experiment"; #8 (CT 0.2→50) |
| **4** | **The RAW round trip is lossy, slow, and requires pre-compensating for algorithm defects.** No tool is Bayer-domain; the best (Helicon) demosaics via Adobe DNG Converter then emits linear DNG. ~12 GB of intermediate TIFFs per 60-frame stack. | Highlight recovery and WB decisions get locked in *before* stacking. Zerene tells users to flatten contrast to counteract PMax. | Zerene FAQ; <https://www.heliconsoft.com/raw-in-dng-out/>; #22 |
| **5** | **Alignment is fragile exactly where macro is hard**: focus breathing/magnification change, non-telecentric corner scale error, near-featureless blurred frames, subject motion from wind. Photoshop's feature-point matcher fails outright on bristles. | Determines whether the stack is usable at all. Field macro has a "very high" failure rate. | #14, #19, #20, #21; Sony's own warning |
| **6** | **No confidence/uncertainty output.** Nothing tells the user *which* pixels are suspect, so retouching is a manual visual hunt across a 33 MP frame. | Directly multiplies the cost of #1. A per-pixel confidence map would be a genuinely novel and cheap deliverable. | Absence — no tool in §1/§2 documents one |
| **7** | **Deep stacks are architecturally awkward.** Photoshop fails ~35 images / 40 GB I/O; Zerene needs 100–200 MB RAM per MP; "slabbing" exists purely to make big stacks tractable. | Bites at 100+ frames, which is routine at high magnification, though above our 20–60 reference. | #15; Zerene memory spec; slabbing doc |
| **8** | **GPU acceleration is absent or paywalled.** Zerene: CPU only. Helicon: OpenCL is **Pro tier and above**. focus-stack: OpenCL. Everything in Python: none. | Less important than it sounds — see §6.1, fusion is already fast. Matters for *interactive* preview, which nobody offers. | §2 table; Helicon licensing table |
| **9** | **No optical/lens modelling anywhere.** Sony's focus-bracket Step Width is explicitly "a relative value"; no tool ingests lens or magnification data to predict per-frame focus distance or expected scale change. | Would improve alignment priors and enable true depth output. Nobody has tried. | Sony help guide; absence across §1/§2 |
| **10** | **Ecosystem friction / vendor risk.** Capture One has no native stacking; Zerene's Lr plugin is Pro-only and does not support cloud Lightroom; Helicon support reportedly unresponsive; C1 round trip requires *closing* Helicon. | Annoying, not fatal. | §1.5; #11; <https://zerenesystems.com/cms/stacker/docs/workingwithlightroom> |

---

## 8. Licensing traps — per project

**Governing assumption: the new project is MIT/Apache-2.0.**

### 8.1 DO NOT READ THE SOURCE — copyleft, contamination hazard for a permissive rewrite

| Project | License | Hazard |
|---|---|---|
| **enfuse / enblend** | **GPL-2.0** | Do not read. This is the canonical open-source fusion implementation, which makes it the most tempting and the most dangerous. Also GPL-2.0 *only* — incompatible even with GPL-3.0. |
| **Hugin / align_image_stack** | **GPL-2.0+** | Do not read the alignment source. Reading the *`--help` output and the panotools wiki page* is fine and sufficient to understand the option surface. |
| **EPFL EDF plugin** (Biomedical-Imaging-Group) | **GPL-3.0** | Do not read the Java. **However — the Forster et al. 2004 paper is a normal academic publication and implementing from the paper is fine.** focus-stack's `docs/Algorithms.md` (MIT) is also a safe secondary description. |
| **ChimpStackr** | **GPL-3.0** | Do not read. |
| **ShineStacker** | **LGPL-3.0** | LGPL, so *linking* would be permissible, but it is Python and we are not linking it. Do not copy source. |
| **deptheos** | GPL-3.0 | Do not read. |
| **darktable** | **GPL-3.0** | Do not read the demosaic or colour-pipeline source. This is a real risk because darktable is the obvious reference for scene-referred colour handling. Use published papers and darktable's *user documentation* instead. |
| **RawTherapee / ART** | **GPL-3.0** (ART license file could not be confirmed, but it is a RawTherapee derivative) | Do not read AMaZE/LMMSE/IGV source. Demosaic algorithms are published in the literature — implement from papers. |
| **Filmulator** | GPL-3.0 | Do not read. |
| **dcraw** | Public domain **except** a "RESTRICTED" GPL-2 code path | Mostly safe historically, but the boundary is unclear and the project is dead since 2018. Not worth the risk or the effort. |

### 8.2 LINKING HAZARDS — the real architectural problem

Every viable pure-Rust RAW decoder is LGPL:

| Crate | License | Consequence |
|---|---|---|
| `rawler` | **LGPL-2.1** | Rust has no practical dynamic linking story. Statically linking an LGPL-2.1 crate into an MIT binary obliges you to enable relinking (ship object files or equivalent). This is awkward but *is* what `z-stackr` does — behind an optional `raw` feature flag, which is the standard mitigation: the core stays clean MIT and RAW support is an opt-in build. |
| `rawloader` | **LGPL-2.1** | Same. |
| `imagepipe` | **LGPL-3.0-only** | Worse — LGPL-3.0-only. Avoid. |
| `libraw-rs` | MIT/Apache bindings over **LGPL-2.1 OR CDDL-1.0** LibRaw | Bindings are permissive but **stale since 2021-02-02** (v0.0.4, 3 releases ever). Underlying LibRaw terms still apply. LibRaw's dual license means you may elect CDDL-1.0, a *file-level* weak copyleft that combines with MIT in a "Larger Work" more comfortably than LGPL — this is arguably the cleanest legal path, at the cost of a C++ dependency. |

**Recommended posture** (this is a legal question, flag for counsel):
1. Keep the core engine MIT/Apache with **zero** LGPL in the default feature set.
2. Put ARW decode behind an optional feature (`--features raw`), as z-stackr does, using `rawler` (LGPL-2.1) — and be honest in the README about what that means for redistribution.
3. Consider writing an **ARW-only** decoder from the format specification. Sony ARW is well-documented and we only need one manufacturer initially. This would eliminate the entire LGPL problem, and given Bayer-domain ambitions we need low-level CFA access anyway rather than a develop pipeline. **This deserves serious evaluation as a first-class option, not a fallback.**

> **PARTLY SUPERSEDED — see [§F1.1](#f11--the-licensing-trap-i-was-too-cautious-correcting-myself).** The *licensing*
> rationale for item 3 is withdrawn. The *technical* rationale (Bayer-domain CFA access) survives, but should be
> tested against what `rawler` already exposes before any decoder work starts. Cost if built: ~2–3 weeks for
> uncompressed + lossy (Apache-2.0 reference exists in `rawkit`), **2–4 months** for all three modes — no permissive
> implementation of Sony's lossless/LJPEG mode exists in any language.

### 8.3 SAFE TO READ

| Project | License |
|---|---|
| **PetteriAimonen/focus-stack** | **MIT** — safe to read. Its `docs/Algorithms.md` is the best free technical description in the field. |
| **z-stackr** (+ all 7 crates) | **MIT** — safe to read. Best available Rust design reference. |
| **stackaroni** | **MIT** — safe to read. |
| **cmcguinness/focusstack** | Apache-2.0 — safe. |
| **iwanders/focus_stacking** | MIT — safe. |
| `image`, `zune-image` | MIT/Apache — safe to use and read. |
| Academic papers (Forster 2004, Burt & Adelson 1983, Burt & Kolczynski 1993, Mertens 2007, He/Sun/Tang guided filter, Kuglin & Hines, Reddy & Chatterji) | Publications — safe to implement from. |
| `bznick98/Focus_Stacking`, `pulsar123/Macro-scripts` | **No license file = all rights reserved.** Not GPL, but *not* safe to copy either. Do not read. |

---

## 9. Names already taken

Avoid: `z-stackr` and `z-stackr-{core,cli,gui,algo,align,nn,pipeline}` (crates.io, MIT, active),
`stackaroni`, `focus-stack`, `focusstack`, `ChimpStackr`, `shinestacker`, `millefeuille` (a Rust *camera controller*
for focus stacking), `deptheos`, `Picolay`, `CombineZP`/`CombineZM`, `macrofusion`, `imcombiners`.

**Available on crates.io as of 2026-08-22** (zero search results): `image-fusion`, `exposure-fusion`,
`wavelet-fusion`. Verified via `https://crates.io/api/v1/crates?q=<term>`.

---

## 10. Gaps and uncertainties

| Item | Status |
|---|---|
| Reddit / DPReview practitioner voices | **Not obtained.** Reddit JSON endpoints → HTTP 403 on all variants; DPReview → CAPTCHA wall; DuckDuckGo HTML → bot-blocked. Complaint corpus is skewed to photomacrography.net high-mag specialists. |
| Affinity Photo Focus Merge official docs | **Could not confirm.** affinity.help → 403; no Wayback captures of the Focus Merge page; forum.affinity.serif.com → 403. Affinity's *pricing* (free forever) IS verified via <https://www.canva.com/newsroom/news/all-new-affinity/>. |
| Adobe checkbox wording ("Seamless Tones and Colors", "Content-Aware Fill Transparent Areas") | **Could not confirm.** Live page is a React SPA; Wayback captures only the intro paragraph across 2015/2018/2023. |
| Adobe / Capture One dollar pricing | **Could not confirm.** Both pricing pages populate via JS; archived copies show empty containers. |
| Modern end-to-end timings for Zerene/Helicon on 40+ MP, 50+ frames | **Could not find.** Only 2009–2011-era numbers exist on photomacrography.net. §6.1's vendor benchmark is the best modern proxy and is fusion-kernel-only. |
| Zeiss ZEN / Leica LAS X / NIS-Elements EDF algorithms | **Could not confirm.** All vendor pages are marketing-only, no technical detail. |
| Luminar Neo / DxO PhotoLab / ON1 focus stacking | **No evidence found**, but several candidate URLs 404'd. Treat as "probably absent, not proven absent". |
| enfuse exact last release date | **Could not confirm** — SourceForge files pages return interstitial ad pages. Community consensus and Hugin's own notes put it ~2016 and unmaintained. |
| macrofusion | **Could not locate at all** — Launchpad 404, SourceForge ad-blocked, GitHub search zero results. Treat as dead. |
| Whether Bayer-domain fusion actually works | **Unresolved and untested by anyone.** This is the central technical bet, not an established fact. §5 argues the standard objection is narrower than it is usually stated, but that is analysis, not evidence. |

---
---

# Follow-up 1

Research date 2026-08-22, same session. Same labelling convention (VERIFIED / VENDOR-CLAIM / PRACTITIONER-REPORT).

## F1.1 — The licensing trap: I was too cautious. Correcting myself.

**Headline: LGPL-2.1 is not fatal, and for a project like ours it is close to free. My §8.2 recommendation to
write an ARW decoder to escape LGPL was wrong, and I am withdrawing it as a *licensing* argument.** There may still
be a good *technical* reason to write one (Bayer-domain access) — but that is a different argument, made below.

### Why LGPL static linking is a non-issue here

**VERIFIED**, LGPL-2.1 §6 full text, <https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html>:

> "**6.** As an exception to the Sections above, you may also combine or link a "work that uses the Library" with the
> Library to produce a work containing portions of the Library, and **distribute that work under terms of your choice**,
> provided that the terms permit modification of the work for the customer's own use and reverse engineering for
> debugging such modifications... you must do one of these things:
> **a)** Accompany the work with the complete corresponding machine-readable source code for the Library... **and, if
> the work is an executable linked with the Library, with the complete machine-readable "work that uses the Library",
> as object code and/or source code, so that the user can modify the Library and then relink** to produce a modified
> executable...
> **d)** If distribution of the work is made by offering access to copy from a designated place, offer equivalent
> access to copy the above specified materials from the same place."

Read 6(a) carefully. The onerous part — "ship object files so the user can relink" — exists to protect users of
**closed-source** binaries. **We publish our complete source under MIT/Apache on GitHub.** A user who wants to swap in
a modified `rawler` clones our repo, edits `Cargo.toml`, and runs `cargo build`. Relinking is not merely possible, it
is the normal way anyone builds the project. 6(a) is satisfied by the act of being open source; 6(d) is satisfied by
GitHub releases sitting next to the source repo.

Residual obligations, which are real but trivial:
1. **Prominent notice** that `rawler` is used and is under LGPL-2.1.
2. **Ship a copy of the LGPL-2.1 text** with binary releases.
3. Include rawler's copyright notice if the app displays copyright notices at runtime.
4. Do **not** relicense rawler itself, and keep any modifications to it under LGPL.

The one genuine consequence: **a downstream party cannot take our binary into a closed-source product without doing
their own LGPL compliance.** That constrains *them*, not us. If a permissive-for-proprietary-reuse story is a project
goal, put RAW behind a `--features raw` flag so the default build is LGPL-free — cheap insurance, and it is exactly
what `z-stackr` does.

### Has anyone in Rust actually done this? Yes, routinely. (VERIFIED)

Reverse dependencies via `https://crates.io/api/v1/crates/{rawler,rawloader}/reverse_dependencies`:

| Depends on | Crate | Its declared license |
|---|---|---|
| `rawler` (LGPL-2.1) | `rawbit` | **MIT** |
| `rawler` | `scryglass` | **MIT** |
| `rawler` | `z-stackr-core` | **MIT** |
| `rawler` | `limbus` | **MIT OR Apache-2.0** |
| `rawler` | `czkawka_core` | **MIT** |
| `rawloader` (LGPL-2.1) | `stardetect` | **Apache-2.0** |
| `rawloader` | `image-hdr` | **Apache-2.0** |
| `rawloader` | `img4avif` | **Apache-2.0** |
| `rawloader` | `skia-rs-codec` | **MIT OR Apache-2.0** |
| `rawloader` | `simp` | **Apache-2.0** |
| `rawloader` | `plakat` | **Unlicense** |

Eleven permissively-licensed crates depend on LGPL RAW decoders. This is **settled, unremarkable practice** in the
Rust ecosystem. (Caveat: a crate's declared license governs *its own source*, which is all crates.io distributes —
it does not by itself discharge §6 obligations for anyone shipping a combined *binary*. But as shown above, for an
open-source project those obligations are near-zero.)

**Verdict: use `rawler`. It is LGPL-2.1, actively maintained (v0.7.2, 107,720 downloads), pure Rust, and
confirmed to support ILCE-7CM2 in all modes. Do not write a decoder to avoid its licence.**

### If we write one anyway: how much work? (The technical argument)

The *technical* reason to write our own is Bayer-domain access. `rawler` "does its own default demosaic/white-balance/
gamma develop pipeline" — but note it also exposes container/CFA decode, so **evaluate whether rawler alone gives us
raw CFA planes before assuming we need to write anything.** That check should precede any decoder work.

If we do build one, the scope for an A7C II:

| Mode | Status | Permissive reference? |
|---|---|---|
| Uncompressed 14-bit | Easy — packed bit reader | ✅ Graphite `uncompressed.rs` (2,393 B) |
| **Lossy** "Compressed RAW" (Sony 11+7 delta, 16-px blocks) | Moderate | ✅ **Graphite `arw2.rs` (4,195 B)** |
| **Lossless Compressed** L/M/S (LJPEG / ITU-T T.81 Huffman) | **Hard — the whole cost** | ❌ **None anywhere, in any language** |

**VERIFIED**: `GraphiteEditor/Graphite` is **Apache-2.0** (<https://github.com/GraphiteEditor/Graphite/blob/master/LICENSE.txt>),
and its RAW library is published as crate **`rawkit` v0.1.0, license `MIT OR Apache-2.0`**, updated 2024-11-03,
1,216 downloads (<https://crates.io/api/v1/crates/rawkit>). Decoder directory contents verified via GitHub API:
`arw1.rs` 3,284 B, `arw2.rs` 4,195 B, `uncompressed.rs` 2,393 B, `mod.rs` 50 B. **There is no lossless/LJPEG file.**

Complexity proxy — `rawler` file sizes via GitHub API (sizes only; **source not read**): `decoders/arw.rs` 29,530 B,
`ljpeg92.rs` 48,411 B, `decompressors/ljpeg/*` ~33 KB, `decompressors/packed.rs` 48,587 B. **The LJPEG machinery is
larger than the Sony decoder itself** — that is where the work is.

Estimate: **lossy+uncompressed only ≈ 2–3 weeks** (Apache-2.0 reference exists). **All three modes ≈ 2–4 months**,
dominated by writing LJPEG from ITU-T T.81. Not a weekend. Given that `rawler` already works and is legally usable,
**a from-spec decoder is not justified for v1.**

Clean specification sources, if ever needed: **TIFF 6.0** (public domain, <https://www.loc.gov/preservation/digital/formats/fdd/fdd000188.shtml>);
**ITU-T T.81** lossless JPEG (free download, <https://www.itu.int/rec/T-REC-T.81/en>); **Adobe DNG spec** — royalty-free
patent grant, "Adobe hereby grants all individuals and organizations the worldwide, royalty-free, nontransferable,
nonexclusive right... to make, have made, use, sell, import, and distribute Compliant Implementations", requires the
notice "This product includes DNG technology under license by Adobe"
(<https://helpx.adobe.com/camera-raw/desktop/dng-and-file-formats/digital-negative.html>).

**Could not confirm:** Sony's official help-guide page stating the A7C II's RAW File Type options
(Uncompressed / Compressed / Lossless Compressed L·M·S). `helpguide.sony.net/ilc/2360/v1/en/` is JS-rendered; all
`contents/TP*.html` URLs and Wayback copies returned 404. The A7C II being **ARW2-family, not ARW6**, is inferred from
<https://github.com/abbradar/arw6_decode/blob/main/README.md> stating ARW6 is used by "(at least) ILCE-7RM6 and
ILCE-7M5" — **inference, not direct confirmation.** Verify against a real A7C II file before committing.

### F1.1c — The darktable `exif.cc` conflict: yes, that is a real hazard

**Confirmed hazard.** darktable is **GPL-3.0** (verified via GitHub API in §3). Reading `src/common/exif.cc` to learn
Sony maker-note lens-correction parsing, then writing that logic into an MIT/Apache Rust file, produces a derivative
work of GPL-3.0 code. The optics workstream's recommendation should be withdrawn.

**On ExifTool as the substitute — my expectation and the orchestrator's was partly wrong, and the nuance matters.**

**VERIFIED**: ExifTool's `LICENSE` file is **GPL-3.0**; `lib/Image/ExifTool.pm` states "free software; you can
redistribute it and/or modify it under the same terms as Perl itself" (= Artistic 1.0 **or** GPL-1.0-or-later).
Effective terms: **Artistic-1.0 OR GPL-3.0**. Critically, the tag tables at `exiftool.org/TagNames/Sony.html` are
**not an independent specification** — the index page states they are "generated automatically by
Image::ExifTool::BuildTagLookup" (<https://exiftool.sourceforge.net/TagNames/index.html>), i.e. they are a
*derivative artifact of the licensed Perl source*, and no separate documentation licence is offered.

That said, the practical risk is low and different in kind from reading `exif.cc`: **tag IDs, byte offsets, data
types, and enumerated values are facts about a file format, and facts are not copyrightable.** Implementing from the
tag *tables* is ordinary interoperability work. The line to hold is: **use the tables as a factual lookup; do not
copy prose descriptions, comments, or code structure; do not read the Perl.**

### Do-not-read / safe-to-read lists for AGENTS.md

**DO NOT READ THE SOURCE** (copyleft; contaminates an MIT/Apache rewrite):

- `darktable` — GPL-3.0. **Explicitly including `src/common/exif.cc`.**
- `RawTherapee`, `ART` — GPL-3.0 (demosaic: AMaZE / LMMSE / IGV).
- `Filmulator` — GPL-3.0.
- `ExifTool` Perl source (`lib/Image/ExifTool/Sony.pm` etc.) — GPL-3.0 / Artistic-1.0.
- `rawspeed` — LGPL-2.1 (verified). No separable format docs; `docs/` is build/test only.
- `LibRaw` — LGPL-2.1 / CDDL-1.0.
- `enfuse` / `enblend` — GPL-2.0-only. `Hugin` / `align_image_stack` — GPL-2.0+.
- EPFL `EDF-Extended-Depth-of-Field` — GPL-3.0. (Implement from the Forster 2004 *paper* instead.)
- `ChimpStackr` GPL-3.0; `ShineStacker` LGPL-3.0; `deptheos` GPL-3.0.
- `Jiangtherapee-sony-compressed-raw-hq-decoder` — AGPL-3.0.
- **Unlicensed repos** — `bznick98/Focus_Stacking`, `pulsar123/Macro-scripts`, `abbradar/arw6_decode`. No licence =
  all rights reserved. Not GPL, but *not* safe to copy. Prose READMEs are lower risk than code.

**Note the asymmetry:** `rawler` is on the *link-freely* list but the *do-not-read* list. Depending on an LGPL crate
is fine; copying its source into our MIT files is not.

**SAFE TO READ AND USE:**

- `GraphiteEditor/Graphite` / **`rawkit`** — Apache-2.0 / MIT OR Apache-2.0. ARW1, ARW2-lossy, uncompressed.
- `PetteriAimonen/focus-stack` — MIT. Best free algorithm description in the field (`docs/Algorithms.md`).
- `z-stackr` (all 7 crates) — MIT. `stackaroni` — MIT. `iwanders/focus_stacking` — MIT. `cmcguinness/focusstack` — Apache-2.0.
- `mindeng/nom-exif` — MIT, Rust TIFF/EXIF container parsing.
- `image`, `zune-image` — MIT/Apache.
- **Specifications:** TIFF 6.0 (public domain), ITU-T T.81, Adobe DNG spec (royalty-free grant + notice requirement).
- **ExifTool published tag tables** — as a *factual* tag-ID/offset/enum lookup only. Do not copy prose; do not read the Perl.
- **Academic papers**: Forster 2004; Burt & Adelson 1983; Burt & Kolczynski 1993; Mertens 2007; He/Sun/Tang guided filter;
  Kuglin & Hines 1975; Reddy & Chatterji 1996.
- **Vendor documentation** — Zerene FAQ/tutorials, Helicon parameter pages. Prose, freely readable, and unusually candid.

*Not legal advice; the LGPL-2.1 §6 reading above should be confirmed by counsel before a binary release.*

---

## F1.2 — Artifact taxonomy: the specification for the confidence map

Sources are overwhelmingly Zerene's own documentation and photomacrography.net. **Stated limitation:** Reddit JSON
endpoints and DPReview returned 403/CAPTCHA to automated clients throughout this session, so this taxonomy reflects
high-magnification specialists and the Zerene author's own vocabulary. Field-macro/naturalist failure modes are
likely under-represented.

**The central finding: no tool emits a confidence map. Nothing even close.** The nearest existing primitives are
Zerene's *binary* DMap contrast-threshold preview mask (an interactive control, not an output), Zerene's optional
depth-map export (encodes assigned depth, not reliability), and focus-stack's internal `contrastmap` debug image
(computed, used for depth-map halo suppression, **never surfaced to the user**). Confirmed absent in Zerene, Helicon,
Photoshop, Affinity, focus-stack, z-stackr, ChimpStackr, ShineStacker.

### Ranked taxonomy

Ranked by (frequency × how much retouching time it costs × how tractable detection is).

| # | Artifact | Cause | Algorithm family | Human fix today | **Detectable from stack data?** |
|---|---|---|---|---|---|
| **1** | **Inversion halo** — fuzzy halo around high-contrast edges; often *inverted* (dark halo on bright subject) | Pyramid/wavelet picks the OOF blur energy of a nearby strong edge over the true flat background | Pyramid, wavelet: PMax, HF A & C, focus-stack | Retouch from DMap; raise HF Radius | **Yes, strongly.** Output value falls outside `[min,max]` of all source frames at that pixel — an unambiguous, cheap invariant. Gate on proximity to a depth discontinuity. |
| **2** | **Loss-of-detail halo** — focused background adjacent to a foreground edge is simply *missing* | Depth map "does not slew quickly enough"; estimation kernel spans two depths and assigns an intermediate one | Depth-map: DMap, HF B (and PS) | Retouch from PMax; reduce Estimation Radius | **Yes.** Selected-frame index differs from the per-pixel focus-measure argmax, near a depth-map gradient. Detect as: winning frame ≠ locally-best frame. |
| **3** | **Transparent / ghost foreground** — opaque foreground shows background through it | "wide aperture lenses will 'look around' opaque parts of your subject to see sharp details in the background behind them" (Zerene tutorial) | Pyramid: PMax, HF A & C | "Stack Selected" the foreground-focused frames, then retouch in | **Yes, geometrically.** Occurs where foreground width < ~2× bokeh radius at that depth separation. Flag pixels assigned to foreground depth that also carry high focus-measure from background-focused frames — i.e. **two well-separated peaks in the focus-vs-frame curve.** |
| **4** | **Smooth-region blotching** — random patches from randomly-chosen frames | Focus measure driven by noise where there is no real detail; "making nearly random decisions based on pixel noise" | Depth-map only | Raise contrast threshold | **Yes, trivially.** Peak focus measure below the sensor noise floor → depth assignment is arbitrary. This is the single cheapest and most reliable confidence signal available. |
| **5** | **Never-in-focus region** — no frame ever saw this pixel cleanly | Pure optics: "the camera simply never sees the background leaf in the way that we'd like"; "There's no way around this problem using DMap or any other software" | **All — physics, not algorithm** | Nothing fully fixes it | **Yes** — same signal as #4 (max focus measure never rises above noise) but distinguished by *spatial context*: adjacent to a strong foreground edge rather than in an open flat field. **Most valuable output of all: it tells the user to reshoot, not to retouch.** |
| **6** | **Background contamination haze** — focused background near an edge loses contrast to OOF foreground light, "essentially the same as veiling glare" | Half the aperture is blocked by foreground | All — physics | Reshoot with foreground separated | **Partially.** Best achievable focus measure is depressed relative to same-depth regions away from edges. Needs a lens/aperture model — which is exactly what the optics workstream is building. Ratio of observed to expected contrast. |
| **7** | **Ghosts / echoes** — a feature appears twice, offset | Alignment error accumulated along the frame chain; or subject motion; "two frames, focused at nearly the same depth but far apart in stack order, end up aligned slightly differently" | All; **PMax worst** | Remove moving frames; raise Estimation Radius | **Yes.** Per-frame alignment residual is already computed during registration — just keep it. Plus local autocorrelation peaks at small offsets. |
| **8** | **Defect / worm trails** — dust and hot pixels smeared into linear trails by alignment | Defects are fixed in *sensor* coordinates while the subject is stabilised, so alignment drags them into tracks | All | Sensor cleaning; dust map; retouch | **Yes, exactly.** Fixed sensor-coordinate outliers across all frames, then trace through the known alignment transforms. Fully predictable — arguably should be *fixed automatically*, not merely flagged. |
| **9** | **Edge streaks / border banding** — smeared band at frame edges | Later frames don't cover the reference frame's full footprint; missing strips filled by nearest-pixel replication | All | Process from narrow-FOV end | **Yes, from geometry alone.** Confidence = number of frames actually covering that pixel, computed from alignment transforms without touching pixel data. Zero-cost. |
| **10** | **Colour / contrast / noise shift** | "unavoidable side effect of PMax"; HF Method C "increases contrast and glare" | Pyramid | Use DMap; pre-flatten contrast | **Yes**, as a global/regional statistic — output histogram vs. source median histogram. Low value as a *per-pixel* map. |
| **11** | **Stacking mush** — crossing bristles/hairs smeared together | Depth-map and weighted-average models assume a single opaque surface per pixel; overlapping thin structures violate it | HF A & B, DMap | Retouch from PMax | **Partially — the hardest case.** Signature is a genuinely multi-modal focus-vs-frame curve (multiple valid depths at one pixel). Detectable in principle; visually confirming it is "wrong" is hard even for a human. |
| **12** | **DMap swirls** from out-of-order frames or flash variation | Depth map assumes monotonic focus ordering | Depth-map only | Re-order; fix lighting | **Yes.** Non-monotonic per-frame scale/brightness sequence — a whole-stack precondition check, not a per-pixel map. Belongs in an input validator that runs *before* stacking. |

### What this means for the design

Nearly every detector above reduces to keeping information the stacker **already computes and currently throws away**:

1. **The focus-measure-vs-frame curve per pixel.** Its peak height vs. noise floor gives #4/#5. Its *modality* gives
   #3 and #11. Its sharpness gives general confidence. This one structure covers the majority of the taxonomy.
2. **Output-vs-source-range violation** (`out < min(src)` or `out > max(src)`) gives #1 essentially for free.
3. **Selected-frame vs. locally-best-frame disagreement** gives #2.
4. **Alignment residuals and frame-coverage counts**, retained rather than discarded, give #7, #8 and #9 with
   **no pixel processing at all.**

Two design consequences worth flagging to the orchestrator:

- **Separate "retouch this" from "reshoot this".** #5 and #6 are physically unrecoverable. Telling a user that a
  region can never be fixed in software — ideally *while they are still at the rig* — is arguably more valuable than
  the stack itself, and no tool does it.
- **#8, #9 and #12 are preconditions, not artifacts.** They should be caught by a validator before fusion starts,
  not reported afterwards.

---

## F1.3 — Performance budget: decomposition and the real risk

Target restated as a hard constraint: **60 frames × 33 MP, ARW → aligned → fused → 16-bit output, ≤ 15 s wall clock**
on a modern discrete GPU. That is ~132 MP/s end-to-end.

### Per-stage allocation

Assumes 60 × ~60 MB ARW = **~3.6 GB** of input, NVMe, 16-core CPU, modern GPU.

| Stage | Budget | Notes |
|---|---|---|
| File read | **1.0 s** | 3.6 GB at 3.5–7 GB/s NVMe. Must be overlapped with decode, not serialised. |
| ARW decode (LJPEG/Huffman) | **2.5 s** | Entropy decode is inherently serial *within* a frame but embarrassingly parallel *across* frames. ~0.2–0.3 s/frame ÷ 16 threads. **CPU-bound; this is the floor.** |
| Demosaic | **1.5 s** | 2.0 GP total. GPU demosaic runs at GP/s. **In a Bayer-domain design this drops toward zero — the single biggest architectural speedup available.** |
| Alignment | **5.0 s** | Multi-scale LK/ECC + warp. **The dominant cost and the dominant risk.** |
| Focus measure + fusion | **2.5 s** | §6.1 says the fusion kernel alone is ~1–2 s at Helicon's throughput. Budget includes focus-measure computation. |
| Confidence map | **1.0 s** | Mostly reuses focus-measure data already resident; incremental cost is small. |
| Output encode + write | **1.5 s** | One 33 MP 16-bit TIFF ≈ 200 MB. |
| **Total** | **15.0 s** | |

### Which stage actually dominates, and where the risk is

**Alignment, unambiguously — for a structural reason, not an arithmetic one.**

Every serious stacker aligns **neighbour-to-neighbour** rather than to a global reference, because extreme frames are
too blurred to register against the centre. focus-stack (MIT, safe to read) documents exactly this: *"In a deep stack
the extreme images are often very blurry and cannot be successfully aligned to the center of the stack. The default
approach is therefore to align each image against its neighbour and combine the alignment coefficients."*

**That is a serial dependency chain of length N.** Frame *k* cannot be registered until frame *k−1* is done. With 60
frames this is an Amdahl wall that no amount of GPU throughput removes. It is the most likely single cause of a
missed budget.

Mitigations to specify up front:
- **Two-phase alignment.** Register all frames against a global reference at low resolution *in parallel* (cheap,
  robust enough for a seed), then refine pairwise at full resolution — the refinement converges in few iterations
  from a good seed, shortening the serial chain's per-link cost.
- **Tree/parallel-prefix composition** of transforms instead of a linear scan.
- **Cap alignment resolution.** focus-stack defaults to ≤2048 px for alignment with `--full-resolution-align` as
  opt-in. Aligning at 33 MP is almost certainly wasted work.

### The memory risk is more dangerous than the time risk

The parallel workstream's observation — the prior project drifting **81 s → 456 s with RAM going 6 → 23 GB** — is
diagnostic, and the number is not a coincidence:

> 60 frames × 33 MP × 3 channels × 4 bytes (f32) = **23.8 GB**

That is the whole stack materialised as float32 RGB. **The 5.6× slowdown is almost certainly not compute — it is
allocation pressure, cache thrashing, and page traffic.** Time regressed *because* memory did.

Both mature tools converge on the same figure and the same answer. Zerene: "at least 100 megabytes of DRAM per each
1 megapixel." focus-stack: "approximately 100 MB of RAM is required per 1 megapixel of input image resolution. **The
images are processed in batches, so total number of images in stack does not significantly affect memory usage.**"

**Therefore state memory as a hard constraint alongside time, and make it independent of stack depth:**

- **Peak RSS ≤ 8 GB for 60 × 33 MP, and must not grow with frame count.** Enforce via tiling + streaming; never
  materialise the full stack. `focus-stack` uses `--batchsize=8`; `z-stackr` uses an out-of-core tile store. This is
  settled practice and should be architectural from commit one, not retrofitted.
- Add a CI regression test asserting both wall-clock and peak RSS on a fixed 60-frame fixture. **The prior project's
  failure was gradual drift under feature addition — that is precisely what a ratcheting CI budget prevents.**

### Is 15 s realistic, or too soft?

**15 s is realistic and correctly placed as a hard ceiling.** The floor is set by read + ARW decode (~3.5 s, CPU-bound
and largely irreducible). A well-built GPU pipeline should reach **8–10 s**, and that is the right internal stretch
goal. Do not tighten the *published* constraint below 15 s: the confidence map is new work no competitor performs,
and Bayer-domain fusion may cost more than a conventional path, not less. **Better to hold 15 s with the extra
quality features on than to hit 10 s and quietly regress to 456 s when they land.**

Framing for the orchestrator: **at 15 s we are ~6× faster than the prior project on the same workload while doing
strictly more work.** "Faster than Helicon's fusion kernel" remains the wrong goal — §6.1 shows that kernel is already
~1–2 s. The differentiator is the *whole pipeline* at that speed, with a confidence map, from RAW.
