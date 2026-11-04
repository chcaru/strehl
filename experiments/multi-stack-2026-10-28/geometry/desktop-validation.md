# Desktop session validation — October 28, 2026

## Scope and build

**VERIFIED mechanism/UI behavior, not photographic improvement.** The actual
desktop worker rendered ten original RAW acquisitions through its embedded CLI
engine. These middle-five subsets do not cover the subject's complete focus
range. The complete-session quality campaign belongs to the root lane.

Workdir: `C:\Users\chris\.codex\worktrees\multi-stack\strehl`.
Build: `c149e52834fc-multi-stack-candidate3`, based on fetched remote-main
`c149e52834fc1c86c2af0fe022713c39fa25f33c`. Frozen source hashes and executable
hashes are in `outputs/multi-stack/candidate-3/build.json`; owned sources are
archived beside it. UI executable SHA256:
`98a0b1681b2aac8d955e0780b4c61a5e0ba69a14ff25a10e5bced8b3f02fe3fc`.

Inputs are the exact five-frame copies per pass in
`outputs/multi-stack/pilot-inputs/pass-106` and `pass-107`, described by
`outputs/multi-stack/manifests/insect-middle-five.json`. Original corpus paths,
copy paths, whole-file hashes and stamps are in
`outputs/multi-stack/pilot-inputs/provenance.json`. No corpus write was performed.
Root held competing numerical jobs while these two sequential renders ran.
There was no independent host-load sample; elapsed times below are receipts,
not a performance comparison.

## Real application exercise

State and requests: `outputs/multi-stack/desktop-validation/candidate3/`.
Outputs: `outputs/multi-stack/desktop-validation/renders/`.

The launch was made through the documented local control helper, not OS input:

```powershell
python scripts/strehl-control.py --exe C:\Users\chris\.codex\worktrees\multi-stack\strehl\outputs\multi-stack\candidate-3\strehl-ui.exe --session-file C:\Users\chris\.codex\worktrees\multi-stack\strehl\outputs\multi-stack\desktop-validation\candidate3\ready.json launch --wait --grant C:\Users\chris\.codex\worktrees\multi-stack\strehl\outputs\multi-stack\pilot-inputs --source C:\Users\chris\.codex\worktrees\multi-stack\strehl\outputs\multi-stack\pilot-inputs\pass-106 --output-dir C:\Users\chris\.codex\worktrees\multi-stack\strehl\outputs\multi-stack\desktop-validation\renders
```

The published process was PID 42648. The same helper's `snapshot`,
`call --request FILE`, and `shutdown` commands then operated the protected
mailbox. Every mutation used the fresh snapshot revision. Request JSON files
preserve exact payloads, including catalog IDs and revisions:

| Request | Observed result |
| --- | --- |
| `import-107.json` | Imported the second granted folder as ordinary catalog stack 3; stack 2 retained pass 106. |
| `create-repeat.json`, `start-repeat.json` | Created stack 4, two five-frame passes, Repeat, primary absent, 16 GiB. Desktop worker saved the photograph and linear master. |
| `create-layers.json`, `start-layers.json` | Created stack 5, reversed pass order 107 then 106, Layers, primary index 1. Both aligned photographs and masters saved; primary layer 02 opened initially. |
| `create-segments.json` | Created an unrendered layout control: one pass with catalog directories 2 then 3. Source scan reported ten captures with segment ends `[5,10]`. This is an interface control, not a claim the repeat captures are a physical continuation. |
| `reopen-layers.json` | Selected stack 5 run 0; restored two pass groups, primary index 1, both layer paths and the scene-linear photograph. |

Saved snapshots include `repeat-ready.json`, `repeat-progress.json` (completed),
`layers-ready.json`, `layers-complete.json`, `segments-ready.json` and
`layers-reopened.json`. Both final render snapshots report no error, no busy
worker, and `Stack saved`. Source groups are 0..5 and 5..10 in the declared order.

| Run directory under `renders/` | Outputs | Engine receipt |
| --- | --- | --- |
| `strehl-1793213081384-42648-0` | `session-output/photograph.tiff` and `master.tiff`, 7008×4672 | Ten frames, two passes, one output, primary null, 21.7219055 seconds. |
| `strehl-1793213142750-42648-1` | `session-output/layer-01/` and `layer-02/`, each photograph plus master, 7008×4672 | Ten frames, two passes, two outputs, primary 1, 22.0966977 seconds. |

