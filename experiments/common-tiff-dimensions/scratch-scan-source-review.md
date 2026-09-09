# Independent source review: scratch scanner continuation

2026-09-08. SOURCE-CLEARED for the fixed private commission, subject to root's
separate committed release. No shim, scanner, control, wrapper, compiler,
fixture or product invocation occurred in this review. One explicitly
authorized metadata-only JSON size construction ran, documented below.
Reviewer is independent of shim, control and capture-wrapper authors.

Read continuation.md first. Build1 remains the committed operational failure;
its canonical-path mismatch did not retain the resolved spelling and its
cause is unknown. Neither the proposed correction nor later controls can
retroactively identify that cause or admit the failed build.

## Exact reviewed versions

| Source | Bytes | SHA256 |
| --- | ---: | --- |
| scratch-scan.py | 2991 | 3a1aa413fd4c9d37bccb973a419e3f4c03291903d44b7198c53992e7b00d3e46 |
| scratch-scan-rationale.md | 7745 | a89a2e7f57decf85fe0d9211e85e566af70ebd874556653b31d72cf8c4e7d817 |
| scratch-scan-controls.py | 19863 | 37c90e6fc52a0f27f7fe5b8c08092bbc1fcb3acc6181fee96911493bcf552f36 |
| scratch-scan-spec.md | 8590 | c65ef3fbe791c473eb3bdfeca0cd72a40b49f71a6efc3639d442d75566f19ab8 |
| scratch-control-capture.py | 11112 | 9a4dc0b4749a1b723603ba3a2b64607488f492ae2dae15a4656599262d2f1f51 |
| held M194h build-and-run.py | 40626 | b505a2fff0024691d98088c599f7f554c1543268de09c836a6bc1fe6c17b7410 |

The unexecuted first shim/rationale/control/spec drafts are preserved. Their
respective pins are2264B/be6da1fb1b69524565dc5bc7e074236c28777272ec1f938319dae3393e9c54fd,
6973B/c7643f6fd1c1f186fa8f38de3bf28784047049b3eba9b16478c940bc354d2354,
18063B/3881b77ac6f7a5f2167742ff5c793489ff22718bcacc4ba5d3e2e7ac0913d2b1
and6891B/8742e318ab18fb072ff7de917a00c8532ffcddfe4f0547497d987642839c71bd.
These drafts were not executed or silently replaced as evidence.

## Choices challenged and corrected before execution

The first shim inherited lexical's exists-gated ancestry check. I identified
a distinct source gap: a present dangling reparse/symlink can be false to
exists while visible to no-follow lstat. Strict resolve could then report
FileNotFoundError, which the tolerant scan would swallow as disappearance
before a canonical mismatch could reject it. An extant exists-true reparse
control had no power against that case. This was a review finding about the
proposed branch, not a diagnosis of build1.

The revised private scratch path checks every path/ancestor with lstat,
without an exists gate. Only lstat FileNotFoundError continues that ancestry
pass; permission and other errors propagate. Observed reparse attributes and
symlink modes refuse before strict resolution. The revised control group
separately injects false-exists/present-lstat reparse and symlink variants,
requires the actual lstat fault to fire and requires no victim resolve call.
Its false-exists witness is explicitly an independent adapter observation;
the corrected production source need not call exists. No real Windows link
or ACL condition is claimed by those injected rows.

I also found a read-budget gap in the deletion witness: raw read_bytes
preceded its byte charge. It now uses the existing cap11 same-buffer reader,
reserving read capacity before allocation. Stdout is also charged as written
bytes. The real deletion records actual preceding ancestry lstat visitation
through the drive anchor, then unlinks only the owned named11-byte victim
immediately before delegating to native resolve. These corrections precede
every private control execution.

## Source behavior and fixed commission power

The factory captures the original scan function and rejects closure free
variables. Its clone uses the same code object, copied globals and preserved
positional/keyword defaults; only the private owned binding changes. The
captured original function, owned and lexical remain unchanged. The exact-bool
false policy delegates to that original scanner. True policy is restricted to
the exact declared owned target, whose private path retains absolute ASCII
width, repository/target containment and declared-versus-resolved equality.
Canonical errors now retain both spellings. The inherited failure handler
still tolerates only FileNotFoundError for the tolerant scan.

The controls instantiate that actual factory against fresh private namespaces
containing the held need/lexical/owned/scan definitions. Scoped Path/walk
adapters retain native behavior except each named fault; no standard-library
global or original imported module is patched. Original helper identities
must match before/after factory construction and invocation.

The fixed population is16 result groups and17 planned dispatcher invocations:
the reparse group has two variants. A failed variant can stop its group, which
then cannot pass; later groups are still attempted. Do not describe this as16
scanner invocations or claim all17 occurred merely from the group count.

The main positive has actual7- and11-byte files. The scratch deletion must
occur during resolve after ancestry inspection, with strict=True, missing
victim witnessed, exactly one file-inspection disappearance and result1/7.
Restored positives require actual bytes and2/18 again. The false-policy
deletion uses the original scanner on an owned scratch fixture and must
propagate FileNotFoundError; a separate retained-root positive checks the
original non-strict resolver and false policy. The initially absent target
checks inherited initial-lstat semantics and does not exercise strict resolve.

