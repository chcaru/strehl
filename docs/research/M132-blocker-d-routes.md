# M132 — real routes to scorecard blocker `(d)`

Research date: **2026-09-04**. Prices below are the prices displayed on that
date, before tax. `[VERIFIED]` means supported directly by a retained vendor
page, machine artifact, or cited scholarly record. `[ASSUMED]` marks an
inference that still needs a witness test or a fact about the intended use.
`[UNKNOWN]` is deliberately unresolved.

## 1. Verdict summary

| Question | Verdict |
| --- | --- |
| **Q1 — Can Helicon supply common-input intermediates?** | **YES IN HELICON 9 BETA; NOT YET A VERIFIED ROUTE UNDER THE SCORECARD AS WRITTEN.** `[VERIFIED]` Helicon Focus 9 Pro has **Export Layers → Aligned source images without transparency**, but the current download is explicitly **9.0.5 Beta**. Current stable 8.3.11 documents only semitransparent contribution layers and no master alignment-off switch. |
| **Q2 — Is a trial left?** | **Zerene: NO. Helicon: UNKNOWN, WITH STRONG LOCAL EVIDENCE FOR “PROBABLY YES.”** `[VERIFIED]` Zerene's installed trial expired 2026-06-06. No Helicon installation, license, log, registry value, prefetch file, or recent item was found; `[ASSUMED]` that means the automatic 30-day Helicon Pro trial is probably unconsumed, but only first installation can establish it. |
| **Q3 — May the benchmark be published?** | **BOTH EULAS ARE SILENT.** `[VERIFIED]` Neither EULA contains a benchmark, comparative-testing, or result-publication clause. Both prohibit reverse engineering. Zerene Prosumer also has use-scope restrictions. Silence is not express permission; obtain written confirmation before paying or publishing. |
| **Q4 — Is there a cheaper/equal replacement?** | **NO VERIFIED EQUAL-STANDING REPLACEMENT.** `[VERIFIED]` PICOLAY and Affinity are free but fail important protocol requirements; Photoshop is a plausible additional comparator but is not demonstrated equal in standing and would require a scorecard amendment. `[ASSUMED]` Zerene/Helicon naming is essential to this scorecard, not incidental. |

## 2. The recommendation

**If `(d)` must be cleared now under the scorecard as written, spend $189 USD
plus tax on Zerene Prosumer, after Zerene confirms in writing that publishing a
black-box comparative benchmark is acceptable, provided the work remains
personal, unfunded, and within the Prosumer use limits; otherwise spend $289 on
Professional.** That buys permanent access to the verified adjusted-input
export. Do **not** buy Helicon now as the guaranteed shortcut: its decisive
unmasked aligned-source export is presently in 9.0.5 **Beta**, while stable
8.3.11 has no verified alignment bypass. If the schedule permits waiting,
reserve the probably unused Helicon trial for a measurement-ready commissioning
run; after Helicon 9 becomes stable, the cheaper paid route should be Pro at the
then-current equivalent of today's **$55 one-year / $200 lifetime** price.

## 3. Q1 — Helicon common-input capability

### Verdict

**YES as a product capability in Helicon Focus 9 Beta; NO verified current
stable route.**

### The decisive version split