Each run retains `session-manifest.json`, `session-recipe.json`,
`session-outputs.json`, complete `render.log`, and the engine's source hashes,
completion and alignment reports. The log records the exact executable and
arguments: the actual engine is `strehl-ui.exe --engine-worker session stack`,
with `--memory-limit-gib 16 --threads 32 --resampler catmull-rom` and the shared
`renders/.strehl-session-cache` destination. All numeric merge overrides were
absent, leaving the recorded engine defaults. Full-resolution output was used.
The desktop worker decoded each complete photograph and each scene-linear
master, checked the master baseline and matching dimensions before publication.

The isolated app accepted orderly `shutdown`; its waiting launcher reported
`process_exited` with exit code 0. The catalog was not reused until exit.

## Actual workspace rendering

`layers-workspace-verified.png` is a 1440×940 GPU readback of the actual egui/wgpu
workspace, opened with the isolated catalog and `--open-run` pointing at the
saved Layers run, with `--projects`. `offscreen-command.json` preserves the exact
argument vector; `offscreen-verified.log` and `offscreen-exit.json` preserve the
waited subprocess result, exit 0. The screenshot was inspected with the image
tool. It visibly contains both named passes, the selected primary, continuation
and independent-pass actions, layer selector, the saved photograph, and the
matching grouped capture timeline. There is no native window or OS input.

An earlier direct PowerShell GUI invocation returned before exposing a native
exit code; its screenshot is retained but is not the verified exit evidence.
The fresh second invocation used Python `subprocess.run` with the exact saved
argument vector and hidden process creation, and captured the actual exit code.

The screenshot is orientation/layout evidence only. It does not commission
native HDR monitor presentation, native-resolution photographic quality,
source-ownership diagnostics, or a mouse interaction with the layer picker.
The picker and timeline interaction have separate author-run egui tests; only
saved-run restoration and initial-primary selection were exercised via the
real application in this lane.

## Independent review repairs after candidate 3

These source changes require the root's next build/tests; they are not credited
to candidate-3 execution:

- Entering a session now remembers the complete ordinary recipe using existing
  `history::Recipe` (settings, exposure, gate and worker count). Fresh ordinary
  import restores it. This prevents forced session restrictions or manual
  exposure changes from leaking into later ordinary stacks. Adversarial tests
  cover defaults, custom automatic exposure and temporal mode; they alter
  session controls and compare restored recipes and exact ordinary CLI flags.
- Before publishing a session as Saved, the worker compares the engine's
  ordered source receipt against the immutable UI snapshot by count, canonical
  path, size and nanosecond stamp, then requires a supported completion receipt.
  Added/removed/reordered/replaced sources and overflowing stamp conversion are
  refused. Root added matching receipts to the unchanged single-pass delegate.
- The local-control snapshot now describes Layers primary semantics separately:
  common reference and initially displayed layer; each layer keeps its own
  appearance.

All numerical work in this lane ended after the two renders above. No third
render was dispatched while the root's full-session campaign was running.

## Completed-session presentation repair

Root and independent screenshot review found that candidate 3 retained ordinary
progress instruments after saving Layers. Their last-pass counters said 5/10,
the saved header used ten captures, and unavailable alignment/admission panels
looked unfinished. The photographs were complete; these were incompatible UI
scopes. This invalidated candidate 3 as final presentation evidence.

The next source revision replaces only the completed-session process canvas.
`session-summary.rs` reads the retained recipe, completion and alignment reports;
it checks each pass census, preserves immutable pass names, and represents
missing measurements as unavailable. `process-session.rs` presents whole-session
totals, placed/refused counts, measured pairs and graph cycles, with a separate
current-layer label and its own capture count. It reuses the existing standalone
photograph viewport, without ordinary admission inputs. The session source
browser labels camera previews, dims captures outside the selected layer, and
states that admission overlays are unavailable. Ordinary process presentation
continues through its existing branch.

The painter control supplies deliberately misleading last-layer counters
(2/6 processed and accepted), requires retained six-capture/session and
two-capture/layer scopes, and rejects ordinary pending/accepted labels. A
separate malformed pass-census control must report unavailable geometry rather
than invented zero fits.

## Candidate 5 presentation and editing verification

