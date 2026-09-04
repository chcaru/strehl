# M175 — retained fork comparator arm

## Verdict

**FORK REBUILT.**

The retained fork source is recoverable, two clean same-host builds are
bit-for-bit identical, the executable SHA-256 was frozen and committed before
image rendering, and the frozen build passed the complete §1.3 native-size
eight-copy tone sentinel. This is a development admission of the fork
rebuild/transfer sub-arm, not a scored quality result
(`experiments/M175-fork-arm/render-result.json:7`,
`experiments/M175-fork-arm/render-result.json:31`,
`experiments/M175-fork-arm/render-result.json:82-112`,
`experiments/M175-fork-arm/render-result.json:240-294`).

No scorecard axis changes status. Licensed Zerene PMax and licensed Zerene DMap
remain required alongside the fork, and the rule says that if any required arm
cannot provide an admitted linear output, dependent axes remain `UNMEASURED`
(`docs/proposals/2026-09-sota-scorecard.md:193-200`,
`docs/proposals/2026-09-sota-scorecard.md:471-478`).

## 1. What “the fork” is

The scorecard's fork is not pristine upstream `focus-stack`. It is Chris
Caruso's modified MIT-licensed fork of Petteri Aimonen's `focus-stack`, retained
at `C:\dev\macro\focus-stack`
(`docs/research/M162-noise-regression.md:20-23`). The retained repository's
origin is `https://github.com/chcaru/macro.git`; the selected source's README
identifies upstream `https://github.com/PetteriAimonen/focus-stack`
(`experiments/M175-fork-arm/revision-selection.json:17-24`,
`experiments/M175-fork-arm/revision-selection.json:38-42`).

“Best-known retained source revision” is concrete here: commit
`4bc7f95e448cf20ee2bdd758403ec43e2612a1c6`, the root and earliest retained
commit touching `focus-stack`. It postdates the archived run log by
`11502.643535` seconds; the next retained revision,
`412d1b5226f69b186a6e8b8ef91b4befa3c55664`, already changes 27 files by 1,582
insertions and 154 deletions
(`experiments/M175-fork-arm/revision-selection.json:26-35`,
`experiments/M175-fork-arm/revision-selection.json:45-55`). It is therefore the
nearest and least-confounded retained source snapshot, but it is **not** claimed
to be the archived producer
(`experiments/M175-fork-arm/revision-selection.json:51-55`). The scorecard
itself identifies this as the beginning of retained history while warning that
existence of the pin did not establish buildability
(`docs/proposals/2026-09-sota-scorecard.md:452-458`).

The archived comparator is
`C:\dev\macro\out\coffee-bean\stack.tif`, SHA-256
`8636c20d73ca0cb1f57db89bf8553abc166e0fbc517e5c62a07c74dee509066e`
(`docs/research/M162-noise-regression.md:23-28`). It fails blocker `(d)` for
the exact reason the scorecard gives:

> “the byte-pinned artifact used `105` Lightroom-developed TIFFs, has no
> producing binary or source revision bound to the render, and is not
> reproducible. The retained May 17 executable postdates the render by six
> days and is not its producer.”

(`docs/proposals/2026-09-sota-scorecard.md:459-464`). M175 independently
re-read the archived file and log and still records the producer identity as
`UNKNOWN` (`experiments/M175-fork-arm/revision-selection.json:2-15`).

The unrelated fork/Strehl repository histories prohibit only a cross-project
bisect: “A Git bisect from one program to the other is impossible and would
confound both algorithm and input development”
(`docs/research/M162-noise-regression.md:42-46`). That does not obstruct this
work because M175 rebuilds the pinned fork source directly rather than
attempting a cross-project attribution.

## 2. Exact admission conditions

The operative conditions are:

1. **Required identity and ordering.** The required set is “licensed Zerene
   Stacker PMax, licensed Zerene Stacker DMap, and a fresh fork rebuild from the
   best-known retained source revision, pinned by commit before scoring, with
   the built executable's hash frozen before rendering”; every included mode
   uses a frozen setting with user post-processing disabled
   (`docs/proposals/2026-09-sota-scorecard.md:193-200`).
2. **Pre-output freeze.** “Before any stacker runs,” the input, site, and run
   manifests plus synthetic plants and hidden truth must be committed; site
   selection may inspect inputs but never an output, after which the site
   manifest is hashed and immutable
   (`docs/proposals/2026-09-sota-scorecard.md:341-354`).