- `[VERIFIED]` Helicon's current download page lists **Helicon Focus 8.3.11** as
  the ordinary release and separately labels **Helicon Focus 9 Beta**, version
  **9.0.5**. The Windows history calls 8.3.11 “the latest version.” Sources:
  [Downloads](https://www.heliconsoft.com/software-downloads/) and
  [Windows history](https://www.heliconsoft.com/helicon-focus-history-of-changes-win/).
- `[VERIFIED]` [Scorecard §1.4](../proposals/2026-09-sota-scorecard.md#14-comparator-settings)
  requires “the newest generally available stable release” at freeze time.
  Therefore the beta cannot be silently substituted for stable 8.3.11 without
  amending the scorecard or waiting for general availability.
- `[VERIFIED]` Stable 8's guide describes **Export Layers** this way:

  > Saves aligned layers as semitransparent PNG/TIFF files. The transparency
  > is set in a way for the layers to produce the output image if opened in
  > Photoshop.
  >
  > PNG and TIFF options are completely different and produce different
  > results. TIFF is based on source map, while PNG is based on depth map.

  Source: [Helicon Focus 8 User Guide, Saving](https://www.heliconsoft.com/focus/help/english/HeliconFocus.html#HF_SAVE).
  Those are contribution/decomposition layers, not documented complete adjusted
  source planes. The feature is gated to **Pro** (and therefore Premium).
- `[VERIFIED]` Helicon 9's guide adds the exact missing option:

  > Exports aligned source images as layers for further work in external
  > editors.
  >
  > **Aligned source images without transparency** - exports all source images
  > after alignment, with no transparency applied.

  Source: [Helicon Focus 9 User Guide, Export Layers](https://www.heliconsoft.com/focus/help9/english/HeliconFocus.html#HF_EXPORT_LAYERS).
  `[ASSUMED]` This is the documented equivalent in kind to Zerene's
  adjusted-input export and is a credible route `(ii)` in the question: expose
  the comparator's aligned intermediate planes so its aligner can be factored
  out. The serialization witness below must still pass.
- `[VERIFIED]` The same Helicon 9 guide lists “Export of aligned layers as
  .png/.tiff files” under **Helicon Focus Pro**. Premium contains the same Focus
  Pro license plus broader Helicon Remote licensing; Premium adds nothing
  needed for `(d)`. Source:
  [Helicon Focus 9 User Guide, Licensing](https://www.heliconsoft.com/focus/help9/english/HeliconFocus.html#HF_ABOUT).

### Can alignment be disabled?

- `[VERIFIED]` No dedicated **Disable alignment**, **Do not align**, or
  equivalent master setting is documented in the complete stable-8 guide, the
  complete beta-9 guide, the edition matrix, or the vendor's site search.
- `[VERIFIED]` The exact documented controls are
  **Edit → Preferences → Autoadjustments → Adjust vertically, Adjust
  horizontally, Rotate, Scale, Adjust brightness, Crop result/output
  automatically**. Stable 8 also exposes command-line values `-va`, `-ha`,
  `-ra`, `-ma`, and `-ba`. Sources:
  [stable-8 Autoadjustments](https://www.heliconsoft.com/focus/help/english/HeliconFocus.html#HF_ADJ)
  and
  [beta-9 Autoadjustments](https://www.heliconsoft.com/focus/help9/english/HeliconFocus.html#HF_ADJ).
- `[ASSUMED]` Setting all four geometric maxima to zero and turning brightness
  and crop off may make stable 8 consume pre-aligned TIFFs without a geometric
  change. The documentation says these controls set *maximum* adjustments, but
  it does not state that zero bypasses the alignment/resampling pipeline or
  preserves input pixels exactly. This is a commissioning hypothesis, not a
  finding.
- `[VERIFIED]` Lite includes automatic alignment, 16-bit processing/output, and
  the command-line interface. Consequently, if the zero-limit hypothesis passes
  a pixel-identity witness, Lite could be the cheapest stable Helicon route.
  The vendor does not document that result, so it must not be budgeted as a
  cleared route yet. Source:
  [Helicon Focus 8 User Guide, Licensing](https://www.heliconsoft.com/focus/help/english/HeliconFocus.html#HF_ABOUT).

### Routes and actual prices

`[VERIFIED]` All Helicon prices in this table were checked **2026-09-04**, in
**USD**, from a checkout geolocated by the vendor's processor to
**United States / Washington**; VAT/tax is extra. The vendor says:

> One year license is valid during one year after purchase and reverts to demo
> mode afterwards.
>
> IT'S NOT A SUBSCRIPTION-BASED LICENSING MODEL, YOU WON'T BE CHARGED
> AUTOMATICALLY.
>
> Lifetime license is valid for lifetime, all updates are free.

Source: [Helicon Focus licenses](https://www.heliconsoft.com/helicon-focus-licenses-paypro/).

| Route | Current scorecard status | Minimum edition | Cost checked 2026-09-04 | What it really costs |
| --- | --- | --- | --- | --- |
| Stable 8.3.11 with all adjustment limits zero | **Unverified** | `[ASSUMED]` Lite if the controls and identity witness pass | **$0** to test in an unused trial; then **$30 one-year** or **$115 lifetime** | Consumes the one 30-day trial; needs a byte/pixel identity witness. Do not buy Lite first. |
| Helicon 9 “Aligned source images without transparency” | **Function verified, version inadmissible while Beta** | Pro; Premium also works | **$0** active trial; Pro **[$55 one-year](https://store.payproglobal.com/checkout?products%5B1%5D%5Bid%5D=12367)** or **[$200 lifetime](https://store.payproglobal.com/checkout?products%5B1%5D%5Bid%5D=12363)** | Wait for stable release or amend the stable-release rule. Buying a one-year license before GA burns paid term while waiting. |
| Helicon 9 Premium | Same Focus capability as Pro | Premium | **$65 one-year / $240 lifetime** | Extra spend buys multi-platform Helicon Remote, not a better `(d)` export. |
| Zerene adjusted inputs | **Verified current stable route** | Prosumer for eligible personal use; Professional otherwise | **$189 / $289 one-time** | Permanent license and current adjusted-input export; publication wording still needs confirmation. |

`[VERIFIED]` Helicon's product page says taxes are added at checkout. The Pro
checkout rendered **55.00 USD** and the lifetime checkout **200.00 USD** for
US-WA on the research date. `[VERIFIED]` Zerene's vendor page lists Prosumer
**$189 USD** and Professional **$289 USD**, says these are one-time costs with
no periodic charges, and adds location-dependent tax:
[Purchasing Zerene Stacker](https://zerenesystems.com/cms/stacker/docs/purchasing).

### What must still pass before Helicon clears `(d)`

- `[VERIFIED]` The public Helicon 9 guide does not specify the exported layer
  TIFF's sample depth, ICC treatment, transfer function, crop behavior, or
  whether brightness correction is baked into it.
- `[ASSUMED]` At a measurement-ready trial commissioning, use the unmasked TIFF
  export with brightness and automatic crop off, then verify: native dimensions,
  16-bit samples, the frozen linear profile, neutral-ramp affine limits, no
  hidden resize/tone operation, and exact correspondence between exported
  planes and the planes used by the Helicon render.
- `[VERIFIED]` Until that witness passes, the feature establishes a credible
  route and price, not a scored comparator arm.

## 4. Q2 — local trial and licence state

### Zerene: trial consumed and expired

- `[VERIFIED]` Zerene Stacker
  **1.04T2026-05-04-0750** is installed at
  `C:\Program Files\ZereneStacker\`. The vendor's current history identifies
  `T2026-05-04-0750` as the current full release:
  [Zerene modification history](https://zerenesystems.com/cms/stacker/docs/modificationhistory).
- `[VERIFIED]` The corroborating log is:
  `C:\Users\chris\AppData\Roaming\ZereneStacker\LastNormalLog.txt`.
  Its exact relevant lines are:

  ```text
  line 70: 0.431: trial.info=1.0,1778210014628,9b39f19827d162b7a3dc867110f8777a
  line 71: 0.448: license 83ced522295099724b84c81abbb79f3199726fd7 expires on Sat Jun 06 20:13:34 PDT 2026
  line 72: 0.449: now = Sat May 09 13:46:23 PDT 2026
  line 73: 0.449: relevant = true
  line 74: 0.449: Using default license key
  line 75: 0.450: License category = TRIAL
  ```

  The file path, hash, installation record, and line extraction are retained in
  [`zerene-machine-state.txt`](../../experiments/M132-blocker-d-routes/zerene-machine-state.txt).
- `[VERIFIED]` No `LicenseKey.txt` or other candidate Zerene state license file
  was found. On 2026-09-04, the recorded 2026-06-06 expiration is in the past.
- `[VERIFIED]` Zerene says that after its 30-day trial, “screen images are
  watermarked and saving images and projects is disabled.” Therefore the
  installed state cannot produce the required output:
  [Zerene FAQ, free trial](https://zerenesystems.com/cms/stacker/docs/faqlist#do_you_have_a_free_trial).
- `[VERIFIED]` Zerene says the adjusted-input export is an advanced Pro-only
  feature available permanently only in Prosumer/Professional:

  > Aligned and brightness-corrected input images can be saved to external
  > files.
  >
  > Adjustment parameters can be saved to an external file for plotting or
  > editing.

  Source:
  [Zerene FAQ, edition differences](https://zerenesystems.com/cms/stacker/docs/faqlist#what_are_the_differences_between_personal_prosumer_and_professional).
  The already consumed trial makes Personal's temporary feature access an
  unsafe/non-durable costing; the minimum Zerene purchase remains Prosumer.

### Helicon: no local trace, eligibility still not provable

- `[VERIFIED]` Read-only searches covered `C:\Program Files`,
  `C:\Program Files (x86)`, `%LOCALAPPDATA%`, `%APPDATA%`,
  `C:\Users\chris`, uninstall entries, `HKCU\Software`, `HKLM\Software`,
  standard Helicon Soft registry paths, `C:\ProgramData`, Windows Prefetch, and
  Recent Items. They found **zero Helicon-named installation, state, log,
  licence, key, or registry matches**. Evidence:
  [`machine-helicon-deep-search.txt`](../../experiments/M132-blocker-d-routes/machine-helicon-deep-search.txt),
  [`machine-helicon-registry-value-search.txt`](../../experiments/M132-blocker-d-routes/machine-helicon-registry-value-search.txt),
  and
  [`machine-helicon-additional-checks.json`](../../experiments/M132-blocker-d-routes/machine-helicon-additional-checks.json).
- `[VERIFIED]` Helicon says: “A fully featured 30-day trial period starts
  automatically upon the first installation of the program.” Source:
  [Helicon downloads](https://www.heliconsoft.com/software-downloads/).
- `[VERIFIED]` The Helicon 9 guide is more specific:

  > The trial lasts 30 days and provides full functionality (equivalent to the
  > Pro edition). After the trial ends, Helicon Focus switches to Demo mode.

  It continues that saved resolution is limited and a watermark is added:
  [Helicon Focus 9 User Guide, Registration](https://www.heliconsoft.com/focus/help9/english/HeliconFocus.html#HF_REGISTRATION).
  The edition page quantifies expired Demo mode as promotional text and a
  **4 MP** limit:
  [Choosing the right license](https://www.heliconsoft.com/helicon-focus-versions-licensing/).
- `[ASSUMED]` An active trial is therefore suitable in principle for
  commissioning, subject to the output witness in Q1.
- `[VERIFIED]` An expired Demo export is unusable measurement input because it
  is watermarked and resolution-limited.
- `[UNKNOWN]` Local absence cannot exclude a removed installation, a
  machine-fingerprint record held by Helicon, or trial use under another local
  state. The only decisive check starts the depletable clock. It was correctly
  not performed in this lane.

## 5. Q3 — licence permission to publish the comparison

This is a contract-text classification, not legal advice.

### Method

- `[VERIFIED]` Complete current vendor EULA pages were fetched with a browser
  user-agent and retained. The audit searched the extracted EULA bodies for
  benchmark, comparative testing, publication/disclosure, test/performance
  results, competitive development, and reverse-engineering terms. See
  [`audit_eulas.py`](../../experiments/M132-blocker-d-routes/audit_eulas.py)
  and
  [`eula-keyword-audit.txt`](../../experiments/M132-blocker-d-routes/eula-keyword-audit.txt).
- `[VERIFIED]` The installed Zerene EULA is not byte-identical to the current
  web page because the web page has a newer third-party component list, but
  clauses 1–7 used for this ruling match after whitespace normalization:
  [`zerene-installed-eula-check.txt`](../../experiments/M132-blocker-d-routes/zerene-installed-eula-check.txt).

### Zerene Stacker — **SILENT on benchmarking; edition scope is conditional**

- `[VERIFIED]` No benchmark, comparative-testing, benchmark-result publication,
  or competitive-product-development clause appears in the EULA:
  [Zerene licence terms](https://zerenesystems.com/cms/stacker/docs/licenseterms).
- `[VERIFIED]` Professional provides this output-use sentence:

  > There are no restrictions on the use of images produced by Professional
  > Edition licenses, unless such restrictions are listed as Special Terms
  > within the license key.

  `[ASSUMED]` This supports publication of produced images, but it does not
  expressly address publication of performance metrics or comparative
  conclusions.
- `[VERIFIED]` Prosumer's complete relevant use restriction says:

  > Prosumer Edition can be used for educational instruction and preparation
  > of instructional materials. However, Prosumer Edition cannot be used to
  > support any other corporate, organizational, or government activity,
  > including funded research and documentation of scientific collections, or
  > in connection with any other activity that produces income or other
  > tangible reward greater than the cost of a Professional Edition license.

- `[VERIFIED]` The reverse-engineering sentence says:

  > You are not allowed to modify, adapt, translate, reverse engineer,
  > decompile, disassemble or otherwise attempt to discover the source code or
  > algorithms of the Software.

- `[ASSUMED]` A black-box run over documented settings, measuring only outputs
  and timings, is not an attempt to discover source code or algorithms. Do not
  inspect binaries, hidden state, or implementation internals.
- `[ASSUMED]` Prosumer is the appropriate tier only while this remains the
  owner's personal, unfunded work and is not connected to restricted
  organizational activity or income above the stated threshold. If those facts
  differ, use Professional.
- **Verdict: SILENT.** The EULA neither forbids nor expressly permits published
  benchmark results. Obtain a written vendor answer that specifically covers
  publishing named comparative images, metrics, timings, settings, and
  conclusions for an open-source competing stacker.

### Helicon Focus — **SILENT**

- `[VERIFIED]` No benchmark, comparative-testing, publication-of-results, or
  competitive-development clause appears in the EULA:
  [Helicon Focus EULA](https://www.heliconsoft.com/end-user-license-agreement-helicon-focus/).
- `[VERIFIED]` The grant says:

  > Upon purchase of an Activation Code, the AUTHOR grants you a
  > non-exclusive, non-transferable (except as provided below) license to use
  > the SOFTWARE PRODUCT according to the terms of the EULA.

- `[VERIFIED]` The reverse-engineering sentence says:

  > You agree not to take steps such as altering, decompiling, reverse
  > assembling or reverse compiling to derive the source code or "look and
  > feel" equivalent(s) of the SOFTWARE PRODUCT.

- `[ASSUMED]` The proposed black-box comparison does not derive source or a
  look-and-feel equivalent, provided the lane does not inspect or manipulate
  program internals.
- **Verdict: SILENT.** There is no express publication permission and no
  benchmark ban. Obtain the same written confirmation before relying on
  Helicon output in a public SOTA claim.

## 6. Q4 — cheaper or better routes to the intent

### Direct answer

- `[VERIFIED]` Under [the scorecard's current text](../proposals/2026-09-sota-scorecard.md#14-comparator-settings),
  another stacker cannot itself clear `(d)`: the protocol defines the claim
  against named Zerene PMax/DMap and Helicon A/B/C modes. Replacing them is a
  scorecard amendment, not a licence workaround.
- `[VERIFIED]` No cheaper third-party candidate was verified to combine
  **equal field standing**, a clean common-input merge boundary, and the
  scorecard's native 16-bit linear-TIFF output contract.

### Field standing

- `[VERIFIED]` Brecko et al. compared CombineZP, Auto-Montage, Helicon Focus,
  and Zerene Stacker and concluded:

  > Zerene Stacker and Helicon Focus both provided satisfactory results.

  Source:
  [Brecko et al., 2014, DOI 10.3897/zookeys.464.8615](https://doi.org/10.3897/zookeys.464.8615);
  retained metadata/abstract from
  [Europe PMC](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI%3A10.3897%2Fzookeys.464.8615&format=json&pageSize=1&resultType=core).
- `[VERIFIED]` A 2020–2026 Europe PMC discovery query returned 1,261 records for
  “Helicon Focus”, 359 for “Zerene Stacker”, 97 for Photoshop plus focus
  stacking, 73 for CombineZP, 38 for Auto-Montage in image/microscopy context,
  and 17 for PICOLAY. These are search-hit counts, **not** a formal market-share
  or quality metric. Queries and URLs are retained in
  [`europe-pmc-stacker-counts.json`](../../experiments/M132-blocker-d-routes/europe-pmc-stacker-counts.json).
- `[ASSUMED]` The combination of the scorecard's named-comparator thesis,
  specialist feature/mode coverage, and much stronger scholarly trace makes
  Zerene and Helicon defensible reference implementations. Their naming is
  therefore essential for the present SOTA claim, though additional comparators
  could strengthen it.

### Candidate alternatives

| Candidate | Cost/capability evidence | Ruling |
| --- | --- | --- |
| **PICOLAY** | `[VERIFIED]` The current site offers “Free download” (version 2026-05-20): [PICOLAY](https://www.picolay.de/). Its manual makes alignment optional and says a two-pass alignment saves `xy...` aligned images. The same manual says TIFFs “will be changed to 24 bit bitmaps internally” and “PICOLAY cannot save tif files”: [English manual](https://www.picolay.de/picolay_helpfiles/Manual_PICOLAY_EN.pdf). | `[VERIFIED]` **Fails the registered 16-bit linear-TIFF contract.** `[ASSUMED]` Useful diagnostic, not an equal replacement. |
| **Affinity** | `[VERIFIED]` Canva says Affinity is “completely free” and “There are no hidden conditions”: [Canva announcement](https://www.canva.com/newsroom/news/affinity-free/). Official help says focus merging is previewed in “three stages: initial alignment, image blending, and final merging”: [Affinity help](https://affinity.help/photo2/en-US.lproj/pages/FocusMerging/focusmerging.html). | `[VERIFIED]` **No documented alignment bypass or intermediate-plane export was found.** `[ASSUMED]` It is therefore not a clean or equal-standing replacement. |
| **Adobe Photoshop** | `[VERIFIED]` Adobe documents separate operations: **Edit → Auto-Align Layers**, then **Edit → Auto-Blend Layers → Stack Images**: [Adobe focus stacking](https://www.adobe.com/creativecloud/photography/discover/focus-stacking.html). `[ASSUMED]` Pre-aligned layers could skip the separate Auto-Align operation. `[VERIFIED]` Creative Cloud and Lightroom are installed locally, but Photoshop is not; account entitlement is unknown. | `[ASSUMED]` **Best amendment candidate for merge-boundary cleanliness**, but output linearity/native 16-bit behavior and equal field standing are uncommissioned. `[VERIFIED]` It cannot clear the named-comparator blocker without amendment. |
| **CombineZP / Auto-Montage** | `[VERIFIED]` Both appear in the Brecko comparison, but contemporary Europe PMC discovery counts are far below Helicon/Zerene. | `[ASSUMED]` **Historical comparators, not a verified cheaper, current, equal-standing route.** |

### Scorecard-amendment options for the owner

- `[ASSUMED]` Allowing Helicon 9 Beta would create an immediate structural route
  through the unmasked aligned-source export, probably at $0 for the trial or
  $55 for a one-year Pro licence. It would also abandon the pre-registered
  stable-release rule and weaken reproducibility. That trade is governance, not
  a purchasing fact.
- `[ASSUMED]` Adding Photoshop as a secondary comparator could improve breadth
  if an existing subscription includes it, but it should supplement rather than
  replace Zerene/Helicon unless the scorecard's claim is deliberately narrowed.

## 7. What I could not determine

1. `[UNKNOWN]` Whether Helicon's server or machine fingerprint records an old
   trial despite the complete absence of local artifacts. Checking would start
   the trial and was intentionally not done.
2. `[UNKNOWN]` Whether stable Helicon 8.3.11 with vertical, horizontal,
   rotation, and scale maxima at zero truly bypasses all alignment and
   resampling, and whether every needed zero control is exposed under a Lite
   licence.
3. `[UNKNOWN]` Whether Helicon 9's unmasked aligned TIFFs are native-size
   16-bit linear ProPhoto files that pass the scorecard's tone sentinel and
   exactly represent the planes consumed by its merge. Vendor documentation
   does not specify those serialization details.
4. `[UNKNOWN]` Helicon 9's general-availability date and what its price will be
   on that date. Today's $55/$200 Pro prices must be rechecked before purchase.
5. `[UNKNOWN]` Whether either vendor will affirmatively authorize publication
   of the proposed named benchmark. Both EULAs are silent.
6. `[UNKNOWN]` Whether future funding, organization, business use, or
   monetization would put the work outside Zerene Prosumer's use scope.
7. `[UNKNOWN]` Whether the installed Adobe account includes a Photoshop
   entitlement; no Photoshop installation was found.
8. `[UNKNOWN]` Whether an unexamined niche stacker could qualify as an
   additional comparator. None found in the reviewed commercial, freeware, and
   scholarly candidates matched both the protocol and the standing requirement.

The retained raw pages, hashes, price context, derived text, and local read-only
artifacts are indexed in
[`snapshot-manifest.json`](../../experiments/M132-blocker-d-routes/snapshot-manifest.json).

## 6. What M7 actually costs

Follow-up research date: **2026-09-04**. Prices are the displayed US prices in
**USD** on that date. Tax and shipping are excluded unless stated. This section
adds `[DERIVED]` for arithmetic from cited dimensions and `[PROPOSED]` for a
decision rule that is not yet in the scorecard.

### Verdict summary

| Question | Verdict |
| --- | --- |
| **What target does M7 require?** | `[VERIFIED]` At least **24 surviving patches**, including every neutral and at least 12 chromatic patches, with published traceable values. `[DERIVED]` Those values must apply to the particular chart. `[UNKNOWN]` The scorecard specifies no reference-value uncertainty budget or conformity rule. |
| **Cheapest plausible target?** | **$660 Image Science Associates ColorGauge Nano, matte, with the listed NIST-traceable calibration certificate.** It has 30 patches and fits at 1.30x. It is only a candidate until ISA supplies a sample certificate with numerical uncertainty and the scorecard explicitly accepts this non-Calibrite target. |
| **Can M7 be shot at 1.30x?** | **YES.** `[DERIVED]` The Sony field is about 27.62 x 18.38 mm; the 20.64 x 17.46-mm ColorGauge Nano fits and leaves hundreds of pixels per eroded patch. Full-size ColorCheckers do not fit; the viable axis-aligned orientation of the 24 x 40-mm Calibrite Nano needs 62.64 degrees of tilt and 35.52 mm of depth travel. |
| **True known-price floor for 4/12?** | **$925 plus tax and shipping:** $189 Zerene + $660 calibrated Nano + $76 three-day C-800 rental. It is **$849** if a suitable illuminant meter is already available, or **$2,748** if the $1,899 C-800 is bought. None is yet guaranteed to clear M7. |
| **Buy now?** | **NO — spend $0.** First obtain the Nano certificate format and uncertainty at no charge, amend/confirm the scorecard target and grey-reference language, and retain the prior written-publication-permission gate. |

### 6.1 The actual target requirement

`[VERIFIED]` [M7](../proposals/2026-09-sota-scorecard.md#m7--colour-fidelity)
requires a tilted target under a measured illuminant, published traceable patch
values, a grey reference and darks. At least 24 valid patches must survive,
including **all neutral patches** and at least **12 chromatic patches**. Every
surviving patch is scored after 20% erosion. The tightest bars are median and
boundary-seam p99 `DeltaE00 <= 1.0`; p95 is `<=2.0`, maximum is `<=3.0`, and
ICC/300-DPI conformance is `100%`.

That wording implies more than buying a branded chart:

1. `[DERIVED]` The reference values must apply to the **particular physical
   target**, either by individual measurement or by a certified batch
   assignment whose uncertainty includes homogeneity and stability. A nominal
   recipe or unqualified batch average is insufficient because chart variation
   is otherwise inseparable from stacker error.
2. `[DERIVED]` The certificate must define the measurand: individual spectral
   reflectance or D50/2-degree CIELAB values, measurement geometry and specular
   condition, target identity, calibration chain, date, and uncertainty.
3. `[VERIFIED]` NIST adopts the VIM definition of traceability as the:

   > property of a measurement result whereby the result can be related to a
   > reference through a documented unbroken chain of calibrations, each
   > contributing to the measurement uncertainty.

   NIST immediately warns:

   > traceability alone does not signify or guarantee fitness for purpose,
   > because this typically requires that the uncertainty associated with a
   > measured value or calibration be sufficiently small to satisfy a
   > particular measurement need.

   Source:
   [NIST, *Metrological Traceability*](https://www.nist.gov/metrology/metrological-traceability);
   retained
   [HTML](../../experiments/M132-blocker-d-routes/m7-nist-metrological-traceability.html).

#### Reference tolerance — decisive ruling

**The scorecard currently has no numerical reference-tolerance requirement and
no uncertainty-aware pass/fail rule.** `[VERIFIED]` It gives the DeltaE00 bars
but never states a permitted target uncertainty, coverage probability, or
guard band. Therefore no unique target tolerance can be derived from the
registered protocol. A raw measured value of `1.0` cannot be declared a pass
when the reference has any non-zero unknown uncertainty.

`[PROPOSED]` Before purchasing, add this procurement and decision rule:

- require a serial-numbered certificate reporting per-patch expanded
  uncertainty, and enough information to propagate it through D50/2-degree
  CIEDE2000 and patch-to-patch seam differences;
- require target-only `U95 <= 0.25 DeltaE00` for every scored patch;
- combine target, illuminant, capture and computation uncertainty, then pass
  only when the **95% upper bound** remains at or below the registered bar.

The `0.25` is a conservative program budget that reserves at least 75% of the
tightest `1.0` limit for the system under test. It is **not** current scorecard
language, an ISA specification, or a claim that every aggregate statistic has
the same uncertainty. If the owner chooses another false-acceptance risk or
guard band, the number must change accordingly. What is non-negotiable is that
an unstated uncertainty, or uncertainty comparable to `1.0`, cannot support
this axis.

### 6.2 Current target prices and what each price buys

| Target | US price, 2026-09-04 | Patches / reference data | 1.30x ruling |
| --- | ---: | --- | --- |
| [Calibrite ColorChecker Classic](https://calibrite.com/us/product/colorchecker-classic/) | **$99** | 24; no per-chart measured dataset or numerical tolerance is stated on the rendered page or browser-UA raw HTML. | **No.** 203 x 292 mm. |
| [Calibrite ColorChecker Classic Nano](https://calibrite.com/us/product/colorchecker-classic-nano/) | **$189** | 24; no per-chart measured dataset or numerical tolerance is stated. | **Not practical.** 24 x 40 mm does not fit face-on and needs extreme tilt. |
| [Calibrite ColorChecker Digital SG](https://calibrite.com/us/product/colorchecker-digital-sg/) | **$369** | 140. Its generic certificate contains values from Munsell Labs and says the measuring instrument was NIST-traceably calibrated, but gives no chart serial/lot or numerical uncertainty. | **No.** 215.9 x 279.4 mm. |
| [ISA ColorBuild Micro, CC Classic](https://www.imagescienceassociates.com/colorbuild-micro-target.html) | **$605** | 24; vendor says the populated version includes “Individual NIST traceable spectral (380-730nm) and colorimetric target data.” | **No.** 38.1 x 47.625 mm; even its short side exceeds the field diagonal. |
| [ISA ColorGauge Pico](https://www.imagescienceassociates.com/colorgauge-pico-target.html) | **$352** | 30; only nominal batch values are offered on the page, with no calibrated-certificate option listed. | **Yes**, but not traceable enough for M7. |
| [ISA ColorGauge Nano](https://www.imagescienceassociates.com/colorgauge-nano-target.html), matte | **$330 nominal / $660 with “NIST Traceable Calibration Certificate”** | 30: 18 chromatic and 12 spectrally neutral patches. Calibration is a **$330** option. Numerical certificate uncertainty is not published. | **Yes. Best candidate.** 17.463 x 20.638 mm. |

The retained Calibrite pages are
[Classic](../../experiments/M132-blocker-d-routes/m7-calibrite-classic.html),
[Nano](../../experiments/M132-blocker-d-routes/m7-calibrite-nano.html), and
[Digital SG](../../experiments/M132-blocker-d-routes/m7-calibrite-digital-sg.html).
The Classic page says “24” and “203 x 292mm”; the Nano says “24” and
“24 x 40mm”; the Digital SG says “140” and “215.9 x 279.4mm.” Browser-UA raw
HTML and rendered-text captures agree on the prices and disclose no numerical
reference tolerance.

`[VERIFIED]` The available Digital SG
[Certificate of Analysis](https://www.bhphotovideo.com/lit_files/850220.pdf)
says:

> This certificate is provided based on data from Munsell Labs at X-Rite. The
> color sheets have been manufactured in accordance to the specifications for
> Munsell Color services. The instrument used to measure the color sheets
> mentioned above has been calibrated against NIST traceable standards.

It specifies D65, 2-degree observer, 400–700 nm, 10-nm data, d/8 geometry and
SCE, but no per-unit identity or uncertainty. `[VERIFIED]` This proves a
traceable **instrument** was used for the source data; under NIST's definition
it does not by itself establish a traceable, fit-for-purpose value for the
particular purchased chart. The certificate is retained as
[PDF](../../experiments/M132-blocker-d-routes/m7-calibrite-digital-sg-certificate.pdf)
and
[text](../../experiments/M132-blocker-d-routes/m7-calibrite-digital-sg-certificate.txt).

`[VERIFIED]` ISA's Nano page says:

> It has the identical 18 color patches as the GretagMacbeth ColorChecker, plus
> 12 spectrally neutral gray patches to assess correct exposure and white
> balance in close-up or macro photography applications.

It lists 1/8-inch patches, an overall 11/16 x 13/16-inch body, and the exact
**$660** matte certificate option. More importantly, ISA's linked
[Micro/Nano/Pico workbook](https://www.imagescienceassociates.com/mm5/pubs/Micro_Nano_Pico_Rez_TargetData.xls)
warns:

> All measurements are based on batch measurements of Munsell color papers as
> purchased from X-Rite Corp. There can always be inter-batch variations. The
> values listed below should be considered nominal for the batch provided to
> ISA by X-Rite Corp. For critical color calculations the user should perform
> their own optical measurments of the colorimetric values or contact us
> (info@imagescienceassociates.com) for individual target calibrations.

`[VERIFIED]` The same workbook's batch data contain component standard
deviations as high as **2.036799 in b-star**. That is not a per-target
CIEDE2000 uncertainty, but it is direct evidence that the free nominal values
cannot simply be treated as exact against a `1.0` bar. Reproduction:
[audit script](../../experiments/M132-blocker-d-routes/m7-evidence-audit.py)
and
[output](../../experiments/M132-blocker-d-routes/m7-evidence-audit.txt).

`[ASSUMED]` The $660 certificate option is ISA's individually calibrated route,
because it is the certificate-bearing product option and the workbook directs
critical users to “individual target calibrations.” The vendor does not publish
a sample Nano certificate, its measurement geometry, or its numerical
uncertainty. That assumption must be replaced by the actual certificate format
before purchase.

### 6.3 Physical use at 1.30x

`[VERIFIED]` Sony's official A7C II help guide specifies a **35.9 x 23.9-mm**
sensor and a 3:2 still-image size of **7008 x 4672 pixels**:
[camera specifications](https://helpguide.sony.net/ilc/2360/v1/en/contents/231h_specifications_ilc2360.html)
and
[image-size table](https://helpguide.sony.net/ilc/2360/v1/en/contents/0404M_jpeg_image_size.html).
The browser-UA captures are retained as
[specifications](../../experiments/M132-blocker-d-routes/m7-sony-a7c2-specifications.html)
and
[image size](../../experiments/M132-blocker-d-routes/m7-sony-a7c2-image-size.html).

At `1.30x`, `[DERIVED]`:

- object-space field = `35.9/1.30` by `23.9/1.30` =
  **27.615 x 18.385 mm**;
- ISA ColorGauge Nano = **20.638 x 17.463 mm**, so it fits face-on;
- each 3.175-mm patch projects to about **806 pixels** across. Even treating
  20% erosion as removal from every side leaves about **484 pixels** across;
- a 15-degree tilt across the target's short dimension projects it to
  **16.868 mm** high and creates **4.520 mm** of focus travel. It still fits
  and supplies a real tilted stack.

Therefore **M7 is physically shootable at 1.30x with the ISA ColorGauge
Nano**. This is not a marginal microscope speck: its patches remain hundreds of
pixels wide after erosion.

The cheaper Calibrite Nano is not a clean substitute. `[DERIVED]` In its best
axis-aligned orientation, the 24-mm side fits the 27.615-mm field, but the
40-mm side must be foreshortened into 18.385 mm. That requires at least
`acos(18.385/40) = 62.638 degrees` and creates **35.525 mm** of depth travel.
It is technically imageable only as an extreme, very deep stack, and it still
lacks per-chart traceable values. The full-size Classic and Digital SG are
orders of magnitude too large. The individually measured ColorBuild Micro is
also too large: its 38.1-mm short side exceeds the entire **33.175-mm field
diagonal**.

`[ASSUMED]` The Nano's 12 spectrally neutral patches satisfy M7's grey-reference
intent because ISA explicitly says they assess exposure and white balance.
If “grey card” is interpreted literally as a separate artifact, add the
[Calibrite Gray Balance](https://calibrite.com/us/product/colorchecker-gray-balance/)
at **$89**; it can be captured separately under the same lighting. Darks
require no purchase. The scorecard owner should resolve this wording before
ordering.

### 6.4 Illuminant measurement and all-in cost

`[VERIFIED]` “Measured illuminant” is a separate M7 input. Sekonic lists the
[C-800](https://sekonic.com/sekonic-c-800-u-spectrometer/) at **$1,899** and
says it measures light from **380 to 780 nm**. Lensrentals lists the
[same meter](https://www.lensrentals.com/rent/sekonic-c-800-spectromaster-color-meter)
at **$76 for three days** or **$109 for seven days**, before shipping and
optional damage coverage. Retained pages:
[Sekonic](../../experiments/M132-blocker-d-routes/m7-sekonic-c800.html) and
[Lensrentals](../../experiments/M132-blocker-d-routes/m7-lensrentals-c800.html).

The minimum cash stack is therefore:

| Item | Cost |
| --- | ---: |
| [Zerene Prosumer](https://zerenesystems.com/cms/stacker/docs/purchasing) | $189 |
| ISA ColorGauge Nano, matte, certificate option | $660 |
| Sekonic C-800, three-day rental without optional coverage | $76 |
| Built-in neutral reference and dark frames | $0 |
| **Known-price floor** | **$925** |

`[DERIVED]` If a suitable illuminant meter is already available, the floor is
**$849**. Buying rather than renting the C-800 makes it **$2,748**. A separately
purchased Calibrite grey card would add **$89**. Shipping, sales tax, rental
shipping and optional coverage remain unpriced.

**Crucially, $925 is not presently the price of a cleared M7. It is the minimum
listed-price bundle for an attempt.** The target's certificate uncertainty and
protocol admissibility are unresolved, so spending it now can still leave the
scorecard at 3/12.

### 6.5 Recommendation

**Spend $0 now.** Ask ISA for a sample of the exact certificate supplied with
the $660 matte ColorGauge Nano and require: serial-number linkage, per-patch
spectral or D50/2-degree values, measurement geometry/specular condition,
calibration chain, coverage factor, and numerical expanded uncertainty. In
parallel, make the scorecard explicitly admit the ColorGauge Nano and its
built-in neutral row, and retain the earlier written benchmark-publication
permission gate. Only if those no-cost gates pass should the owner spend
**$660 on the target, $189 on Zerene, and rent the C-800 when every capture and
comparator input is ready**.

### What I could not determine

1. `[UNKNOWN]` The numerical uncertainty, coverage factor, geometry, and exact
   contents of ISA's Nano calibration certificate. No sample certificate or
   tolerance is published on the browser-UA product page, linked workbook,
   comparison sheet, or technical brochure.
2. `[UNKNOWN]` Whether the $660 certificate is explicitly tied to the serial
   number of the delivered target and supplies D50/2-degree values or spectral
   data sufficient to derive them.
3. `[UNKNOWN]` The scorecard's intended uncertainty budget and conformity
   decision rule. The `U95 <= 0.25 DeltaE00` rule above is proposed, not
   registered.
4. `[UNKNOWN]` Whether the scorecard owner will accept the ColorGauge Nano as
   the required “ColorChecker” and its 12 neutral patches as the required grey
   reference.
5. `[UNKNOWN]` Exact shipping, tax, and rental-delivery charges; all totals are
   therefore explicit price floors, not checkout totals.
