# M157 - comparator viability (Zerene / Helicon / fork)

> **PROVENANCE.** Lane M157 ran as a `research` agent, whose environment cannot
> write files. The brief below is its verbatim deliverable, extracted from the
> lane transcript by the orchestrator and committed here so it is not lost with
> the session. Nothing has been added, removed, or reworded. Numbers and tags are
> the lane's own and carry the lane's evidence tags, not orchestrator
> verification.
# M157 — Comparator viability research brief

**Research cut-off:** 2026-09-04  
**Repository changes:** None. The requested file was not created because this research environment prohibits writing results to files; the complete brief is supplied inline.

## Evidence tags

- **VERIFIED** — directly established by primary vendor documentation, source code, or retained repository artifacts.
- **UNVERIFIED** — plausible or partially supported, but not proven to the program’s required contract.
- **NOT FOUND** — searched through multiple retrieval methods without finding the required documentation.
- **DISPUTED** — sources conflict, or implementation contradicts a published claim.

---

## Q0 — Zerene “Save Adjusted Input Images”

### Decision

**[UNVERIFIED — decisive]** A current Zerene Prosumer or Professional licence verifiably unlocks export of separate aligned and brightness-corrected source frames. It does **not yet prove the complete scorecard path**, because public documentation does not bind that command to native-size 16-bit **linear** TIFF output, does not specify its pixel/canvas/ICC contract, and does not document a batch or command-line invocation for the export itself.

The scorecard requires:

> “Each program must emit a native-size 16-bit linear TIFF.”  
> `C:\dev\blog\death-of-software\projects\strehl\docs\proposals\2026-09-sota-scorecard.md:250-253`

Accordingly, purchasing Zerene clears the licence gate but should not, by itself, mark the common-linear-input gate closed. A licensed witness run or written vendor confirmation is still needed.

### Q0(a) What the feature does

**[VERIFIED]** Zerene describes the feature as exporting adjusted **input images**, not the stacked composite:

> “Aligned and brightness-corrected input images can be saved to external files.”