3. **Common input form.** The shared derivative must be “**uncompressed**
   16-bit **linear ProPhoto RGB, D50** TIFFs at the native active-image
   dimensions,” with the listed development operations disabled, only the
   frozen linear ICC/provenance/source hash embedded, and both pixel payload
   and whole TIFF hashed
   (`docs/proposals/2026-09-sota-scorecard.md:365-373`).
4. **Byte identity at consumption.** PMax, DMap, the fresh fork, and Strehl
   “must receive the exact same TIFF bytes”; the fork executable hash must
   already be frozen
   (`docs/proposals/2026-09-sota-scorecard.md:375-381`).
5. **Output form and no post-processing.** “Each program must emit a
   native-size 16-bit linear TIFF.” Histogram matching, auto-exposure, white
   balance, sharpening, denoising, resizing, and tone mapping after stacking
   are forbidden, and numerical metrics run in linear light
   (`docs/proposals/2026-09-sota-scorecard.md:413-419`).
6. **§1.3 tone sentinel.** The input set contains eight identical copies of a
   33-step neutral linear ramp from `0.02` to `0.98`; each channel is fitted as
   `y = ax + b` on steps 2–32. The exact acceptance limits are
   `0.995 <= a <= 1.005`, `|b| <= 0.001`, maximum absolute affine residual
   `<= 0.002`, RMS affine residual `<= 0.0005`, no interior clipping, and
   strictly monotone ordering
   (`docs/proposals/2026-09-sota-scorecard.md:421-429`).
7. **Input audit.** Any file or sidecar containing non-zero `Contrast2012`,
   `Sharpness`, `Clarity`, `Texture`, `LuminanceSmoothing`, a tone curve, or an
   equivalent development instruction fails admission
   (`docs/proposals/2026-09-sota-scorecard.md:431-439`).
8. **Complete fork freeze.** Before rendering, record the source-tree hash,
   toolchain/dependency lock, compiler flags, final executable SHA-256, and
   complete settings manifest. Select one build and one preset before any
   scored output; per-subject tuning and post-result rebuilding are forbidden
   (`docs/proposals/2026-09-sota-scorecard.md:443-458`).
9. **Failure consequence.** If the fork cannot produce a linear output passing
   §1.3, the named-comparator requirement is unmet. Until the pinned rebuild,
   pre-render executable hash freeze, and exact common-input consumption all
   exist, the fork remains `UNMEASURED` under `(d)`
   (`docs/proposals/2026-09-sota-scorecard.md:471-478`).

The literal §1.1 destination is `experiments/SCORECARD/`
(`docs/proposals/2026-09-sota-scorecard.md:341-350`). M175's ownership
constraint prohibited editing that path, so the equivalent pre-render
manifests and truth live under `experiments/M175-fork-arm/` and were committed
before rendering. This makes the result a reproducible arm-admission package,
not a scored `experiments/SCORECARD/` campaign.

## 3. Execution and evidence

### Source and reproducible build

M175 froze the selected Git subtree without reading the mutable worktree:

- commit: `4bc7f95e448cf20ee2bdd758403ec43e2612a1c6`;
- subtree Git SHA-1: `543b825e325f959ed15c10032d2b8156f11070cc`;
- 103 files, 14,961,176 source bytes;
- canonical source-manifest SHA-256:
  `494d3abb49ccec3f23d7c37676acd806111f973f12c0cf416ae45999359d1196`;
- `source-pin.json` SHA-256:
  `603e2cd42526707cd0ce7871a44b645ba63bb866b6c2749e1a507032bd45d222`.

The source commit/tree/manifest bindings are recorded in
`experiments/M175-fork-arm/build-freeze.json:232-236`; the source-pin file
enumerates every retained blob.

Two clean source and build directories produced byte-identical 271,360-byte
executables with zero differing bytes:

```text
SHA-256 691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac
```

(`experiments/M175-fork-arm/build-freeze.json:101-107`,
`experiments/M175-fork-arm/build-freeze.json:140-166`,
`experiments/M175-fork-arm/build-freeze.json:195-228`). The runtime-bundle
SHA-256 is
`4b9d4c310a16294bcc46ee5b947aec02cbdba9887787af017018071dd9455150`
(`experiments/M175-fork-arm/build-freeze.json:36-75`). An independent earlier
M165 build at commit `e3f2c841b6ed41ab131fc842172c52bdd9752a61`
produced the same executable hash
(`experiments/M175-fork-arm/verification.json:61-65`).