Distinct extant canonical substitution must preserve both path spellings.
Injected permission errors at resolve and walk must retain class, errno and
marker. Injected nonregular metadata must hit the plain-file guard. Actual
18 bytes against17 must refuse capacity. Wrong root and integer1 policy must
refuse before traversal. False-policy canonical substitution must hit the
original canonical error, not the private scratch one. Every injected row
requires its fault seam to fire; a different error is not an accepted negative.

These controls can reject overly broad disappearance handling, wrong policy
dispatch and bypassed ancestry/type/capacity predicates. They do not certify
native reparse/ACL behavior, atomic snapshots, all possible filesystem races,
peak compiler storage or numerical output. Initial absence is an observation
at a scan, not proof the directory never existed. Already counted extents and
the inherited bounded disappearance-sample semantics remain unchanged.

## Capture wrapper and finite resource contract

The held capture wrapper checks its exact isolated Python command and source
hash, then the exact control/shim/spec extents and hashes. It creates only the
fresh external output and launches one fixed childless control interpreter,
with exact flags and the fresh fixed control output path. It imports none of
the product/controller/process-helper/scanner modules itself.

It polls only the retained direct-child handle. Timeout10 seconds or oversized
stdout/stderr triggers owned direct-child termination and a bounded one-second
wait. No peer process enumeration, PID reuse or tree kill is introduced.
Any attempted termination, missing exit, timeout, nonempty stderr or source
change prevents admission. Terminal exit unavailable is distinct from never
started. Failed cleanup is retained as such and cannot be reported as success.

Raw stdout/stderr and literal actual exit are retained. A successful capture
requires child exit0, no cleanup intervention, actual interval<=10, byte-exact
stdout/result.json identity, correct result schema/status, all16 groups passed
and source refs associated to the authenticated inputs. Root still must read
actual detailed rows and retain the wrapper's external whole interval/exit;
the wrapper's success string alone is not independent result verification.

Private controls retain their5CPU/10wall allocation,1MiB aggregate reads and
1MiB aggregate writes, including sources, readbacks, replaced progress and
stdout. The adapter metadata counter is capped8192; source/publication
bookkeeping is separately finite and is not falsely counted in that counter.
Each group<=2KiB, progress<=40KiB, final<=64KiB, with1CPU/2wall reserved before
final publication. Fixed fixture writes are at most11 bytes and two real
deletions target only their own victim; no recursive deletion is used.

The wrapper has a separate5CPU/10-overhead-wall,1MiB-read/1MiB-write slice.
Full wrapper wall<=20; only min(child interval,10) is subtracted from its
overhead wall, so cleanup beyond the child window remains charged. It reserves
1CPU/2wall before publication and checks after stdout flush. Child transport
bytes are additionally charged to this wrapper slice. Retain both full
allocations; no short sample authorizes another attempt.

Stream64KiB/16KiB ceilings are polled and checked at final reads; they are not
a hard no-overshoot filesystem interceptor. CPU/work fields are samples plus
explicit reservations, not exact terminated-process CPU. Post-write failures
can leave a positive-looking file with a nonzero outer exit, which must refuse.
This source clearance grants neither a control rerun nor a new build.

## Independently re-chosen combined-row capacity

Root authorized one metadata-only serialization before private execution.
I constructed the complete two-variant group at the fixed path, choosing the
larger traversal footprint: root resolve plus keep.bin before the rejected
victim. Each variant includes every emitted summary field and full bounded
error metadata. This produced1592B under2048, margin456; each variant770B.
It is a JSON shape result, not an actual scanner observation.

The following exact construction ran through local Python312 -I -S -B on
stdin; tool exit0 and command interval0.0845743 seconds. It imported no
candidate and created no fixture or process. It was not rerun.

```python
# Metadata serialization only: no scanner/shim/control import, filesystem fixture or invocation.
from pathlib import Path
import hashlib,json
root=Path.cwd()
victim=root/'experiments/common-tiff-dimensions/work/scratch-scan-controls-1/scratch/victim.bin'
message='scan file-inspection path='+str(victim)+': reparse/symlink path'
raw=message.encode()
def enc(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode()
variants=[]
for mode in ('reparse','symlink'):
 variants.append(dict(id='reparse-refuses',passed=True,mode=mode,policy=True,
  original_helpers_unchanged=True,fault_fired=1,walk_calls=1,
  resolves=[dict(path='scratch',strict=True),dict(path='keep.bin',strict=True)],
  actual_deleted=False,exists_false_calls=1,ancestry_lstats_before_resolve=1,
  exists_false_scope='explicit independent adapter witness; production need not call exists',
  evidence_kind='injected metadata/I/O response',
  expected_error=dict(type='ValueError',message=message[:400],full_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())))
value=dict(id='reparse-refuses',passed=True,variants=variants)
size=len(enc(value))
assert size<=2048
print(json.dumps(dict(schema='scratch-reparse-row-metadata-envelope-v1',
 bytes=size,cap=2048,margin=2048-size,variant_bytes=[len(enc(v)) for v in variants],
 path=str(victim),resolve_order='root plus keep-before-victim; includes maximum preceding regular-file resolve',
 classification='DERIVED metadata serialization, not actual scanner result')))
```

No remaining blocking source issue was found in the reviewed package. A
separate committed once-only control release and independent saved-result
admission remain root's next steps. Build2 integration and its source delta
archive require their own review; no old source/evidence is modified here.