**VERIFIED:** root reports the rebuilt full UI suite passed 987 tests, with 15
ignored. The frozen executable is
`outputs/multi-stack/candidate-5/strehl-ui.exe`, SHA256
`9fb20ee6590491d2b5d01551749340cd3708e87ca79e5d0eb8ff07808dbf4878`, build
`c149e52834fc-multi-stack-candidate5`.

The existing candidate-3 catalog and saved Layers run were opened with that
executable. No engine/RAW render was launched. The actual egui/wgpu images are
`outputs/multi-stack/desktop-validation/candidate5/layers-workspace.png` and
`layers-edit-workspace.png`. Both subprocesses exited 0; exact command vectors,
logs and exits are retained as `offscreen-command.json`, `offscreen.log`,
`offscreen-exit.json` and their `offscreen-edit-*` counterparts. The only changed
launch presentation flag for the second image is `--projects` to `--edit`.
Both images were inspected through the image tool.

The Projects image displays the measured 10/10 placed, zero refused, 41 pair
fits and 32 graph cycles separately from the visible “Layer 2 of 2 · Pass 106
primary · 5 captures.” It states two completed photographs plus linear masters.
There is no ordinary 5/10 process counter, pending scale matrix, or unavailable
admission plot. Other-pass thumbnails are dimmed, and the source browser says
admission overlays are unavailable. The photograph footer describes only image
navigation. The Edit image retains ordinary photograph adjustments, region
tools, saved-version actions and the editable photograph viewport, with the same
saved-session scopes.

The real headless application was also relaunched with candidate 5 and the same
isolated catalog, PID 30448, using:

```powershell
python scripts/strehl-control.py --exe outputs/multi-stack/candidate-5/strehl-ui.exe --session-file outputs/multi-stack/desktop-validation/candidate5/ready.json launch --wait --catalog outputs/multi-stack/desktop-validation/candidate3/ready.projects.json --output-dir outputs/multi-stack/desktop-validation/renders
```

Revision-bound requests in `candidate5/` selected saved stack 5/run 0, requested
2× view centered at `[0.42,0.58]`, changed development exposure to +0.25 EV, saved
the named version “Desktop session validation quarter-stop”, then restored the
exact original recipe. `before-controls.json`, `edited.json`,
`version-saved.json` and `restored.json` retain the observed states. The final
state had exposure 0, no error or busy work, and the correct saved layer master.
The app accepted shutdown and its waiting launcher reported exit 0.

The zoom command was accepted, but a headless application does not paint the
viewport (`photo_view` remained null). This is command-path evidence only, not a
claim of a rendered zoom gesture. The actual offscreen screenshots commission
the default photo and edit layouts. Manual OS mouse interaction and monitor HDR
presentation remain outside this check.

## Candidate 6 final worker-to-history check

**VERIFIED:** after explicit root release, exactly one additional ten-source
Repeat render ran through the current desktop worker, with primary pass 0,
16 GiB and 32 workers. Build `c149e52834fc-multi-stack-candidate6` is frozen at
`outputs/multi-stack/candidate-6/strehl-ui.exe`, SHA256
`1629df86c1f770a1aa9dc0d6824a5c5edea63532191ee80bf2dadcfe8dbaeb9d`.
The ordinary single-pass path was not exercised by this desktop run.

```powershell
python scripts/strehl-control.py --exe outputs/multi-stack/candidate-6/strehl-ui.exe --session-file outputs/multi-stack/desktop-validation/candidate6/ready.json launch --wait --catalog outputs/multi-stack/desktop-validation/candidate3/ready.projects.json --output-dir outputs/multi-stack/desktop-validation/renders
```

The actual revision-bound creation and start payloads are in
`candidate6/create-repeat.json` and `start-repeat.json`; `repeat-ready.json` and
`repeat-complete.json` retain the input and saved states. The worker used the
existing shared desktop source cache. Saved catalog stack 7 has exactly one
revision, `renders/strehl-1793215569755-4580-0`, and the app reported `Stack saved`,
`photo_ready:true`, no error and no busy operation.

`candidate6/verify-receipts.py` was executed with Python and exited 0. Its
`receipt-verification.json` verifies all ten ordered path/size/nanosecond stamps
against the immutable UI snapshot, every engine source SHA256 against the pilot
provenance, and the saved catalog recipe/source list against that worker
snapshot. Completion reports ten frames, two passes, one output and primary 0.
The retained alignment has ten placed captures, 41 measured edges and 32 graph
cycles. The complete photograph is 196453474 bytes and its scene-linear master
392900853 bytes, both 7008×4672; full decode/baseline/dimension validation and the
new exact source postflight succeeded before Saved publication.