### Freeze-before-render ordering

The executable hash, source pin, two-build evidence, input manifest, site
manifest, truth, run manifest, and fixed settings were committed before the
successful render. The pre-render freeze records executable SHA-256
`691eada9...09ac`, input SHA-256 `dc6c7871...532e`, and confirms the output was
absent (`experiments/M175-fork-arm/PRE-RENDER-FREEZE.json:3-4`,
`experiments/M175-fork-arm/PRE-RENDER-FREEZE.json:82-88`). The committed
pre-render guard is `32618aafb66e88c066fcbb638507423810b29050`; the persisted
ordering checks say both freeze-before-render and render-start-before-output
creation are true
(`experiments/M175-fork-arm/render-result.json:8-29`). These timestamps are
used only to prove ordering, never as performance evidence.

The fixed preset disables alignment, white-balance matching, contrast
matching, consistency filtering, denoising, and OpenCL; fixes one thread and a
batch size of two; accepts input bytes without a colour conversion; and requests
16-bit TIFF output. No post-stack processing or per-subject tuning is admitted
(`experiments/M175-fork-arm/SETTINGS-MANIFEST.json:2-20`).

### Exact common input and §1.3 result

The frozen sentinel has eight distinct paths to one byte-identical 197,684,652
byte TIFF, native `7028 x 4688`, uncompressed RGB16, with the deterministic
linear ProPhoto D50 ICC and no sidecars or forbidden development instructions
(`experiments/M175-fork-arm/INPUT-MANIFEST.json:2-27`,
`experiments/M175-fork-arm/INPUT-MANIFEST.json:29-172`). Its whole-file
SHA-256 is
`dc6c7871137283448ebff150832559c7cf42cd8b7c3551eea72920247957532e`;
its pixel-payload SHA-256 is
`2f8d3631e7e858e4e4fbb79d61ee031d07af7f5a809cc12050ab4d4501751087`
(`experiments/M175-fork-arm/INPUT-MANIFEST.json:178-183`).

The rebuilt fork consumed all eight paths and emitted a native
`7028 x 4688 x 3` uint16 TIFF. Output SHA-256 is
`d40e59699b1a9fd19972a78f4c0ec2aa99b32cc9f97ac7c44eab8e3b847caaad`;
the decoded output-pixel SHA-256 equals the frozen input-payload SHA-256
exactly (`experiments/M175-fork-arm/render-result.json:82-112`). The output
does not carry an ICC tag; §1.3 does not require one on output, and the
full-frame pixel identity plus the ramp fit establish the frozen linear
interpretation (`experiments/M175-fork-arm/render-result.json:88-99`,
`docs/proposals/2026-09-sota-scorecard.md:413-429`).

All three channels produced the same fit:

| quantity | measured |
|---|---:|
| slope | `1.0000000000000002` |
| intercept | `-6.6597626500634704e-18` |
| maximum absolute affine residual | `2.220446049250313e-16` |
| RMS affine residual | `1.3031039891780493e-16` |
| interior clipping | none |
| ordering | strictly monotone |

Every §1.3 predicate is `true`
(`experiments/M175-fork-arm/render-result.json:240-285`,
`experiments/M175-fork-arm/render-result.json:291-294`). The independent
post-run verifier re-read the executable, manifests, input, and output and
reports every check `true`, including the two-build identity, §1.3 pass,
full-frame decoded-pixel identity, frozen ordering, and absence of a holdout
path (`experiments/M175-fork-arm/verification.json:40-59`,
`experiments/M175-fork-arm/verification.json:68`).

No file under `D:\personal\macro` or `D:\edited\macro` was read or written.
The invocation contains only the M175 synthetic common-input paths, and the
verifier's holdout-path check is true
(`experiments/M175-fork-arm/render-start.json:1-46`,
`experiments/M175-fork-arm/verification.json:50-52`).

### Preserved failed preflights

The first render preflight stopped before launching because Git's CRLF
conversion made the working bytes differ from the committed bytes; that
failure is retained in
`experiments/M175-fork-arm/preflight-failure-crlf.json:1-6`. A subsequent
non-native `2112 x 128` synthetic attempt exited with Windows access violation
`0xC0000005` and wrote no TIFF; it was invalid under §1.2's native-dimension
rule and is retained in
`experiments/M175-fork-arm/invalid-nonnative-render-failure.json:1-18`.

