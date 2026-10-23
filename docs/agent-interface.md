# Work with an agent in Strehl

Strehl exposes the open photograph and its workspace through **Model Context
Protocol (MCP)**. Your agent runs in its normal host—Codex, Claude Code, Copilot
CLI, or another local MCP client—and operates the same workspace you see.
Strehl does not contain a model, charge for inference, or read the host's login
credentials.

Enable the connection in Strehl's **Agent** pane. Copy its session descriptor
path, then configure one of the hosts below. Keep Strehl open while working.
Disconnecting in Strehl revokes that session; enabling again creates a new
descriptor. The connection is local standard I/O with a private local mailbox,
not an HTTP service.

For an explicitly enabled launch, `Strehl --agent` opens the Agent pane and
creates a session. Ordinary launches leave agent access off. `--edit` opens the
Edit pane without enabling an agent.

## Connect your existing host

Replace the executable and session paths with the paths shown by your copy of
Strehl. Quote paths containing spaces. On macOS, the executable is
`Strehl.app/Contents/MacOS/Strehl`; on Linux, use the downloaded AppImage.

### Codex

```text
codex mcp add strehl -- "C:\Apps\Strehl.exe" --mcp --session "C:\...\session.json"
```

Sign in to Codex normally. ChatGPT sign-in uses the host's subscription access;
API-key sign-in uses that host's API billing. MCP configuration does not change
the selected account or billing mode. Check the connection with `codex mcp list`
or `/mcp` in the CLI. See the official [MCP setup](https://developers.openai.com/codex/mcp/)
and [authentication documentation](https://developers.openai.com/codex/auth/).

### Claude Code

```text
claude mcp add --transport stdio strehl -- "C:\Apps\Strehl.exe" --mcp --session "C:\...\session.json"
```

Use your normal Claude Code login and its eligible plan or configured provider.
Check with `claude mcp get strehl` or `/mcp`. Existing server entries may need
removing and adding again when you enable a new Strehl session. See the official
[local MCP configuration](https://code.claude.com/docs/en/mcp) and
[authentication options](https://code.claude.com/docs/en/authentication).

### Copilot CLI

```text
copilot mcp add strehl -- "C:\Apps\Strehl.exe" --mcp --session "C:\...\session.json"
```

Alternatively use `/mcp add`, choose **STDIO**, and enter the executable and
arguments. Check with `copilot mcp list`. Your existing Copilot account,
entitlement, quotas, and organization policies still apply. See the official
[Copilot CLI MCP setup](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers).

### Other local hosts

The equivalent server configuration is:

```json
{
  "mcpServers": {
    "strehl": {
      "command": "C:\\Apps\\Strehl.exe",
      "args": ["--mcp", "--session", "C:\\...\\session.json"]
    }
  }
}
```

The outer configuration key varies by host. A local standard-I/O client must
run on the same computer and have access to the session directory. A remote
cloud agent does not gain access merely by receiving this configuration.

This implementation negotiates MCP `2025-11-25`, with support for the
`2024-11-05`, `2025-03-26`, and `2025-06-18` initialization flows. It does not
implement the newer handshake-free `2026-07-28` protocol era. A client that
supports only that era must enable legacy compatibility. References:
[stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports),
[initialization](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle),
[tool results](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).

## Circle, inspect, change, compare

An example instruction to the agent:

> Inspect the circled mineral highlight. Show me the same region in the final
> image and the strongest contributing source frames. Separate source clipping,
> alignment uncertainty, and merge fallback in your explanation. Suggest a
> reversible adjustment, apply it, then compare the result in that region and
> in a nearby unaffected region.

The useful loop is:

1. **Observe:** read a workspace snapshot and the current annotations.
2. **Inspect:** request a region's bounded diagnostics and matching image crops.
3. **Propose:** leave a visible suggestion tied to the region, or apply a
   validated change when the human has asked for that action.
4. **Try:** change development controls or start a new stack with different
   settings. The original capture files are never edited.
5. **Compare:** inspect the completed output, the same region, and an unaffected
   control. A queued operation is not a completed render.

The human can circle and edit without an agent. The shared region geometry and
development recipe are also available to the agent, so a region does not lose
its identity when the viewport pans or zooms.

## Interface

| Tool | Purpose |
| --- | --- |
| `strehl_snapshot` | Current revision, projects/stacks/runs, settings, development recipe, annotations, job state, and available evidence. |
| `strehl_probe` | Bounded source admission, saved confidence ranks, and linear-light statistics for an output-image region. |
| `strehl_preview` | A bounded PNG of the final image, a source, or an available diagnostic, optionally cropped. |
| `strehl_command` | Validated workspace operations: select, annotate, adjust, save/restore edit versions, start/cancel, export, undo/redo, organize, import from shared folders, and suggest. |

Every mutation includes `expected_revision` from a fresh snapshot. If the human
or another agent has changed the workspace, Strehl rejects the stale command.
Read again and reconsider the change rather than silently retrying it. Source
frames and run indices are zero-based in the interface.

Regions use normalized coordinates in the **entire saved output**, not pixels
in the visible viewport:

```json
{
  "expected_revision": 12,
  "command": {
    "operation": "annotate",
    "annotation": {
      "id": "highlight-edge",
      "label": "Bright boundary",
      "kind": "bright_spot",
      "region": {
        "kind": "ellipse",
        "center": [0.42, 0.61],
        "radius": [0.035, 0.05]
      },
      "note": "Compare source clipping and admitted detail before changing exposure."
    }
  }
}
```

Available issue kinds are `occlusion_halo`, `bright_spot`, `alignment`, `noise`,
`colour`, `exposure`, `focus_gap`, and `other`. Geometry can be an ellipse,
rectangle, or polygon. Diagnostic crop metadata identifies the coordinate
space: a camera source must not be presented as geometrically registered when
that transform is unavailable.

`set_settings` accepts a bounded patch for the existing stack controls.
`set_adjustments` replaces manual controls in an explicit scope: `region_id`
names an existing enabled region; null or omitted means the whole photograph.
Omitted adjustment controls reset to zero. Geometry, source repairs, measured
Adaptive fields, and HDR settings remain intact.

`set_develop` accepts the shared, versioned development recipe, including global
and regional controls and bounded `spatial` fields. Unknown fields are rejected.
Those measured fields belong to the current photograph: round-trip them from
the snapshot unchanged instead of inventing coefficients or copying them to
another photograph. A nonempty spatial list replaces that list. For compatibility
with older clients, an omitted or empty list **preserves** existing treatments.
Use `clear_adaptive` with the same explicit `region_id` scope to remove one
treatment; it is undoable and retains the manual controls. Removing an annotation
also removes its associated treatment. A legacy replacement that would orphan a
treatment fails with an actionable error. Preset imports report unsupported Adobe
profile operations as warnings. Arbitrary code and unknown settings are rejected.

A region's optional `source_range: {"first": 12, "last": 18}` limits its repair
to an inclusive range in filename order. This is a merge instruction: **restack
after changing it**. The master records which repairs were baked in; export
refuses an edit recipe whose enabled repair ranges, shapes, feathering, or
ordering no longer match that master. A tone-preview update is not evidence
that a source-range repair has run.

Preview requests are limited to 1024 pixels on the longest side. Region probes
return at most 32 source records. The fixed request limit is 2112 KiB, including
a recipe of at most 2 MiB and 64 KiB for the envelope; the reply limit
is 8 MiB. Long render/export work returns a queued state and proceeds through
the application's normal background jobs. Snapshots list up to 256 catalog
objects and the latest 32 runs per object; truncation and full run counts are
reported explicitly.

## Photograph edit versions

`save_edit_version` saves the current recipe as a named, immutable version of
the open photograph. Its `name` must contain 1–120 characters (at most 384 UTF-8
bytes), without control characters:

```json
{
  "expected_revision": 12,
  "command": {"operation": "save_edit_version", "name": "Softer reflections"}
}
```

The reply is `queued`. Poll `photo_history.busy` and check `photo_history.error`
before treating the operation as complete. `photo_history.versions` lists the
current photograph's newest versions first, up to 64; each includes its `id`,
name, owner, creation time, and source identities. `photo_history.exports` lists
up to 128 deliveries for that photograph, newest first, with their version ID,
destination, encoding settings, byte count, and SHA-256. `list_limit` states
these bounds; the arrays are not the entire project library. `status` is a
human-readable operation message.

Use a returned version ID with `restore_edit_version`:

```json
{
  "expected_revision": 15,
  "command": {
    "operation": "restore_edit_version",
    "id": "0123456789abcdef0123456789abcdef"
  }
}
```

Replace that example ID with an actual saved ID and use a fresh revision.
Restore opens the version's photograph if needed, validates its recorded file,
decoded source and loaded-pixel identities, then replaces the recipe through
the shared Undo journal. Before a different recipe is restored, the current
recipe is saved as a backup version. Changed or missing source evidence causes
an error; versions are not portable presets. A newer edit or photograph change
during restoration prevents stale work from replacing the current view.
Saving a version alone does not render a delivery; `export` records the recipe
version and resulting file together.

## Export delivery

`export` defaults to the folder beside the current photograph's TIFF, matching
the human Export pane. An alternate chosen in **Export → Destination** is
remembered for that photograph. The snapshot reports the resolved folder in
`export_capabilities.destination`; null means no photograph destination exists.
Changing the destination invalidates the agent revision. `file_name` is a name,
never an arbitrary path. The original `file_name` and
`format` command remains valid. Optional delivery fields now match the app:

`busy.export` includes version preparation and delivery recording as well as
encoding. `photo_history` reports bounded version/export metadata, status and
errors. Only a successfully published and recorded file is a completed delivery.

```json
{
  "expected_revision": 12,
  "command": {
    "operation": "export",
    "file_name": "specimen.avif",
    "format": "avif",
    "color_space": "rec2020",
    "hdr": true,
    "quality": 100,
    "speed": 6
  }
}
```

Formats are `avif`, `tiff`, `png`, and `jpeg`; color spaces are `srgb`,
`display_p3`, and `rec2020`. Defaults are Rec.2020, quality 100, and AVIF speed
6. Omitted HDR defaults to true for a scene-linear AVIF export and false
otherwise. An explicit HDR request for SDR input, or a format other than AVIF,
is rejected. The queued reply contains resolved settings; completion remains
observable through `busy.export`, `export`, and `error` in the snapshot.
`export_capabilities.hdr_available` reflects the current photograph.
Existing files are never overwritten. JPEG/AVIF remain lossy even at quality
100; TIFF/PNG are lossless and ignore codec quality/speed.

## Adaptive development and display evidence

The command `{"operation":"adaptive_develop","strength":1.0}` queues a bounded
scene-aware development analysis. Poll `adaptive.analyzing` in `strehl_snapshot`;
completion includes measured statistics, diagnosis, control changes, compact
spatial-treatment metadata, limitations, and any stale-result error. The complete
current recipe is available once under `development`, without duplicating its
coefficient arrays in the analysis. Strength is finite
and between 0 and 1. When the current treatment is still attached, another amount
uses that same frozen analysis without compounding edits. Changing the photograph
or recipe while analysis runs prevents its result from overwriting newer work.
The same Undo journal is used as for human development changes.

The optional `intent` is `"balance"` by default, preserving strength-only clients.
It builds image-dependent spatial light and color curves for `selected_region`
from the snapshot, or the whole photograph when that field is null. Ordinary
Light/Color sliders remain unchanged; the measured field is stored in the recipe.
`{"operation":"adaptive_develop","strength":1.0,"intent":"highlights"}`
uses the human's **Balance highlights** action and requires a selected, enabled
region. It compresses existing bright light and reports stored-white/variation
limits; it cannot recreate clipped texture. Annotating a region selects it.
Selection changes invalidate the agent revision, so obtain a fresh snapshot
before either action. An unknown intent is rejected before reaching the app.
Cached Amount belongs to both the selected region and the intent; switching
between balance and highlights starts a new analysis instead of reusing the
other treatment. `adaptive.analysis` includes its scope, intent, before/after
sampled measurements and diagnosis. The after measurements describe full amount,
not the current interpolated amount.
Adaptive is unavailable while Magic selection is pending. Starting a newer Magic
selection invalidates an older Adaptive analysis even if that selection is later
cancelled; worker completion order cannot choose which operation wins.

Snapshots also expose `display` with the actual visible region, physical-pixel
demand, detail sampling stride, publication identity, worker/cache counters, and
native display capability. `frame_performance` contains the latest bounded CPU
frame observations, including renderer submission time reported by eframe.
Repeated layout passes are summed under one egui frame ID; the framework CPU
value belongs to the preceding frame and is sampled only once.
`photo_view.uv` identifies the final photograph's actually painted visible crop;
it is null when that process photograph is not visible. Audits can use this
to distinguish a requested navigation action from a changed image view.
These are CPU costs for rendered frames, **not** GPU timings, refresh rate,
input latency, or proof of what an HDR monitor physically emitted.

## Evidence and limits

Admission samples indicate where a frame passed a particular detail-band gate.
They are **not exact RGB ownership**, especially after reconstruction and
colour processing. An observation-balance output is not a calibrated
probability that a pixel is sharp. A missing diagnostic must be reported as
unavailable, not inferred from a thumbnail.

After a regional source repair, retained admission maps describe the original
global merge **before repair**. Probe responses identify this domain and list
the actual repair regions and allowed source spans baked into the master.
They do not claim a per-pixel ownership map for the repaired result. Linear
region statistics precede the display baseline; their reference is named
explicitly: sensor normalization for scene-linear masters, or imported SDR
white for an older display-referred TIFF.

The saved confidence map is computed against the reconstructed run output,
including regional source repairs. Its folded rank ranges from 0 (one-sided)
to 1000 (balanced), with ties also capable of producing zero. **Neither end is
a quality grade.** Probe histograms preserve missing observations separately;
confidence PNGs show them as transparent. These ranks describe the saved merge,
before later development edits, and omit source identity and observation count.

The interface makes existing evidence accessible. It does not by itself
establish that an agent's proposed edit improves the photograph. Inspect the
complete image, then matched native-resolution regions, including a region
that should remain unaffected. Capture advice should distinguish measured
evidence from a hypothesis that needs a new bracket.

The local bridge permits operations in the enabled workspace. It has no shell
endpoint and no arbitrary file-read endpoint. Imports resolve only within
folders explicitly shared by the human, including a canonical path check
against symbolic-link/junction escapes. Export accepts a file name in the
app's selected destination and does not overwrite an existing file.

The session descriptor is a capability: keep it private. Unix sessions use
owner-only permissions; Windows sessions use a protected owner-only ACL.
Processes already running as the same operating-system user are inside that
trust boundary. Selecting image/diagnostic tools gives the host the requested
content; the host's own model data policies then apply.

## In-app conversation

This version uses the host for conversation and account authentication, with
annotations, edits, suggestions, and results visible in Strehl. A future
embedded conversation can use a vendor's supported app integration where that
vendor permits it. There is no universal subscription inference API, and this
feature does not reuse browser cookies, extract host tokens, or impersonate a
vendor client.
