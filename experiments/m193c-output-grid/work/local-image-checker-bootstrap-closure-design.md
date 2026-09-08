# Checker bootstrap closure after saved audit2

SAVED-METADATA DIAGNOSIS / PROSPECTIVE DESIGN, 2026-09-08.
Author diagnosis, not independent certification. Metadata/source/docs only;
no numerical import, runtime discovery, array operation or control executed.

## Actual boundary

Audit2 stopped before private checks on
Python312/Lib/site-packages/win32/lib/pywin32_bootstrap.py in numpy_runtime.
No private/checker_runtime result exists. Phases stop at runtime-intake and
audit-refusal. The original worker remains REFUSED without runtime_modules;
its11/128/32 control/real/disjoint links await independent saved-data checks.

Audit2 final and stdout are both168790 bytes/SHA256
9440c3cd8b25b0d7cba5c938c923e2daf6597eafeeaf4dd785ffb7da3723592f.
The actual outer reports exit1,9.875 whole wall and empty stderr. The final
samples9.78125CPU/9.828000000001339wall, retaining full25CPU/30wall/3MiB.
Raw transport survived; data checks did not run. CPU is a sample, not a
complete terminal-process measurement.

## Structural mismatch

The actual plan has338 sources,2087 positive runtime files and17 empties.
The preparer walks Lib while pruning site-packages, then separately visits
only numpy, scipy, skimage, lazy_loader, packaging, imageio and PIL, plus DLLs;
it includes .py/.pyd only. numpy_runtime instead imports NumPy and visits every
current sys.modules entry, including modules loaded before reaching that call.

Neither _distutils_hack nor win32/lib belongs to those seven package roots.
Granting only the first observed omission therefore did not establish closure.
No pre-import snapshot establishes WHEN pywin32_bootstrap loaded. No
.pth/bootstrap source was opened.

Python documents automatic site initialization, executable .pth import lines
and site/user customization. Such hooks can run independently of intended
application imports. This is a plausible mechanism, not measured attribution
for this process. [Python3.12 site documentation](https://docs.python.org/3.12/library/site.html)

## Re-choice

A normal-startup collector covers pre-NumPy modules, but site hooks may already
have run; later NumPy imports remain outside that snapshot. -I alone removes user/script paths and ignores
PYTHON environment variables; it does not disable global site initialization.
[Python3.12 command-line options](https://docs.python.org/3.12/using/cmdline.html)

Prefer root's approved checker profile: -I -S -B and one fixed absolute
site-packages path appended directly after startup validation. -S suppresses
automatic site processing; use neither site.main nor site.addsitedir. -B
prevents bytecode writes, not necessarily reads of existing caches. -I ignores
PYTHONHASHSEED, so retain explicit sorted/canonical serialization and do not
claim an unchanged environment. These documented properties do not guarantee
that the installed NumPy will import without site hooks.
[Python3.12 startup option](https://docs.python.org/3.12/using/cmdline.html#cmdoption-S)

## One whole import capture, then a separate audit grant

1. Freeze a small collector using the pinned interpreter and absolute source
   under -I -S -B. Record argv, flags, executable/prefixes, sys.path, import
   machinery identities and non-PYTHON thread settings. Require isolated,
   no_site and dont_write_bytecode; retain the entire pre-import registry.
   Bound Windows ._pth/virtual-environment configuration witnesses; refuse
   incompatible path initialization. [Python path initialization](https://docs.python.org/3.12/library/sys_path_init.html)

2. Append only Python312/Lib/site-packages directly. Import exact NumPy once,
   with no saved patches or explicit array/projection/correlation operation.
   Retain the ENTIRE post-import registry. Built-in/frozen/no-file entries get
   explicit kinds/spec origins. File aliases index a deduplicated file table
   with reported/source/cache paths, extents/hashes and stable open identity.
   Source hashes do not prove which cached bytecode executed. Preload inspection
   helpers before snapshots; require unchanged full registry after inspection.
   Dependent native-DLL completeness remains outside scope.

3. Bound capture to4096 aliases,2048 file identities,1MiB registry JSON and
   128MiB total file bytes hashed. Original-plan files and new collector files
   form its read authority. Record all unresolved names/path metadata within
   the bounds before refusal; do not automatically read/grant an arbitrary
   new file. No truncation becomes a complete registry. This stage executes
   NumPy import initialization; it is not a claim of zero third-party code.

4. Independently review the completed capture and actual outer, every added/
   rebound identity and any unresolved entry. Freeze a separate checker-only
   manifest/grant. Incomplete or incompatible capture stops before the saved
   audit; there is no add-one-file/retry loop. Original producer authority and
   absent runtime_modules are unchanged.

5. The new audit uses the same isolated flags/path policy and NumPy identities.
   Compare complete pre/post-import registries with the held capture, allowing
   only the explicitly named new checker/collector source difference. Retain
   added, missing and rebound identities. Lazy modules loaded during data
   checking must already be in the held original package manifest; retain a
   final complete registry. Unknown late imports produce a bounded full
   discrepancy record and refusal, never a widened authority.

This is finite closure for one checker path, not arbitrary future imports.
Import capture can expose missing DLL setup or package assumptions after
suppressing site hooks. Failure means a separate reviewed compatibility choice,
not a silent fallback. The numerical checks and exact NumPy installation stay
fixed; only checker initialization is changed.

## Minimal source delta and power

Preserve all old files. Add one collector with startup/path checks, one NumPy
import, exact file witnesses and bounded publication. A new audit changes only
checker startup/authority/registry representation, retained-cost bindings and
fresh names. Its38 original numeric/reader/producer-runtime functions remain
unchanged. Subject_complete/scientific_contract_verified/producer runtime
completion stay false even if saved_data_checks_complete passes.

Predeclare metadata faults: wrong flags/extra path, missing/rebound alias,
wrong hash, truncation, zero-as-positive and changed original-plan reference.
Use captured metadata copies and canonical restoration. These test authority
predicates, not the physical action of interpreter startup. No extra sentinel
process is included; flags and registry are actual startup witnesses.

Success/refusal retains phase, paired CPU/wall samples, argv and registry
progress/unresolved list. Final/console use raw bytes; the compact console binds the final hash. Bound actual
outer/termination; a sampled CPU plus tail is not terminal process CPU, and a
canonical positive alone releases nothing.

## Separately budgeted phase

Root prospectively authorizes1600->1660 cumulativeCPU and160->168MiB metadata,
retaining1800wall/4GiB files. Prior remains1588.443678CPU,
1601.9278447999966wall,4140565273file bytes and149304339metadata bytes.
All prior subject/preparation/audit charges survive. The old ceiling's11.556322CPU remainder cannot fund another audit.

Proposed allocation: source/metadata preparations10CPU/20wall/2MiB
(split5/10/1MiB before capture and5/10/1MiB before audit); capture15CPU/25wall/
2MiB; saved-data audit25CPU/30wall/3MiB; independent outcome read and external
publication10CPU/15wall/1MiB. Total60CPU/90wall/8MiB. Source/review/outer files
and finite terminal reserves belong inside those lanes.

The derived full finish is1648.443678CPU,1691.9278447999966wall,
4148953881file bytes and157692947metadata bytes, within1660/1800/4GiB/168MiB
with11.556322CPU margin. Actual overshoot increases charge and stops release.
These are proposed limits, not a throughput measurement.

One source-frozen capture precedes independent review and a separate audit grant. Neither stage reruns the
subject, changes the saved populations or relaxes a scientific threshold.