The sole native-size render succeeded. Its wrapper then failed only while
serializing NumPy boolean values after output inspection and scoring. The
existing TIFF was finalized without rerendering; the result records
`no_rerender: true` and `original_output_reused: true`
(`experiments/M175-fork-arm/render-result.json:67-80`). No fork source,
executable, input, or setting changed after the pre-render freeze.

## 4. Scorecard effect

**Clearing the fork sub-arm alone changes no axis status.** All three named
required arms must be present
(`docs/proposals/2026-09-sota-scorecard.md:193-200`), and a missing required arm
keeps the named-comparator requirement unmet
(`docs/proposals/2026-09-sota-scorecard.md:471-478`). In particular, M3 remains
`UNMEASURED_COMPARATOR_QUALIFICATION` if any required comparator is absent
(`docs/proposals/2026-09-sota-scorecard.md:1149-1158`), and M11 remains so for
a missing required arm
(`docs/proposals/2026-09-sota-scorecard.md:1867-1876`). Licensed Zerene PMax and
DMap are still absent, and this lane created no scored campaign corpus.

The task brief's “10 of 12; only M8 and M12 escape” count is not the current
§3.1 classification. The table marks `(d)` explicitly on seven axes, M1–M7;
M11 carries the same comparator dependency under
`UNMEASURED_COMPARATOR_QUALIFICATION`; M9 is transitively blocked through M1;
and **M10, M8, and M12 are comparator-independent**
(`docs/proposals/2026-09-sota-scorecard.md:776-789`,
`docs/STATUS.md:6649-6658`). Thus the comparator dependency reaches nine axes,
not ten, and no status changes from this fork rebuild alone.

## 5. Defects for the orchestrator to repair

M175 did not edit these owner-controlled files.

### `docs/proposals/2026-09-sota-scorecard.md`

Current text:

> “The first retained fork commit ... makes a fresh rebuild plausibly
> constructible but does not establish that it builds. Until a qualifying
> rebuild exists, every fork result cell is `UNMEASURED` under blocker `(d)`.”

(`docs/proposals/2026-09-sota-scorecard.md:162-166`).

Recommended replacement:

> The retained fork was rebuilt from commit
> `4bc7f95e448cf20ee2bdd758403ec43e2612a1c6`. Two clean same-host builds were
> byte-identical at executable SHA-256
> `691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac`;
> the hash and settings were committed before rendering, and the build passed
> §1.3 on the native-size eight-copy common-input tone sentinel. The fork
> rebuild/transfer prerequisite is closed. Fork score cells remain
> `UNMEASURED` until scored common-input campaign outputs exist, and blocker
> `(d)` remains at run level while licensed Zerene PMax or DMap is absent.

The same distinction should replace lines 2033–2036 and 2173–2178: the rebuild
and development transfer are no longer absent, but no scored fork quality
column exists yet
(`docs/proposals/2026-09-sota-scorecard.md:2033-2037`,
`docs/proposals/2026-09-sota-scorecard.md:2173-2179`).

### `docs/STATUS.md`

Current text:

> “The third — the fork rebuild — needs no licence, no money, no photography
> and no owner action, and has never been attempted. Lane M175 is on it.”

(`docs/STATUS.md:6660-6665`).

Recommended replacement:

> The third arm is complete: M175 independently rebuilt retained commit
> `4bc7f95e448cf20ee2bdd758403ec43e2612a1c6` twice to byte-identical executable
> SHA-256
> `691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac`,
> froze it before rendering, and passed §1.3 on the native-size eight-copy tone
> sentinel. Blocker `(d)` and every dependent axis remain unmoved because
> licensed Zerene PMax and DMap are still absent.

### `docs/OWNER-ACTIONS.md`

The header says “Last updated after lanes M157, M159, M160, M161” even though
the body discusses M164 and M165
(`docs/OWNER-ACTIONS.md:3-12`,
`docs/OWNER-ACTIONS.md:502-508`). Recommended replacement:

> Maintained by the orchestrator. Last updated after lane M175.

At the Zerene decision, replace “buy the edition they name and `(d)` is
cleared” with:

> The fork sub-arm is complete. Buy the edition they name; `(d)` clears only
> after both licensed PMax and DMap produce common-input outputs that pass
> §1.3.

The current text is at `docs/OWNER-ACTIONS.md:474-478`.
