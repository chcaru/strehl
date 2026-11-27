# Desktop control without mouse or keyboard automation

Strehl exposes the application's existing workspace commands through its local
agent mailbox. Use the packaged executable's `--control` mode for one request,
or `scripts/strehl-control.py` for launch, discovery, status, requests, and orderly
shutdown. The helper needs Python 3.9 or later and only the standard library.
It does not use Computer Use, a network listener, or a second command protocol.

## Launch a separate workspace

Use a dedicated state directory and a fresh publication filename within it.
Different catalog filenames in one directory still share presets and photograph
history; a separate directory keeps the automation workspace independent. The helper starts a
headless workspace by default and waits for bounded session publication. On
Windows it suppresses a console window and sends application logs to a sibling
`<session-file>.log`. The published JSON contains the process ID, build identity,
and path to the protected `session.json`; it contains no capability token.
Do not print or copy the contents of the protected descriptor.

```powershell
$exe = 'C:\path\to\packaged\Strehl.exe'
New-Item -ItemType Directory -Path 'C:\workspace\strehl-session-01' -Force | Out-Null
$session = 'C:\workspace\strehl-session-01\ready.json'
$ctl = @('scripts/strehl-control.py', '--exe', $exe, '--session-file', $session)
python @ctl launch --source 'D:\captures\stack' --output-dir 'C:\workspace\results'
$launchExit = $LASTEXITCODE
if ($launchExit -ne 0) { throw "Launch failed: $launchExit" }
python @ctl status
```

`launch` reports `session_published`, not completion of import or rendering.
Read snapshots to learn whether the workspace is ready. Source import,
stacking, metadata reading, and export may continue asynchronously.

If your execution environment ends child processes when their launcher exits,
use `launch --wait`. This prints and flushes the publication JSON first, then
keeps the helper attached until the owned application process exits. Use a
second command session for `snapshot`, `call`, and `shutdown`. The waiting
launcher then prints a second JSON line with `state: "process_exited"`, the PID,
and the actual child exit code; its own exit status is 1 for a nonzero child
exit. Its stdout is therefore a two-event JSON-lines stream, not one JSON
object. The publication timeout still bounds startup; the subsequent process
wait lasts until exit. A saved publication alone does not prove the process is
still alive.

```powershell
python @ctl launch --wait --output-dir 'C:\workspace\results'
# In another command session, with the same $ctl arguments:
python @ctl snapshot
python @ctl shutdown
```

Optional launch arguments:

| Helper argument | Meaning |
| --- | --- |
| `--source DIR` | Import this source directory. |
| `--grant DIR` | Share a directory for later imports; repeat for separate roots. |
| `--output-dir DIR` | Select the destination for generated results and reports. |
| `--catalog JSON` | Use a separate headless projects catalog; never the interactive desktop's catalog. |
| `--gui` | Explicitly launch a native window instead of headless mode. |
| `--wait` | Keep the launcher attached until its owned process exits; emit a final exit event. |

The default headless catalog is the publication path with its extension changed
to `.projects.json`. A headless process holds an exclusive catalog lease. Keep
outputs outside capture directories. Existing publication files are refused;
use a fresh filename for another launch. An existing isolated catalog can be
reused with `--catalog` after its previous process has exited. Do not remove an
active lease. A crashed process can leave its publication or lease behind;
verify that the process has exited before handling stale files.

The global `--timeout SECONDS` bounds launch or each control call (30 seconds by
default, at most 300). It precedes the subcommand. A timed-out launch leaves its
process running and reports the PID and log path. Do not launch duplicates until
you have inspected that state. A timed-out control request may already have been
accepted; the helper does not retry it.

## Read state and metadata

Snapshots return the complete `AgentReply`. The current revision is at
`data.revision`; the snapshot itself is at `data.result`. Source indices and run
indices are **zero-based**. Use `source_count`, `selected_frame`, projects, and
run lists to determine which imported source or saved run is available.

```powershell
$snapshot = python @ctl snapshot | ConvertFrom-Json
$snapshotExit = $LASTEXITCODE
if ($snapshotExit -ne 0) { throw $snapshot.error }
$snapshot.data.result
```

Pass request JSON through a UTF-8 file to avoid command-line quoting. This
PowerShell here-string example works without adding a UTF-8 byte-order mark:

```powershell
$requestPath = 'C:\workspace\strehl-request.json'
$requestText = @'
{"command":{"operation":"metadata","frame":0}}
'@
[IO.File]::WriteAllText($requestPath, $requestText, [Text.UTF8Encoding]::new($false))
python @ctl call --request $requestPath
$callExit = $LASTEXITCODE
if ($callExit -ne 0) { throw "Metadata request failed: $callExit" }
```

`metadata` reads a source from the currently imported bracket without changing
selection, settings, or the photograph. Its reply includes the captured
workspace revision, stack identity, source identity, full bounded audit report,
and JSON/log report paths in the configured output directory. Read its
`limitations` alongside AF and optical fields. Stored AF values are not
calibrated depth or evidence that the camera measured them freshly.

For a bounded source preview, the request is:

```json
{"command":{"operation":"preview","target":{"kind":"source","frame":0},"max_side":768}}
```

A preview reply preserves `image.mime_type` and base64 `image.data`. Decode that
image separately if needed. Preview limits and display transforms apply; a
headless preview is not evidence that the native desktop viewer was exercised.

`call --request -` reads one complete JSON request from standard input until
EOF. File input is preferable when PowerShell pipe encoding is uncertain.
The direct client caps input at 2112 KiB and rejects unknown fields, malformed
JSON, multiple JSON objects, and oversized requests. The bridge also caps the
serialized request envelope, so its transport allowance includes overhead.

## Make one deliberate change

Every mutation needs `expected_revision` from a fresh snapshot. The helper's
`call` command passes requests unchanged. It never fills a missing revision, retries a mutation, or
changes a request after a stale-revision error. Read the new state and decide
again if another action has changed the workspace.

For example, select a source using the current revision:

```powershell
$state = python @ctl snapshot | ConvertFrom-Json
$stateExit = $LASTEXITCODE
if ($stateExit -ne 0) { throw $state.error }
$change = @{
    expected_revision = $state.data.revision
    command = @{ operation = 'select_source'; frame = 0 }
} | ConvertTo-Json -Depth 8
[IO.File]::WriteAllText($requestPath, $change, [Text.UTF8Encoding]::new($false))
python @ctl call --request $requestPath
$changeExit = $LASTEXITCODE
if ($changeExit -ne 0) { throw "Source selection failed: $changeExit" }
```

The same command schema supports validated settings and development edits,
regions and annotations, stack start/cancel, source/run selection, project
organization, and exports. A queued result does not establish completion; poll
snapshots and inspect the requested output. The MCP tool catalog exposes the
full current schema and command descriptions.

Stacks also wait in a serial queue. `queue_stack` queues a catalog stack with
its saved recipe and starts it when no other stack runs; `remove_queued_stack`,
`move_queued_stack` and `resume_queue` manage it. The same render is never
queued twice behind itself. The snapshot key `activities` lists running and
waiting work with phase, counts and time left, the recent history, and
`queue_paused`. A queue restored after a restart waits for `resume_queue`;
`start_stack` still answers as before and is refused while a stack runs.

Imports are constrained to explicit grants. Commands do not grant arbitrary
filesystem access. Metadata cannot accept an arbitrary source or output path.
Exports use the configured destination and do not overwrite existing files.
There is no force-stop, automatic overwrite, automatic mutation retry, or
implicit selection of a source or run in this helper.

## Save and stop

```powershell
python @ctl shutdown
$shutdownExit = $LASTEXITCODE
if ($shutdownExit -ne 0) { throw "Shutdown refused or failed: $shutdownExit" }
```

`stop` is an alias for `shutdown`. This operation takes one fresh snapshot and
sends one revision-bound `shutdown` request. It applies only to an idle headless
workspace and saves before accepting shutdown. Active work, GUI sessions, or a
revision change can cause refusal. Inspect the state and decide what to do;
the helper does not cancel, kill, or retry on your behalf. A successful reply
means shutdown was accepted. Observe the published PID exiting to confirm
completion before reusing the catalog.

## Direct client and MCP

If you already have the protected descriptor **path**, the one-shot executable
client avoids the helper entirely:

```powershell
& $exe --control --session 'C:\path\to\session.json'
& $exe --control --session 'C:\path\to\session.json' --request $requestPath
& $exe --control --help
```

This direct client writes one full JSON `AgentReply` on stdout, including an
operation error or image. Usage, input I/O, and transport errors go to stderr.
Exit status is 0 for success, 1 for operation/I/O/transport error, or 2 for invalid
arguments/JSON input. `--help` is human-readable. The Python helper preserves
reply JSON and exit status; it wraps its own operational/transport errors in a
JSON error reply. Argument-parser errors still go to stderr with status 2.

