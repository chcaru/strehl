# Fixed weevil B4 comparator preparation

**SOURCE PREPARED / execution UNVERIFIED.** This allocation prepares one complete 299-source Helicon B observation with radius 4 and smoothing 4. Root alone executes it after the native jobs finish, using the authorized desktop context that succeeded for the flat comparisons. No application was launched, original RAW opened, TIFF payload decoded, activation attempted or native Rust source edited during preparation.

Prospective command from the worktree root:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/weevil-fine-comparator/run.py
```

The default fresh output is `outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-1`. Optional `--out` only names another nonexistent directory below this campaign's workspace outputs; there is no method, radius, smoothing, input or executable override. A failed attempt stays intact. The wrapper does not retry or dispatch another setting.

## Frozen workflow and preservation

The wrapper reuses the prior desktop runner's pinned Windows Job helper, executable, silent command and TIFF/JPEG handling. Its exact vendor arguments are `-silent -noprogress -i <manifest> -mp:1 -rp:4 -sp:4 -sort:asc -tif:u -save:<master> -o <saved-list>`. It compares these with the pinned prior B invocation after replacing only manifest/output paths and the prior radius 8 token. The explicit processing-parameter change is therefore radius 8 to 4. Installed application defaults remain subject to current-log review; historical settings not recorded by the prior run are not retrospectively proven identical.

All 299 existing native-developed TIFFs, DSC00001 through DSC00299, must match the pinned export receipt and the prior B input manifest by order, name, full-content SHA256 and byte count. New pre/post records also bind mtimes. No redevelopment or RAW-path consumer exists. The original export's fixed WB, tone and developer remain inherited through these exact TIFF bytes. Existing B8/C outputs and native masters are never written.

| Bound artifact | SHA256 |
| --- | --- |
| HeliconFocus.exe, same installed 8.3.11 binary | `29ca62df122163c1295e1e2a416a42acfdf52f20c83d0beed99c4af154d42089` |
| Native 299-TIFF export receipt | `461ecb3a8e44a82005ed6883718aa85276a74a2ebfca31fb0628809c4ba315a0` |
| Prior B input manifest receipt | `ee7a3ad62c89380c207bf2b18f86fc0d155c5588e14d7ba9fd282972ca0bd7af` |
| New run.py | `6c8ef9ef09c62d71fef49411271169fd03dc509b1c0cd2078c6e9f20159d304c` |

The prior B invocation, B/C completion receipts and process-control helper/harness are also pinned in source and checked before/after execution. Only the wrapper's generated artifacts are written in the worktree. Helicon retains its existing application-managed global log/cache behavior; the wrapper copies the current log into the fresh output and does not alter application settings or remove global files.

## Bounds and completion evidence

The owned vendor child tree has a 180-second wall, 5760-second observed CPU, 45-GiB committed-memory and 32-MiB stdout/stderr limit. Available physical RAM must exceed 49 GiB, preserving a 4-GiB host reserve; free output storage must exceed 4 GiB. An existing Helicon process causes refusal, never termination. The helper may close only its own job tree on a bound/failure. Root is responsible for serializing this against native heavy jobs. Pre/post TIFF hashing and output conversion occur serially outside the child-job wall/commit limits; these costs are included in the separately reported whole-wrapper time.

The current application log must differ from the pre-launch log, carry a UTC start time within this run and contain exactly the new command with its fresh output path. It must list all 299 sources in ascending order, then all 299 in reverse order, with the correct per-pass ordinals and rendering/clean-exit markers. A stale copied log cannot satisfy this check. License observations are retained without changing activation; OpenCL enumeration is not treated as proof of GPU execution. The application log is evidence of requested settings and processed inputs, not a quality metric.

Completion additionally requires clean terminal Job accounting, unchanged TIFFs and pins, a complete single-page RGB16 TIFF within the expected full-frame extent, and the original common ICC hash `238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b`. The complete master is retained. The full-size JPEG uses the already developed values with `(value+128)//257`, quality 98 and no chroma subsampling; the overview alone is resized. The earlier application's absent `saved-outputs.txt` is handled explicitly: its presence/absence is recorded, and current command/log/master evidence is checked independently.

**UNVERIFIED:** the wrapper has not run. The only executed preparation check was Python `ast.parse` on its text, without importing the wrapper. The bound application-log parser is prepared from the retained actual B log format, not commissioned by a new vendor run. No successful launch, log match, output, timing or photographic improvement is claimed.

Independent photo review must inspect the complete result before the same ten mapped native witnesses and compare B4 with B8, C and native masters. A changed vendor geometry requires explicit correspondence; reusing identical crop coordinates is not justified. Better existing hair separation must be weighed against real scale/gap preservation, glint growth, background traces, fringes and occlusion contours. The [brief](brief.md) fixes the one-setting rationale; this is neither an optimum search nor a pure native-merge attribution. Existing development cost remains separate in `outputs/raw-quality-2026-10-26/weevil-107-comparator/develop/completion.json` (212.156-second original wrapper; 211.109-second child). Those retained measurements and this new operational run do not establish an isolated competitive speed ranking.
