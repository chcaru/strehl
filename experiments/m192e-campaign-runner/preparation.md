# M192e metadata preparation and release recipe

SOURCE ONLY. This is an additional preparation helper; it has not run and no
actual plan, preservation manifest, process or product output is created by
writing these instructions.

After the full source package is independently reviewed, root freezes prepare.py,
this recipe, all required controller/reader/helper sources and the independent
reviews. Invoke the selected Python with -B from the repository root. Supply:

- --source PATH BYTES SHA256 once for every exact held source and review. The
  embedded REQUIRED list is the minimum; it includes this preparer and recipe.
  Each triple must be a positive ordinary owned file, unique by resolved path.
  Additional dependencies remain root's release responsibility.
- --review PATH once per relevant independent review, each already supplied by
  an exact source triple. The helper binds review bytes; it does not interpret
  their prose as an automated approval.
- --campaign-id a root-selected canonical UUID.
- --output-name a fresh direct-child name starting rehearsal-.
- --preparation-name a fresh direct-child name starting preparation-.

The metadata preparation itself is limited to10 process CPU seconds and20 wall
seconds, including an explicitly charged0.25CPU/0.5wall publication allowance.
The whole family of its three emitted JSON files must be at most256KiB, with
each at most128KiB. Root must retain the actual preparation command, stdout,
exit and whole external wall interval; complete metadata creation is not
permission to launch the subject. A prepublication sample is not complete CPU;
the final allowance is reserved bookkeeping, with external wall required to
cover final writes/exit. An unexpected failure can leave an exclusive partial
preparation directory; retain it and refuse, never reuse or overwrite it.

The embedded old pins select exactly the completed M192d seven-record package,
its independent PASS, source-freeze and before/after input lists. The exact
33 filenames and order DSC00001.ARW through DSC00033.ARW must match both
unchanged saved lists and the held protocol directory. The preparer does not
open any RAW or TIFF payload and imports no subject module. It reads the
existing executable and sidecar only as opaque bytes for identity; it never
loads or executes them. Every emitted output-image FileRef is explicitly the
inherited expected identity from the actual old records and independent review,
not a new preparer observation of those TIFF bytes.

The helper rejects a changed old metadata digest, missing/duplicate/empty
source, unbound review, changed protocol/binary/sidecar, different canonical
33-input population, wrong old index or output identity, reused destination or
oversized preparation. No alternative binary, sidecar, input subset, output
record, schedule or gate is selected in response.

Successful preparation writes only:

1. preserved.json: exact seven ordered {index,record,output} rows.
2. plan.json: the existing closed eight-key m192e-rehearsal-plan-v1, bound to
   the same33 inputs, actual observed old positive02, executable, sidecar,
   complete source closure and fresh output root.
3. preparation.json: source/argv, exact plan/preservation refs, actual sampled
   preparation work and fixed allowance, plus the complete future launch argv
   and saved-artifact verification argv.

The final source/input recheck finishes before the publication sample. The
preparer hashes its exact emitted plan bytes and inserts that SHA into the
launch argv; no placeholder remains in the launch command. Its verification
argv deliberately contains ACTUAL_OUTER_SHA256, to be replaced only by the
actual produced outer receipt hash after the subject has exited.

Root independently checks the preparation, then may explicitly release the
held launch_command once. Execute launch.py rather than run.py directly, and
retain an external receipt for the entire wrapper with actual command, exit,
stdout and whole wall interval. The helper creates the fresh rehearsal root
through its owned parent and a separate fresh sibling ending -outer. The
wrapper's outer.json is subject process evidence, not itself a campaign
certificate. After exit, run the held verification command with the actual
outer SHA and retain its result plus the independent saved-output audit.

The three new calls remain exactly off/on/placebo N33 W8. The worker actually
hashes the seven old TIFFs and33 selected RAW inputs before and after, performs
the existing fixed sampler/output checks and records every maximum gap/drop/
checkpoint count. No old completed control, seven-run rehearsal or full133
campaign is repeated. Sampling failure stays a failed integration outcome;
durable INCOMPLETE recovery and canonical success alone never authorize
completion. This metadata helper neither relaxes limits nor launches a retry.