MCP clients can instead start the same executable as
`Strehl --mcp --session <protected-session.json>`. Complete MCP initialization
before `tools/list` or `tools/call`. Available tools include `strehl_snapshot`,
`strehl_metadata`, `strehl_preview`, `strehl_probe`, `strehl_command`, and
`strehl_shutdown`. Both entry points use the same local bridge, request
validation, application command pump, and revision checks.

Headless mode runs the ordinary application state and CPU workers without a
native window or GPU renderer. It is useful for application control and result
inspection. It does not verify native rendering, layout, mouse interaction,
viewer commissioning, or GPU behavior. For those checks, launch a separate
interactive workspace and follow the [desktop build guide](desktop-build.md).

## Check the UI without opening a window

Native Capture is available through `launch --capture --capture-settings PATH`
and `screenshot --route capture --capture-settings PATH --png PATH` (or the older
`--capture`). The settings file
contains pairing credentials; do not include it in reports. Capture screenshots
read live state/preview but never initiate an exposure. `open_capture` selects
the tab in an existing session. Snapshots expose sanitized `capture` state,
preview dimensions, receiver status and completed-stack candidates.
`capture.in_progress` names the run being written (newest registered run with a
capture journal and no `result.json`). `capture.follow` reports stacking during
capture: the switches, and under `checker` the followed run, its `state`
(`running`, `finished`, `failed`, `stopped`), whether it only `observing` another
process's checker, and the counts `checked`, `passed`, `attention`,
`retake_positions` and `align_pairs`, plus `retaken` (planes taken again during the capture). Error
correction is the controller's `error_correction` state, set between stacks
with `capture_command` `{"op":"error_correction","enabled":true}`. `note` says what became of the last
finished capture. `capture.stored_raws` lists, per camera model, the newest
registered run with RAW receipts and its mean original and stored bytes per RAW
and storage encoding: the basis of the expected stack size beside the worst
case. The receiver status carries `archive_format` (2, or 1 when the receiver
writes format 1). `scripts/replay-capture.py` re-creates a recorded run file by file
at its recorded pace and can register it with a scratch receiver configuration.
Use it to exercise this without a camera.

`capture_command` carries a `request` with a unique `id`, the camera's
`camera_revision`, `plan_revision`, `sequence_id`, and a `command` such as
`{"op":"mark","start":true}`. The outer command still needs the application's
`expected_revision`. Use the revisions from a fresh snapshot; never fill them
in after the decision or automatically retry a mutation. `import_capture` with
an `index` from `capture.completed` rechecks and opens a completed receiver run.
`start_capture_receiver` starts/attaches the background receiver;
`set_capture_compression` changes its new-stack default via `compressed: true`
or `false`. Folder selection remains in the native UI. Closing a headless control
workspace does not stop the Pi or the background receiver.

