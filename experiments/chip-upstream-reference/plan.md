# One complete stock upstream chip reference

Prepared September26. Root executes after independent source review; no author
execution. First inventory the existing upstream executable by exact SHA256,
`--version` and `--help`. Its path is
`C:/dev/strehl-out/V-LINEAR2/fs15/focus-stack/focus-stack.exe`; required SHA256 is
`e256176d70bec54bb51a448b2adc452e7f49d21bc5042b40689a3257bbfdee9e`.
V-SPEED§1 records self-reported1.3-42-g0cd289e, despite the fs15 directory name.
Inventory must succeed and show every proposed flag before a full run. Root's
initial direct invocation failed0xC0000135 because that old folder lacked
libprotobuf.dll. Root staged the same executable and complete cached30-file
runtime into this experiment's program-1; all28 common executable/DLL files match
the old bundle exactly. Two cached files are additional: libprotobuf.dll and
libprotoc.dll. The libprotobuf.dll SHA256 is
36e7e36b191edf2ef74eb9063146b8b91c47b0c37dcdeb100b2562fb075657b1.
The libprotoc.dll SHA256 is
c68420e9f91ec6fb257e162c5fd031584136035a098ebec2332dc0acd350b5b6.
Program-manifest.json retains identities and actual successful version/help text:
expected exit0 for version, exit1 for help, output on stderr. Root's initial
helper checked stdout and failed after successful staging/inventory; its channel
guard was corrected without recopying or changing experiment data. The runner
checks combined stdout+stderr, all runtime files and flags. It neither recopies
the bundle nor reruns inventory executables. No installation/global PATH change.

Use the exact ordered299 prepared TIFFs from chip-competitor/run-1, excluding
golden.tiff. Developer receipt97f198664496c18ebb7723450e240163983cf00a5499e1db0695bdd0f4c3bf9c
binds full7032×4688 RGB16 inputs, decoder/MHC/WB/matrix/tone and original source
identities. Read original identities only from receipts; do not open or restat
RAWs. The original-order receipt has path/bytes/mtime only; original SHA256 values
come from the pinned developer receipt and are format-checked, not independently
corroborated by that order receipt. Recheck all299 TIFF headers/ICC and fresh content hashes before launch;
repeat all299 content hashes and metadata after any vendor outcome. This scans
approximately118GB across both passes and intentionally is stronger than a
retained-hash-only check. No source resize, recolouring or intermediate stack.

One fixed invocation: `--no-whitebalance --no-contrast --threads=8 --batchsize=4
--no-opencl`, with explicit ordered repository-relative input paths and
`--output=<owned whole-stack.tiff>`. Require the encoded command length below
32760characters. Leave default neighbour alignment and common-area cropping;
these are declared vendor workflow confounds, not endorsement of chaining or
new strehl geometry. V-SPEED§6 records this build lacked an OpenCL/CUDA backend;
the explicit disable keeps this experiment on CPU. No save-steps or per-source
output request. Vendor job cap900s wall,18000s CPU,24GiB committed;8threads/batch4.
The content scans occur outside that vendor job and their time is disclosed.

This upstream stock operator is distinct from our rejected boundary-CFA port:
it owns its grayscale transform, consistency/reassignment and RGB workflow.
It is also distinct from Helicon. Its8bit input/transform/output limitation
remains explicit: providing RGB16 TIFFs does not make the vendor pipeline16bit.
No claim of shared sampling, native CFA arithmetic, held geometry or pure merge
comparison. The sources are unaligned CA-off while native Current uses held CA;
tone precedes the external merge. Any output crop/dimensions/ICC are recorded.

Preserve the complete vendor8bit TIFF and pixel-exact whole PNG; make only the
overview smaller. No inferred ICC is silently attached if the vendor omits it.
All review must include the whole output before any local inspection. No extra
synthetic quality screen, tuning, retry, automatic promotion or algorithm port.

Root's inventory-1 refused mechanically before any vendor launch: the runner
incorrectly required29 shared runtime files, while the actual manifest has28
shared plus these two additions. The failed inventory and its bindings are
preserved. The correction asserts the actual28-count and both addition names;
it does not change the executable, inputs, full recipe, resource caps or image
requirements. No binary or stack was run by the author during this repair.

Inventory-2 passed. Full run-1 then refused before image reads or a vendor launch:
prepared() incorrectly expected a SHA256 in the original-order receipt. Its actual
path/bytes/mtime schema is now respected; exact developer-receipt hash, original
hash format, path, size and all299 ordinals remain checked. The failed run-1 is
preserved. Root authorized only metadata prepared()/binary() checks for this
repair; these do not read TIFF pixels or execute the vendor. A new source-bound
inventory is needed after the runner correction; the full recipe stays fixed.
MEASURED after correction: importing run.py and invoking only prepared() and
binary() returned METADATA_ONLY_OK,299 rows from DSC00001.tiff to DSC00299.tiff,
developer97f198664496c18ebb7723450e240163983cf00a5499e1db0695bdd0f4c3bf9c and
executablee256176d70bec54bb51a448b2adc452e7f49d21bc5042b40689a3257bbfdee9e.
No TIFF was opened or vendor process launched by that check.

Root commands after corrected source freeze:

```text
python -I -B -X faulthandler experiments/chip-upstream-reference/run.py inventory --out experiments/chip-upstream-reference/inventory-3
python -I -B -X faulthandler experiments/chip-upstream-reference/run.py full --inventory experiments/chip-upstream-reference/inventory-3 --out experiments/chip-upstream-reference/run-2
```

The second command remains conditional on inventory success and root's explicit
execution decision. Neither command has been run by the author.