Source: [Zerene Systems FAQ](https://zerenesystems.com/cms/stacker/docs/faqlist), section “What are the differences between Personal and Professional?”

The project representation independently identifies the saved adjustment state as per-input:

> “A project contains links to the input images, values of alignment and brightness adjustments for each input image…”

Source: [Zerene Systems — How To Use Zerene Stacker](https://zerenesystems.com/cms/stacker/docs/howtouseit), “Saving Work In A ‘Project’.”

**Assessment:** This is sufficient to establish that “Save Adjusted Input Images” produces the aligned/brightness-adjusted source frames rather than a PMax or DMap result.

**[VERIFIED]** The menu command historically appeared as:

> “Save Other > Save Adjusted Input Images added as new capability (Professional Edition only).”

Source: [Zerene Systems modification history](https://zerenesystems.com/cms/stacker/docs/modificationhistory), entry for build `T201106111240`.

The “Professional Edition only” wording is historical; current gating has changed, as documented below.

### Q0(a) Common-linear-output qualification

**[VERIFIED]** Zerene generally supports high-bit-depth TIFF input and output:

> “The input and output formats are JPEG and TIFF, the latter in either 8- or 16-bit RGB.”

Source: [Zerene Systems FAQ](https://zerenesystems.com/cms/stacker/docs/faqlist), “What kinds of image files will Zerene Stacker handle?”

It also generally documents ICC propagation:

> “By default, whatever color profile is used by the input files is also copied through to output files that are saved as JPEG or TIFF.”

Source: [Zerene Systems FAQ](https://zerenesystems.com/cms/stacker/docs/faqlist), “How does Zerene Stacker handle color profiles?”

**[NOT FOUND]** Neither statement is explicitly attached to **Save Adjusted Input Images**. Across the FAQ, how-to page, modification history, Batch API, browser-UA raw HTML, and the vendor’s full-text search, I found no official specification for that command’s:

- exact output format choices;
- 8-bit versus 16-bit behavior;
- transfer function or sample-value identity;
- ICC preservation;
- crop/canvas geometry;
- interpolation;
- whether brightness correction can be disabled;
- ramp fidelity.

The general TIFF/ICC statements therefore cannot be promoted to a command-specific guarantee.

**[UNVERIFIED]** The export is semantically suitable as a source-frame export, but its qualification as the program’s required common **linear** TIFF boundary remains unproved. It must pass the scorecard’s ramp and identity witnesses before use.

### Q0(b) Editions containing the feature

**[VERIFIED]** The current vendor page explicitly places the feature in both **Prosumer and Professional**:

> “Here is a full list of the features that require Prosumer Edition or Professional Edition.”

The list includes:

> “Aligned and brightness-corrected input images can be saved to external files.”

Source: [Zerene Systems FAQ](https://zerenesystems.com/cms/stacker/docs/faqlist), “What are the differences between Personal and Professional?”

**[VERIFIED]** Personal does not permanently unlock it; Personal users only receive a separate advanced-feature trial:

> “Menu items are labeled (Pro) if you need a Professional Edition or Prosumer Edition license to use them beyond a 30-day trial.”

Source: [Zerene Systems FAQ](https://zerenesystems.com/cms/stacker/docs/faqlist).

**[DISPUTED — resolved in favor of current documentation]** The 2011 changelog calls the feature Professional-only, while the current FAQ says Prosumer **or** Professional. The current edition comparison supersedes the historical launch restriction.

**[VERIFIED]** Technical availability does not determine whether Prosumer is legally appropriate. Zerene restricts Prosumer use:

> “Use must be strictly for your own or your immediate family’s nonprofessional purposes.”

Professional permits broader use:

> “Use may support any purpose including commercial, corporate, organizational, government, educational, or funded research activities.”

Source: [Zerene Systems licence terms](https://zerenesystems.com/cms/stacker/docs/licenseterms).

Therefore, **Prosumer is technically sufficient**, but Professional may still be contractually required depending on who operates the benchmark and for what purpose.

### Q0(c) Current prices

**[VERIFIED]**

> “Professional Edition, $289 USD”  
> “Prosumer Edition, $189 USD”  
> “Personal Edition, $89 USD”

Source: [Zerene Systems purchasing page](https://zerenesystems.com/cms/stacker/docs/purchasing).

**[VERIFIED]** The current generally available production build is:

> “The current production version of Zerene Stacker is T2026-05-04-0750 (May 4, 2026).”

Source: [Zerene Systems downloads](https://zerenesystems.com/cms/stacker/softwaredownloads).

### Q0(d) Perpetuity and upgrade rights

**[VERIFIED]** Purchased non-Student licences are perpetual:

> “These prices are a one-time cost. There are no periodic charges.”

> “All licenses except Student Edition never expire.”

Source: [Zerene Systems purchasing page](https://zerenesystems.com/cms/stacker/docs/purchasing).

**[VERIFIED]** Edition upgrades cost only the edition-price difference:

> “Pricing for an upgrade is just the difference in purchase prices.”

Source: [Zerene Systems purchasing page](https://zerenesystems.com/cms/stacker/docs/purchasing).

**[VERIFIED, current policy rather than irrevocable future guarantee]** Product updates are currently free:

> “Yes, updates are free. We’ve been issuing free updates ever since Zerene Stacker was first sold, back in 2009. We have no plans to change that policy.”

Source: [Zerene Systems FAQ](https://zerenesystems.com/cms/stacker/docs/faqlist), “Are program updates free?”

The wording describes current policy and intent; it is not an unconditional contractual promise for every future major version.

### Q0(e) Batch, scripting, CLI, and the adjusted-image export

**[VERIFIED]** Zerene has an official unattended automation interface:

> “Zerene Stacker can be launched, controlled, and terminated from another program, with no interaction needed between Zerene Stacker and a human user.”

> “Batch scripts are XML files that tell Zerene Stacker what to do.”

Source: [Zerene Systems Batch API](https://zerenesystems.com/cms/stacker/docs/batchapi).

The documented workflow is to write an XML batch script, invoke Zerene through its bundled Java runtime, and wait for termination. Relevant switches include:

- `-batchScript`
- `-exitOnBatchScriptCompletion`
- `-runMinimized`
- `-noSplashScreen`

The same page states:

> “For reference, here are all of the currently defined command line options.”

Source: [Zerene Systems Batch API](https://zerenesystems.com/cms/stacker/docs/batchapi), “Command Line Options.”

**[VERIFIED]** PMax and DMap can be run unattended:

> “A new project will be constructed for each folder of source images, PMax and DMap will be run within each project, the projects will be saved in a designated location, and output images will be both retained within the projects and written to external files.”

Source: [Zerene Systems — How To Use Zerene Stacker](https://zerenesystems.com/cms/stacker/docs/howtouseit), “Batch Processing.”

The published XML example uses:

> `<TaskIndicatorCode value="1" />       Align and Stack All (PMax)`

Source: [Zerene Systems Batch API](https://zerenesystems.com/cms/stacker/docs/batchapi).

**[UNVERIFIED — edition boundary]** The vendor’s explicitly “full list” of features requiring Prosumer/Professional does not include the general batch facility. That strongly supports batch being available in Personal as well, but I found no direct sentence saying “batch is available in Personal.” The precise safe wording is: **general batch is not documented as edition-gated**.

**[NOT FOUND]** No public Batch API task, command-line switch, XML example, or vendor instruction was found for **Save Adjusted Input Images** itself.

This absence was checked through:

1. parsed Batch API documentation;
2. browser-UA raw HTML scans for `Save Adjusted`, `Adjusted Input`, and `Save Other`;
3. vendor full-text search for the exact feature name, which returned modification-history references but no automation documentation;
4. vendor full-text search for `zsnocons`, which returned no substantive documentation.

The vendor’s exhaustive command-line list contains no adjusted-input export switch. This does **not** prove the operation is impossible through generated XML; it establishes that the route is undocumented publicly.

**[NOT FOUND]** The locally observed `zsnocons.exe` has no official public documentation that I could locate. The vendor instead documents launching the JRE directly:

> “Zerene Stacker is a Java application, so launching Zerene Stacker really amounts to launching a copy of the Java Runtime Environment (JRE)…”

Source: [Zerene Systems Batch API](https://zerenesystems.com/cms/stacker/docs/batchapi).

**[UNVERIFIED]** A possible no-realignment batch path exists but is not fully specified. Vendor history says:

> “Avoid unnecessary re-alignment on Stack Selected when Brightness correction is not selected.”

and separately:

> “In batch dialog, correctly report task as ‘Stack Selected (DMap)’ instead of ‘Align Selected (DMap)’.”

Source: [Zerene Systems modification history](https://zerenesystems.com/cms/stacker/docs/modificationhistory).

This proves that `Stack Selected` and at least its DMap form have existed in the batch dialog and can avoid unnecessary realignment. It does not document the XML task code or a repeatable “all pre-aligned frames, no realignment” benchmark recipe. That exact recipe must be confirmed before claiming `alignment_bypassed=true`.

---

## Q1 — Current stable Helicon Focus and aligned-source export

### Verdict: **NO**

**[VERIFIED]** The current stable release is **Helicon Focus 8.3.11**, released **16 February 2026**:

> “What is new in the latest version”

> “Helicon Focus (Lite, Pro, Premium) 8.3.11 (16.02.2026)”

Source: [Helicon Focus Windows history API](https://www.heliconsoft.com/wp-json/wp/v2/pages?slug=helicon-focus-history-of-changes-win).

The current downloads API separately labels the two channels:

> “Helicon Focus 8”

> “Version 8.3.11”

and:

> “Helicon Focus 9 Beta”

> “Version 9.0.5”

Source: [Helicon software-downloads API](https://www.heliconsoft.com/wp-json/wp/v2/pages?slug=software-downloads).

**[VERIFIED]** Stable v8 documents only masked/semitransparent layer output:

> “Saves aligned layers as semitransparent PNG/TIFF files.”

Source: [Helicon Focus 8 manual, Save tab](https://www.heliconsoft.com/focus/help/english/HeliconFocus.html#HF_SAVE).

That is not equivalent to the required unmasked aligned source frames.

**[VERIFIED]** The required option is documented in the v9 manual:

> “Aligned source images without transparency - exports all source images after alignment, with no transparency applied.”

Source: [Helicon Focus 9 manual, Export Layers](https://www.heliconsoft.com/focus/help9/english/HeliconFocus.html#HF_EXPORT_LAYERS).

**[NOT FOUND]** The exact phrase and any equivalent unmasked-source option were absent from the stable v8 manual in both parsed retrieval and browser-UA raw HTML. The positive v8 documentation instead specifies semitransparent aligned layers.

**Conclusion:** As of 2026-09-04, the required capability remains in **9.0.5 Beta**, not in the current generally available stable **8.3.11**.

---

## Q2 — Helicon pricing and licence model

**[VERIFIED]** Current prices are:

| Edition | One year | Lifetime |
|---|---:|---:|
| Lite | $30 | $115 |
| Pro | $55 | $200 |
| Premium | $65 | $240 |

Source: [Helicon Focus licence purchasing](https://www.heliconsoft.com/helicon-focus-licenses-paypro/).

The repository’s `$55 one-year / $200 lifetime` statement is therefore correct for **Pro**.

**[VERIFIED]** The required layer export is a Pro function:

> “Note: Export of layers is available in Helicon Focus Pro version only.”

Source: [Helicon Focus manual](https://www.heliconsoft.com/focus/help/english/HeliconFocus.html#HF_SAVE).

Premium includes Focus Pro functionality alongside the broader Premium package, so the feature is available in **Pro and Premium**, not Lite.

**[VERIFIED]** The one-year SKU is genuinely time-limited but is not an auto-renewing subscription:

> “After the license expires, the program reverts to demo mode.”

> “The license is not renewed automatically.”

Source: [Helicon Focus licence purchasing](https://www.heliconsoft.com/helicon-focus-licenses-paypro/).

**[VERIFIED]** Lifetime licences are permanent and include updates:

> “Lifetime license is permanent and includes all future updates free of charge.”

Source: [Helicon Focus licence purchasing](https://www.heliconsoft.com/helicon-focus-licenses-paypro/).

---

## Q3 — Zerene prices and licence duration

**[VERIFIED]**

- Personal: **$89**
- Prosumer: **$189**
- Professional: **$289**

> “These prices are a one-time cost. There are no periodic charges.”

> “All licenses except Student Edition never expire.”

Source: [Zerene Systems purchasing](https://zerenesystems.com/cms/stacker/docs/purchasing).

**Answer:** Zerene Professional is **$289** and perpetual: **YES**. Updates are currently free, and upgrading editions costs the price difference.

This corroborates the user’s reading of the installed licence text: the trial is time-limited; purchased non-Student licences are not.

---

## Q4 — Zerene batch/scripted/command-line operation

**[VERIFIED]** Zerene supports repeatable unattended XML batch processing and command-line launch through its Java entry point.

> “Write a ‘batch script’ that tells Zerene Stacker where to get its input files, how to stack them, and where to save its output images.”

> “Launch Zerene Stacker as a command-line application, passing arguments that specify the batch script and various other controls.”

Source: [Zerene Systems Batch API](https://zerenesystems.com/cms/stacker/docs/batchapi).

**[VERIFIED]** PMax and DMap can both be placed in an unattended batch, including output saving. This is sufficient for repeatable timing of normal automatic stacks.

**[UNVERIFIED]** General batch processing is not named in the vendor’s complete Prosumer/Professional-only feature list, so it appears available in Personal, Prosumer, and Professional. The vendor does not provide an explicit per-edition batch row.

**[NOT FOUND]** Public documentation does not expose:

- a batch task for `Save Adjusted Input Images`;
- a dedicated command-line switch for that export;
- official behavior or invocation of `zsnocons.exe`;
- a complete pre-aligned “stack without any realignment” XML recipe.

Therefore the correct answer is:

> **General Zerene PMax/DMap batch scripting: YES, not documented as edition-gated.  
> Automated Save Adjusted Input Images: NOT FOUND/documented.**

---

## Q5 — Other possible foreign-arm comparators

The owner’s plan controls the decision:

> “An open-source stacker is a useful foreign arm and repairs a real provenance defect, but it clears no blocker.”

`C:\dev\blog\death-of-software\projects\strehl\docs\proposals\2026-08-sota-path.md:2307-2309`

None of the following substitutes for licensed Zerene under that plan.

### Enfuse / Hugin — best additional comparator

**[VERIFIED]** Enfuse is command-line native:

> “Enfuse is a command-line program…”

It directly accepts input files:

> `enfuse <options> <input files>`

and explicitly supports focus stacks:

> “Enfuse can also be used to build extended DOF images, by blending a focus stack.”

Source: [Hugin Enfuse manual](https://hugin.sourceforge.io/docs/manual/Enfuse.html).

**[VERIFIED]** Alignment is a separate executable. `align_image_stack` performs a six-step detect/optimize/remap workflow, while Enfuse consumes supplied images directly:

> “align_image_stack is a command-line tool to align overlapping images…”

> “Remap all images and output result files.”

Source: [Hugin `align_image_stack` manual](https://hugin.sourceforge.io/docs/manual/Align_image_stack.html).

Therefore invoking Enfuse directly on pre-aligned TIFFs bypasses Hugin alignment.

**[VERIFIED]** Source supports uint16 RGB/grayscale paths, an identity blend colour space, and ICC-profile propagation: `jackmitch/enblend-enfuse:src/enfuse.cc:1628-1650,2069-2177,2317-2378,2548-2580`.

**[UNVERIFIED]** It remains subject to the scorecard’s actual ramp/identity witness. It is nevertheless the strongest additional arm because it is headless, alignment-separable, TIFF-capable, and exposes its colour-processing behavior.

### CombineZP

**[VERIFIED]** Source parses positional path, macro, and save arguments and calls `silent_open`, `silent_macro`, and `silent_save_out`: `Vincentdecursay/CombineZP:combineZP/combine/combine.cpp:67-134,215-280`.

**[VERIFIED]** Its default macros separate:

> `// Align and Balance`

from:

> `// Do Stack`

and other stack-only macros: `Vincentdecursay/CombineZP:combineZP/combine/macro.cpp:374-430,500-565`.

Thus a macro can omit alignment.

**[VERIFIED — disqualifying limitation]** Its image storage/export path uses `PixelFormat32bppRGB`/`PixelFormat24bppRGB`, meaning 8-bit RGB channels rather than the required native 16-bit linear output: `Vincentdecursay/CombineZP:combineZP/combine/Files.cpp:2963-3021`.

### PICOLAY

**[VERIFIED]** PICOLAY can save separately aligned frames:

> “2x will first generate aligned images…”

> “The aligned images will be saved with new names (xy...).”

Source: [PICOLAY English manual](https://www.picolay.de/picolay_helpfiles/Manual_PICOLAY_EN.pdf), alignment/batch section.

**[VERIFIED — disqualifying limitation]**

> “TIF images … will be changed to 24 bit bitmaps internally. PICOLAY cannot save tif files.”

Source: same manual.

**[NOT FOUND]** No documented headless command-line interface was found after checking the manual, website, and raw page content. It has GUI batch-like facilities but is not a credible automated 16-bit linear arm.

### ImageJ/Fiji Extended Depth of Field

**[VERIFIED]** The EDF plugin is macro-callable:

> “The plugin is callable from an ImageJ macro, in ‘easy’ mode.”

Source: [EPFL Extended Depth of Field](https://bigwww.epfl.ch/demo/edf/index.html).

Fiji can run macros headlessly:

> “ImageJ2 provides the capability to execute ImageJ plugins, macros and scripts in headless mode.”

Source: [ImageJ headless documentation](https://imagej.net/learn/headless).

**[VERIFIED]** Registration is external rather than inherent:

> “The images have been realigned first using: StackReg…”

Source: [EPFL EDF examples](https://bigwww.epfl.ch/demo/edf/index.html).

Thus pre-aligned input is structurally acceptable.

**[VERIFIED — limitation]** The RGB output route constructs an ImageJ `ColorProcessor`, i.e. the conventional 8-bit/channel color path: `Biomedical-Imaging-Group/EDF-Extended-Depth-of-Field:src/edfgui/ExtendedDepthOfField.java:203-215` and `src/edf/PostProcessing.java:83-96`. Higher-depth grayscale processing exists, but a qualifying 16-bit RGB linear route is not established.

### Photoshop

**[VERIFIED]** Adobe exposes alignment and blending as separate operations:

> “Choose Edit > Auto-Align Layers.”

> “Choose Edit > Auto-Blend Layers. In the dialog, select Stack Images…”

Source: [Adobe focus stacking guide](https://www.adobe.com/creativecloud/photography/discover/focus-stacking.html).

Therefore pre-aligned layers can conceptually omit Auto-Align.

**[VERIFIED]** Photoshop commands can be scripted:

> “batchPlay … executes one or more Photoshop action commands…”

Source: [Adobe UXP `batchPlay`](https://developer.adobe.com/photoshop/uxp/ps_reference/media/batchplay/).

**[NOT FOUND]** I did not establish a supported, fully unattended command-line Auto-Blend route or a documented linear-output/ramp contract. Photoshop is automatable, but not yet a reproducible headless comparator.

### Affinity Photo

**[VERIFIED]** Affinity supports focus merging:

> “Multiple images of the same subject that have different focus distances can be merged together…”

Source: [Affinity Photo focus merging](https://affinity.help/photo2/en-US.lproj/pages/FocusMerging/focusmerging.html).

**[VERIFIED]** Its batch facility applies macros independently:

> “Any number of pre-recorded macros can be applied to the source files…”

> “Applied Macros—lists macros that will be applied to each source image in the batch job.”

Source: [Affinity Photo batch jobs](https://affinity.help/photo2/en-US.lproj/pages/Macros_Batch/batchjobs.html).

**[NOT FOUND]** No documented multi-file Focus Merge batch operation, alignment bypass, or headless CLI was found. Per-file macro batching is not equivalent to one multi-frame focus-stack job.

### darktable and RawTherapee

**[VERIFIED]** Both are scriptable image processors/exporters:

> “The `darktable-cli` binary … allows images to be exported.”

Source: [darktable CLI manual](https://docs.darktable.org/usermanual/development/en/special-topics/program-invocation/darktable-cli/).

> “Use this application to start the command line only version.”

> “Convert files in batch…”

Source: [RawTherapee command-line options](https://rawpedia.rawtherapee.com/Command-Line_Options).

**[NOT FOUND]** Searches of their official manuals and source documentation found no focus-fusion/stacking engine. They are useful common-input preprocessors, not focus-stacking comparators.

### ShineStacker

**[VERIFIED]** ShineStacker supports scripted jobs and high-bit-depth TIFF:

> “Image Formats: JPEG, 8 and 16 bits TIFF and PNG … output can be JPEG, 8 and 16 bits TIFF and PNG.”

> “Python API — batch processing”

Source: `lucalista/shinestacker:docs/main.md:11-29,64-83`.

**[VERIFIED]** Alignment and stacking are separate job actions:

```python
job.add_action(CombinedActions("align", [AlignFrames()]))
job.add_action(FocusStack("result", PyramidStack()))
```

Source: `lucalista/shinestacker:docs/main.md:21-29`.

Omitting the alignment action provides a plausible pre-aligned path.

**[UNVERIFIED]** Its documentation does not define transfer-function or ICC identity for 16-bit TIFF. It is a credible secondary candidate, but not yet a qualifying linear arm.

### ChimpStackr

**[VERIFIED]** It has a headless CLI and alignment is opt-in:

> `help="Align images before stacking (default: stack only)"`

Source: `noah-peeters/ChimpStackr:src/cli.py:31-52`.

**[DISPUTED — disqualifying precision behavior]** The loader reduces uint16 samples to a `0–255` float scale:

> `img = img.astype(np.float32) * (255.0 / 65535.0)`

Source: `noah-peeters/ChimpStackr:src/ImageLoadingHandler.py:143-190`.

Its “16-bit” writer then expands that range:

> `result = np.clip(algo.output_image, 0, 255) * 257.0`

Source: `noah-peeters/ChimpStackr:src/cli.py:185-225`.

Thus its 16-bit file output does not preserve genuine sub-8-bit input precision, contradicting any broad full-bit-depth claim.

### Stackaroni

**[VERIFIED]** It ships a headless runner:

> “the `stackaroni-cli` headless runner”

and accepts:

> “16-bit TIFF, already developed and denoised from RAW…”

> “Samples are converted to linear light on decode and re-encoded to sRGB on write.”

Source: `nschroeter/stackaroni:README.md:24-52,77-102`.

**[NOT FOUND]** Its documented pipeline is fixed as:

> `registration → focus measurement → weight estimation → fusion`

No documented switch bypasses registration. It therefore does not presently satisfy the program’s alignment-bypass condition.

### z-stackr

**[VERIFIED]** It exposes CLI/Python APIs, 16-bit support, and alignment mode `none`:

> “`none` skips refinement entirely.”

Source: `suitable-name/z-stackr:README.md:17-30,38-43`.

**[DISPUTED — linearity]** The README introduction claims “physically accurate, linear-light blending,” but its detailed pipeline states:

> “The pipeline deliberately stores and blends gamma-encoded (sRGB) values end to end…”

Source: `suitable-name/z-stackr:README.md:17-30`.

The detailed implementation description contradicts the headline claim; it is not a demonstrated linear comparator.

### Q5 conclusion

**Best additional arm: Enfuse.** It is command-line native, accepts supplied TIFFs directly, keeps alignment in a separate tool, supports uint16 paths, and exposes identity-space/ICC handling. It still requires the scorecard’s ramp witness and does not replace Zerene under the authoritative plan.

---

## Q6 — What “the fork” is and where 13.93 s/frame came from

### Identity and upstream

**[VERIFIED]** “The fork” is the owner’s heavily modified `chcaru/macro` repository, derived from Petteri Aimonen’s `focus-stack`.

The repository status records:

> “The repo at `C:\dev\macro` has one remote: `https://github.com/chcaru/macro.git`.”

> “It has 92 commits total. The first commit, `4bc7f95`…”

`C:\dev\blog\death-of-software\projects\strehl\docs\STATUS.md:2821-2828`

The prior-corpus audit independently labels it:

> “Patched `PetteriAimonen/focus-stack` fork (`C:\dev\macro`)”

`C:\dev\blog\death-of-software\projects\strehl\docs\research\A-prior-corpus.md:1-8`

The owner’s modifications include registration, RAW/development, colour, HDR, denoise, and output work; it is not a pristine upstream binary:

`C:\dev\blog\death-of-software\projects\strehl\docs\STATUS.md:2830-2867`

### The build that produced 13.93 s/frame

**[VERIFIED]** The timing harness invoked:

> `$fork = 'C:\dev\macro\focus-stack\build-msvc\focus-stack.exe'`

`C:\dev\blog\death-of-software\projects\strehl\experiments\V-HEADTOHEAD2\timing2.ps1:75`

Read-only hashing and metadata inspection found:

- path: `C:\dev\macro\focus-stack\build-msvc\focus-stack.exe`;
- size: `858624` bytes;
- timestamp: `2026-05-17 03:01:25.1680714 -07:00`;
- SHA-256: `0ABA0CF0936AF8B1CACE2681CA43D49729D253E8ED1F786F2A8960B7974CA45D`.

The surviving `dist\focus-stack.exe` is byte-identical and carries the same timestamp and hash. The retained provenance file records that hash and timestamp:

`C:\dev\blog\death-of-software\projects\strehl\experiments\M8-COMPARATIVE\focus-stack-executable-provenance.json:12-20`

**[VERIFIED]** The two observed run times were:

> “Standalone probe: 1604.15 s”

> “Scripted rep 1: 1320.64 s”

and the derivation was:

> “median = (1604.15 + 1320.64) / 2 = 1462.395 s”

> “1462.395 / 105 = 13.9275714286 s/frame”

`C:\dev\blog\death-of-software\projects\strehl\experiments\V-HEADTOHEAD2\logs\timing-derive.txt:1-18`

Only the 1320.64-second second run appears in `timing2.csv`; the first was a standalone probe documented by the harness:

`C:\dev\blog\death-of-software\projects\strehl\experiments\V-HEADTOHEAD2\timing2.ps1:150-190`

The repository summary rounds this to:

> “the fork measured **13.93 s/frame**”

`C:\dev\blog\death-of-software\projects\strehl\README.md:1325-1356`

**[VERIFIED]** That measurement used the 860-task graph and `--hdr-preserve=off`; the default auto/on route exhausted memory. It is a later, badly regressed May 17 build—not the “best-known” build behind 2.4×.

### The different “best-known build” behind 2.4×

**[VERIFIED]** The best retained historical run is in:

`C:\dev\macro\out\coffee-bean\stack.log`

It contains 105 source-load tasks and reports:

> `OpenCL device: NVIDIA Corporation NVIDIA GeForce RTX 5090 OpenCL 3.0 CUDA`

`C:\dev\macro\out\coffee-bean\stack.log:1-9`

For the merged TIFF:

> `93.068 [768/772] ... Starting task: Save ... stack.tif`

> `Saved Linear Rec.2020 (D65, gamma 1.0) TIFF: ... stack.tif`

> `93.739 ... Finished task 768 in 0.671 s.`

`C:\dev\macro\out\coffee-bean\stack.log:2164-2173`

The final depth/3D artifacts completed at:

> `143.458 ... Finished task 772 in 0.373 s.`

`C:\dev\macro\out\coffee-bean\stack.log:2174-2188`

The comparable merged-TIFF scope is therefore **93.739 seconds**, or approximately **0.893 s/frame** over 105 frames. Against Strehl’s 38.39-second comparable result:

> “`93.739 / 38.39 = 2.4428`”

`C:\dev\blog\death-of-software\projects\strehl\docs\research\V-HEADTOHEAD2.md:1148-1200`

That is the source of the defensible **2.4×** claim.

### Reproducibility gap

**[NOT FOUND]** The exact executable and source revision that produced the May 10 93.739-second best-known run were not retained or cryptographically bound.

The executable-provenance audit concludes:

> “No available executable or source revision can be bound to the archived coffee render.”

`C:\dev\blog\death-of-software\projects\strehl\experiments\M8-COMPARATIVE\focus-stack-executable-provenance.json:36-43`

The later source audit identifies only a candidate source tree and comparison baseline:

- `chcaru/macro@864ff08862414682e75d58245a1e7f1d25cf3315`;
- `PetteriAimonen/focus-stack@0cd289e224fe24aead5b146faeaa46950775f346`.

It also states that the binary has no embedded revision or reproducible-build identity:

`C:\dev\blog\death-of-software\projects\strehl\experiments\M8-COMPARATIVE-CONTROLLED\SOURCE-AUDIT-RESULT.md:7-23`

The archived log’s mtime is `2026-05-10T23:45:16Z`. The fork’s first retained commit, `4bc7f95e448cf20ee2bdd758403ec43e2612a1c6`, was created about three hours later. It is the nearest retained snapshot, not proof of the source that built the logged executable.

**Conclusion:** “Rebuild the fork at its best-known build” is not presently reproducible. The 13.93 s/frame May 17 binary is identified; the May 10 best-known 2.4× binary/source pair is not.

---

## Repository contradictions and corrections

**[DISPUTED]** `docs/STATUS.md` says:

> “Professional is specifically required for Save Adjusted Input Images…”

`C:\dev\blog\death-of-software\projects\strehl\docs\STATUS.md:2677-2685`

Current vendor documentation says the feature requires **Prosumer or Professional**. The repository’s technical Professional-only statement is stale, although Professional may still be legally required by Zerene’s use restrictions.

**[DISPUTED]** The authoritative plan says:

> “licensed Zerene … the fork rebuilt at its best-known build … Helicon if obtainable.”

`C:\dev\blog\death-of-software\projects\strehl\docs\proposals\2026-08-sota-path.md:1535-1539`

The scorecard later requires both commercial products and says:

> “If either product cannot produce a linear output that passes §1.3, the named-comparator requirement is unmet and the SOTA verdict remains `UNMEASURED`.”

`C:\dev\blog\death-of-software\projects\strehl\docs\proposals\2026-09-sota-scorecard.md:280-295`

That is a real policy conflict. Under the authority order supplied for this lane, Helicon is optional.

**[VERIFIED]** The owner page’s current Helicon claim is not stale; it is confirmed:

> “that capability is only in 9.0.5 Beta; current stable 8.3.11 documents no alignment bypass.”

`C:\dev\blog\death-of-software\projects\strehl\docs\OWNER-ACTIONS.md:888-898`

**[DISPUTED]** The plan’s “best-known build” requirement cannot currently be reproduced exactly because no executable hash or source revision is bound to the May 10 run. The identified 13.93 s/frame May 17 build is a separate regression and must not be substituted for the best-known build.

---

## Requested short summary

- **Q0:** Zerene **does** export aligned, brightness-corrected source frames; current permanent gating is **Prosumer or Professional**. It is **not yet proven** to emit the required native-size 16-bit linear TIFF, and no public batch/CLI task for that specific export was found.
- **Q1 verdict:** **NO** — the required Helicon unmasked aligned-source export is not in a stable release today; it remains in **9.0.5 Beta**.
- **Current stable Helicon:** **8.3.11, released 16 February 2026**.
- **Zerene Professional:** **$289; perpetual YES**. Personal is $89 and Prosumer $189.
- **Zerene automation:** General unattended XML/CLI batch for PMax and DMap is available and is not documented as edition-gated; automation of **Save Adjusted Input Images** is **NOT FOUND**.
- **Best alternative:** **Enfuse**, because it is headless, accepts TIFF inputs directly, keeps alignment in a separate executable, and has uint16/identity-colour/ICC source paths; it remains an additional foreign arm, not a Zerene substitute.
- **Contradictions:** The repo’s Professional-only Zerene feature claim is stale; mandatory Helicon in the scorecard conflicts with the authoritative plan’s “Helicon if obtainable”; and the fork’s best-known 2.4× build is not reproducibly pinned.