`calibrate` runs the calibration pass of
[the capture calibration spec](proposals/2026-11-capture-calibration-spec.md)
(camera connected and idle, a host with `exposure_tiers`; no marks needed): a live
sweep of 33 lens positions over 6,000 units around the lens (or the marks' middle
until the lens has moved since it connected), read from the preview after each move;
a wait until the light has been on 150 s; a test pair at the sweep's busiest position
(the camera's shutter, at most 1.3 s, and five stops under) read by `strehl survey`,
whose body top sets the survey's long shutter; and the survey around the sweep's
range, read by `strehl survey`. It then puts the lens back at the busiest position and
the camera's ISO and shutter as they were. It moves the lens and takes RAWs; the
survey's are deleted once read. `stop_calibration` stops it (or a `calibrate_step`) at
once; what was measured stays. `capture.tools.calibration.pass` reports its `stage`
(`sweep`, `light`, `test`, `survey`, `return`, `done`, `failed`), `error`,
`stopped_in`, the sweep's `range`, `busiest` and kept tiles, the test pair's
`test_top`, the survey's `shutters` and `survey_depth`; `light_on_seconds` beside it is
how long this desktop has seen the light on. `prove` with `count` (1 to 10) takes that
many proof planes at the busiest position exactly as the plan stands, each a test run
of the base group (and of the highlight group when the plan has them) checked by
`strehl pixel-shift` and then deleted; a finished pass takes one by itself.
`capture.tools.calibration.proof` reports `running`, `error`, the `results` (verdict,
reason, `retake`, `local_px` against `limit_px`, `residual_px`, `seconds`) and their
`line`.

`calibrate_step` (with the start and end marked and the camera idle) takes
single RAWs across the marked range and measures how far detail stays sharp: on a
host with `exposure_tiers`, a survey at two shutters read by `strehl survey`
(also the subject, its depth and the exposure advice), else 25 RAWs at one
shutter read by `strehl focus-step`. The dense cluster (25 positions 8 units
apart) is centred on the marks and runs past them when the range is shorter,
inside the lens's known ends; when nothing is measurable a second survey at four
times the spacing follows. It deletes the survey and puts the camera's
pixel-shift mode back, also when it fails or is stopped (it then waits for the
host and reports the failure once four-shot is set again); the host leaves the
camera at the shutter it found. `capture.tools.calibration` reports its `stage`
(`switching`, `capturing`, `measuring`, `restoring`, `done`, `failed`) and, when
done, the `result` with `width` (focus units) and `suggested_step`. Applying the
step is a separate `settings` capture command. `measure_focus_step` with an
`index` from `capture.completed` measures a completed capture
(`capture.tools.focus_step`). `compact_capture` with an `index` and `apply: false`
estimates a completed capture's calibrated compaction and writes nothing
(`capture.tools.compact_estimate`); `apply: true` compacts it (not lossless;
`capture.tools.compact`) and is refused unless that capture was estimated first.

Capture commands also include `{"op":"focus","target":37308}` (absolute
normalized focus, while idle) and `{"op":"pixel_shift","shots":4}` (or `1`).
Use `pixel_shift_options` from state for capability detection. `initial_seconds`,
`raw_max_bytes`, `storage_required_bytes` and `storage_error` describe the current
plan. The controller independently checks fresh disk capacity before starting;
an accepted command is not evidence that an oversized stack began. Confirm its
phase, sequence ID and status message. Never replay a rejected or unanswered
shutter request automatically. Pairing keys and QR contents are excluded from
public snapshots.

The offscreen path paints the real workspace with egui and wgpu into a texture,
then saves the GPU readback as a PNG. It creates no native window or graphics
surface and sends no operating-system mouse or keyboard events. It requires a
working GPU backend; ordinary headless command control does not.

```powershell
python scripts/strehl-control.py --exe $exe screenshot --source 'D:\captures\stack' --metadata --output-dir 'C:\workspace\results' --png 'C:\workspace\metadata.png' --size 1440x940
$renderExit = $LASTEXITCODE
if ($renderExit -ne 0) { throw "Offscreen render failed: $renderExit" }
```

`--metadata` opens the native bracket explorer after import. The screenshot waits
for metadata and source previews, with a 60-second overall readiness/readback
limit. It refuses an existing PNG. A separate catalog is derived beside the
screenshot unless `--catalog` is supplied. Use a dedicated output/state folder.
The offscreen runtime cancels and waits for its owned metadata worker before
returning any render result. The 60-second render budget excludes that
cooperative cleanup. The helper waits up to 70 seconds for the process; if that
expires, it requests termination of only its owned process tree and waits to
reap the parent. Tree termination and the final parent wait each have a further
10-second allowance. A tree-cleanup failure is logged and reported as
unconfirmed descendant cleanup, even if a fallback parent kill succeeds.
A timed-out screenshot is never reported as successful and is not retried.
On normal completion the helper checks the PNG header, dimensions and final
IEND chunk. Its screenshot command does not require `--session-file`.
This is the SDR workspace rendering path; it does not validate native monitor HDR
presentation. The normal interactive `--screenshot` option remains available.

### Stations and themes

`--route` opens a Studio 2 station: `library`, `subject`, `capture`, `stack`,
`engine` (the Stack station's engine room), `develop` or `export`. It is applied
after the launch's document is opened, so `--open-run DIR --route develop`
renders that run's photograph in Develop. `subject:NAME` or `subject:ID` opens
that subject's page (the name is matched without regard to case); a plain
`subject` opens the open stack's subject, else the subject with the most renders.
`--theme graphite|instrument|lightbox` sets the theme for that render only; the
owner's Preferences (`studio.json` beside the catalog) are never written by
offscreen or headless runs. The older `--edit`, `--export` and `--projects` flags
are forwarded too and open the Develop, Export and Library stations.

More of the shell and the stations can be drawn without input:

| Option | What it draws |
| --- | --- |
| `--overlay projects` | the project tree drawer over the station |
| `--overlay activity` / `agent` | the Activity log or Agent drawer |
| `--overlay palette` / `preferences` | the command palette, or Preferences |
| `--plane-hold N` | the Stack station holding plane N (from 1) beside the photograph |
| `--capture-fixture plan` / `flight` / `glance` | Capture from a fabricated state (a synthetic subject); no camera host is reached |
| `--capture-fixture plan+survey` | The plan with a two-shutter survey's choices, highlight groups' row, an outline and the automatic selection's panel (pass it to the executable; the helper lists the three base fixtures) |

The helper's `screenshot` forwards all of them; `--route` alone is enough to
name what to render (no `--source` or `--open-run` needed for `library`,
`subject` or `capture`).

```powershell
python scripts/strehl-control.py --exe $exe screenshot --open-run 'C:\Users\me\Pictures\Strehl\strehl-run' --catalog 'C:\scratch\catalog.json' --route stack --plane-hold 150 --theme graphite --size 1680x1050 --png 'C:\scratch\stack.png'
$renderExit = $LASTEXITCODE
if ($renderExit -ne 0) { throw "Offscreen render failed: $renderExit" }
python scripts/strehl-control.py --exe $exe screenshot --catalog 'C:\scratch\catalog-2.json' --route 'subject:Blue weevil' --overlay projects --png 'C:\scratch\subject.png'
```

The executable accepts the same options directly with `--offscreen-screenshot
PNG`. Readiness waits for the photograph on Develop and Export, for the Library's
pictures and source checks, and on Capture for the station's state and the top
bar's rig lamp to agree. Use a copy of a catalog for every render: an offscreen
run may save the catalog it was given.

To draw Capture against a camera host without a camera, run the host's simulator
on this PC with scratch settings: `strehl-capture-headless --config host.json
--demo`, where `host.json` names `bind` `127.0.0.1:PORT`, a 48-hex-digit
`pairing_key`, a private `lan` such as `10.0.0.0/24` and scratch folders for the
journal and transfer state. Point a scratch `--capture-settings` file at
`http://127.0.0.1:PORT` with the same key and LAN, and a `receiver_config` path in
scratch. The simulator never opens a camera or transfers a RAW; `capture_command`
requests (`connect`, `focus`, `mark`, `settings`, `capture_positions` with `kind`
`test`, `start`) then change the state the next render shows.

Snapshots carry additive `route` (`key`, `station`, `drawer`, `focus`), `notices`
(the 16 newest, with `severity`, `source`, `read` and `resolved`) and `activities`
(`current`: what runs and waits, with `kind`, `state`, `phase`, `done`, `total`,
`eta_seconds`, `queued` and whether it can be stopped; `history`; `queue_paused`);
`status` and `error` keep their meaning. Catalog entries in `projects` have the
`kind` `Subject` for subjects and a `subject` for the subject a stack belongs to.
`create_subject` (`name`, `parent_id`), `move_node` (`id`, `parent_id`) and
`set_subject_meta` organise the Library; `import_stack` with a `parent_id` puts the
new stack there, named after its folder (a camera folder such as `100MSDCF` takes
its parent folder's name), and without one creates a project called `name`.
`export` adds the format's extension (`.jpg`, `.tiff`, `.png`, `.avif`) to a
`file_name` that has none.

## Export an independent-view bundle

An Independent views result keeps each photograph and focus map in its own coordinates. Open a completed result and choose **Export view bundle…** beside the view selector or in Export. Choose a fresh folder name. The app copies the bound photographs, linear masters, focus maps, original identity metadata and receipts. It preserves recorded original paths as provenance; it does not copy RAWs or developed edit versions. Selected-photograph export remains a separate action.

The control command uses an explicitly shared destination parent and a fresh child name:

```json
{"operation":"export_view_bundle","grant_id":"folder-1","relative_parent":"exports","folder_name":"insect-views"}
```

Read `export_capabilities.view_bundle` in snapshots for availability, busy state and the last completed destination. A queued response is not completion. `cancel_view_bundle_export` requests cooperative cancellation. Cancelled or failed copies may leave an incomplete folder, but the root `completed.json` is published only after every copied binding verifies. Choose another fresh destination for a retry. Reopen the exported folder with `import_completed_session`; original capture access is not required. Focus ordinal/width/support maps are descriptive within each view, not metric depth or a relative camera pose.

Use `select_session_output` with a zero-based `index` from the current session's output list to choose an aligned layer or independent view. The app rechecks the selected retained photograph/master/report hashes in the background, then saves the selected output in history. Poll `session.selection_busy` and `session.selected_output`; a queued response does not establish the switch. An invalid index, different saved directory or changed artifact refuses without changing the current photograph or saved recipe.