The engine receipt records 36.4182551 seconds. Root's other controls ran
concurrently by explicit allocation; this is not an isolated benchmark or a
comparison with the earlier candidate-3 elapsed times.

The owned headless process, PID 4580, accepted orderly shutdown and its waiting
launcher reported exit 0. The current executable then reopened that newly saved
run in the actual egui/wgpu offscreen path, also exit 0. The exact vector, log,
exit and inspected image are `candidate6/offscreen-command.json`,
`offscreen.log`, `offscreen-exit.json` and `repeat-workspace.png`. The image shows
the explicit primary, complete ten-capture session, retained geometry counts,
saved photograph and source-only browser without unfinished ordinary panels.
No further RAW job was launched in this lane.

## Candidate 7 final integration and transfer prefetch

**VERIFIED:** after a subsequent explicit root release, the final bounded-transfer
build ran one ten-source Repeat revision through the real desktop worker. Build
`c149e52834fc-multi-stack-candidate7` is frozen at
`outputs/multi-stack/candidate-7/strehl-ui.exe`, SHA256
`51e99d3d9528510bc79be406253254bf5beb075e1a3efefbe10eea66fd1edf48`.
The worker used the existing stack-7 recipe: primary 0, 16 GiB, 32 workers,
and the shared desktop source cache. No product source was changed by this lane.

```powershell
python scripts/strehl-control.py --exe outputs/multi-stack/candidate-7/strehl-ui.exe --session-file outputs/multi-stack/desktop-validation/candidate7/ready.json launch --wait --catalog outputs/multi-stack/desktop-validation/candidate3/ready.projects.json --output-dir outputs/multi-stack/desktop-validation/renders
```

`candidate7/select-repeat.json` selects existing stack 7; `start-repeat.json`
starts its new immutable revision. The saved job is
`renders/strehl-1793217251483-21592-0`. `repeat-complete.json` records `Stack saved`,
the ready 7008×4672 scene-linear master, no busy operation and no error. The
catalog now contains both completed revisions of that stack.

`python outputs/multi-stack/desktop-validation/candidate7/verify-receipts.py`
exited 0. `receipt-verification.json` records the exact ordered source-stamp,
original-provenance SHA256 and catalog-snapshot checks, plus the new
`render-report.json` transfer reservation:

| Receipt field | Value |
| --- | --- |
| Reserved lane cap | 4 |
| Per-probe bytes | 426382322 |
| Retained result bytes | 43520 |
| Transfer reserved bytes | 1705572808 |
| Total working memory reservation | 9033618959 bytes, below the 16 GiB limit |
| Actual per-source cache-hit flags | All 10 true |
| Transfer phase elapsed | 0.0032907 seconds |

The check verifies `reserved = lanes × per_probe + retained`, that per-probe
storage agrees with the recorded probe memory estimate, and that the complete
working reservation fits the user limit. Lanes describe a planned concurrency
cap, not a measurement of simultaneously active cold probes. This run reused
all ten transfer receipts and cannot benchmark cold-prefetch speed. The engine
completion receipt is 12.5097922 seconds; root HDR controls and a full render
were concurrent by allocation, so no isolated timing claim is made.

The result retains ten placed sources, 41 measured pair fits and 32 graph
cycles, one 7008×4672 photograph and one linear master. `render.log` lines 10–12
record the merge stage before the ten-probe preparation message and its bounded
four-lane/cache-hit summary. Source postflight and complete image validation
succeeded before the new catalog revision was marked Saved.

The owned headless PID 21592 shut down cleanly and its launcher exited 0.
`candidate7/offscreen-command.json` then opened this newly saved run with the
same executable; `offscreen-exit.json` records 0 and the log records a 1440×940
Dx12 GPU readback with no OS window. The inspected `repeat-workspace.png` shows
the complete two-pass/ten-capture session, explicit primary, saved geometry
counts, photograph and source-only browser, with no ordinary pending panels.

The scoped package review also confirmed `docs/multi-stack.md` is copied and
linked from the package README. Root added the guide's referenced
`experiments/multi-stack-2026-10-28/brief.md` to the source package, resolving the
previously reported broken evidence link. This is a source-script review, not a
claim that a separately distributed archive was installed or exercised.
