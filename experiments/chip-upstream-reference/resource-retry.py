"""One40GiB resource-only retry; frozen image recipe and original runner reused."""
from pathlib import Path
import argparse
import importlib.util
import os
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('upstream_frozen_recipe',HERE/'run.py')
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)
PRIOR = HERE/'run-2'


def prior_and_sources():
    process = r.read(PRIOR/'process.json')
    r.require(process['error'] == "ValueError('child committed-memory bound')"
        and process['limits']['committed_bytes'] == 24<<30 and process['terminal_job_accounting']
        and not process['cleanup_errors'] and not (PRIOR/'whole-stack.tiff').exists(), 'Wrong prior resource refusal')
    before, after = r.read(PRIOR/'inputs-before.json'),r.read(PRIOR/'inputs-after.json')
    r.require(len(before) == 299 and before == after, 'Prior all299 immutability proof differs')
    r.unchanged(r.read(PRIOR/'sources.json'))
    paths = [HERE/name for name in ('resource-retry.py','resource-decision.md','resource-review.md')]
    paths += [PRIOR/name for name in ('process.json','process.log','inputs-before.json','inputs-after.json',
        'bindings.json','invocation.json','prepared.json','sources.json')]
    return process, r.sources()+[r.ref(path) for path in paths]


def prelaunch():
    import psutil
    memory = psutil.virtual_memory()
    own = psutil.Process()
    allowed = {own.pid,*[parent.pid for parent in own.parents()]}
    watched = {'focus-stack.exe','heliconfocus.exe','strehl.exe','cli-tests.exe','cargo.exe','rustc.exe',
               'python.exe','pythonw.exe','python3.exe','python3.12.exe'}
    busy = [dict(pid=p.info['pid'],name=p.info['name']) for p in psutil.process_iter(['pid','name'])
            if p.info['pid'] not in allowed and (p.info['name'] or '').lower() in watched]
    return dict(available_bytes=memory.available,total_bytes=memory.total,
        minimum_available_bytes=48<<30,other_experiment_processes=busy,
        watched_process_names=sorted(watched),excluded_runner_and_ancestor_pids=sorted(allowed),
        passed=memory.available >= 48<<30 and not busy,
        scope='Immediate available-memory and named scientific/vendor process snapshot; no process is stopped')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=HERE/'run-3')
    parser.add_argument('--inventory',type=Path,default=HERE/'inventory-3')
    args = parser.parse_args()
    out = args.out.resolve()
    r.require(out == HERE/'run-3', 'Only the single fresh run-3 is authorized')
    out.mkdir(exist_ok=False)
    checked = r.checked_inventory(args.inventory.resolve())
    prior, bindings = prior_and_sources()
    r.save(out/'sources.json',bindings)
    executable = r.binary()
    rows,provenance = r.prepared()
    expected_previous = [{k:v for k,v in row.items() if k != 'mtime_ns'} for row in r.read(PRIOR/'inputs-after.json')]
    r.require(rows == expected_previous, 'Prepared input identities differ from prior run')
    r.save(out/'prepared.json',dict(inputs=rows,**provenance))
    before = r.scan(rows,True)
    r.save(out/'inputs-before.json',before)
    master = out/'whole-stack.tiff'
    command = [str(r.BINARY),f'--output={master.relative_to(r.ROOT).as_posix()}',*r.FLAGS,
        *[Path(row['path']).relative_to(r.ROOT).as_posix() for row in rows]]
    r.require(command[0] == prior['command'][0] and command[2:] == prior['command'][2:]
        and prior['command'][1] == '--output=experiments/chip-upstream-reference/run-2/whole-stack.tiff',
        'Resource retry changed the image recipe')
    chars = len(subprocess.list2cmdline(command))
    r.require(chars < 32760, 'Windows command line too long')
    binding = r.read(PRIOR/'bindings.json')
    binding.update(executable=executable,inventory=checked,prepared=r.ref(out/'prepared.json'),command_chars=chars,
        limits=dict(vendor_wall_seconds=900,vendor_cpu_seconds=18000,vendor_committed_bytes=40<<30),
        resource_only_retry=True,prior_process=r.ref(PRIOR/'process.json'),image_argv_unchanged_except_output=True,
        no_further_resource_retry=True)
    r.save(out/'bindings.json',binding)
    guard = prelaunch()
    r.save(out/'resource-prelaunch.json',guard)
    r.require(guard['passed'], 'Need at least48GiB available and no other named experiment jobs')
    start = time.perf_counter()
    try:
        r.jobs.job(command,{},out,wall=900,cpu=18000,gib=40)
    finally:
        after = r.scan(rows,False)
        r.save(out/'inputs-after.json',after)
        r.require(after == before, 'Prepared TIFF content or metadata changed across vendor run')
        r.require(r.binary() == executable, 'Staged runtime changed')
        r.unchanged(bindings)
        r.require(r.prepared() == (rows,provenance), 'Prepared provenance changed')
    result = r.views(master,out)
    r.save(out/'output.json',dict(complete_299_source_reference=True,prepared_inputs_unchanged=True,
        before_after_fresh_content_hashes=299,original_raw_read=False,original_metadata_not_rechecked=True,
        elapsed_vendor_postcheck_and_views_seconds=time.perf_counter()-start,views=result,
        resource_only_retry=True,prior_resource_failure=r.ref(PRIOR/'process.json'),
        photographic_review='pending',quality_claim=False))
    (out/'images.md').write_text('\n\n'.join(['# Complete299-source stock upstream reference',
        'One resource-only retry; unchanged8bit workflow/independent alignment; quality review pending.',
        f'[Complete vendor TIFF]({master.as_posix()})',f'[Native whole PNG]({(out/"whole.png").as_posix()})',
        f'![Whole-field overview]({(out/"overview.png").as_posix()})'])+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()
