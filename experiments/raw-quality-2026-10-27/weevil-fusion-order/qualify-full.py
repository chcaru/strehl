"""Qualify frozen-executable output after a proven source-only rustfmt mutation."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys

AREA = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fusion_qualification_helpers', AREA / 'run.py')
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)
h = r.h


def main():
    full = r.folder('full', 1)
    out = full / 'source-qualification'
    out.mkdir(exist_ok=False)
    r.terminal_clean(full / 'process.json')
    build = r.folder('build', 1)
    rust = r.read(build / 'rust-sources.json')
    differences = [v for v in rust if h.ref(v['path']) != v]
    target = r.ROOT / 'crates/strehl-cli/src/image_out.rs'
    assert len(differences) == 1 and Path(differences[0]['path']) == target
    expected = differences[0]
    before = h.ref(target)
    (out / 'observed-image-out.rs').write_bytes(target.read_bytes())
    command = ['git', '--work-tree=' + r.ROOT.as_posix(), 'show', 'HEAD:crates/strehl-cli/src/image_out.rs']
    proc = subprocess.run(command, cwd=r.ROOT, capture_output=True, check=False)
    assert proc.returncode == 0
    original = proc.stdout.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
    assert len(original) == expected['bytes'] and hashlib.sha256(original).hexdigest() == expected['sha256']
    preimage = out / 'bound-image-out.rs'
    preimage.write_bytes(original)
    copy = out / 'format-copy.rs'
    copy.write_bytes(original)
    format_command = ['rustfmt', '--edition', '2024', '--config', 'skip_children=true', str(copy)]
    fmt = subprocess.run(format_command, cwd=r.ROOT, capture_output=True, check=False)
    (out / 'rustfmt-stdout.log').write_bytes(fmt.stdout)
    (out / 'rustfmt-stderr.log').write_bytes(fmt.stderr)
    assert fmt.returncode == 0 and copy.read_bytes() == target.read_bytes()
    assert h.ref(target) == before
    exe = r.read(build / 'executable.json')
    h.check_refs([exe] + r.read(full / 'source-bindings.json') + r.read(full / 'prerequisite-bindings.json'))
    h.check_refs([v for v in rust if v != expected])
    receipt = r.read(full / 'output/receipt.json')
    assert receipt['test_executable'] == exe
    assert receipt['status'] == 'COMPLETE299_WEEVIL_FUSION_ORDER_PAIR'
    assert receipt['complete'] and receipt['source_count'] == receipt['native_decode_count'] == 299
    assert receipt['indices'] == list(range(299))
    for key in ('known4_after_finish_exact','admission_exact','writer_camera_path_parity_exact',
                'baseline_complete_golden_exact','baseline_material_metadata_exact',
                'all299_original_bytes_and_metadata_unchanged','all_bound_inputs_unchanged'):
        assert receipt[key] is True
    assert not receipt['quality_claim'] and not receipt['photographic_admission']
    qualification = dict(status='FROZEN_EXECUTABLE_FULL_OUTPUT_SOURCE_FORMATTING_QUALIFIED',
        original_wrapper_exit=1, original_wrapper_source_check_failed=True,
        scientific_job_clean=True, executable_unchanged=True, original_rust_source_set_unchanged=False,
        changed_source=before, build_bound_source=expected, exact_bound_source_recovered_from_HEAD_CRLF=True,
        isolated_rustfmt_reproduction_byte_exact=True, commands=[command, format_command],
        expected_exits=[0,0], actual_exits=[proc.returncode,fmt.returncode],
        runtime_source_reading=False, other_build_sources_unchanged=True,
        rationale='Only image_out.rs source formatting changed; the executable was not rebuilt and its exact hash remains bound. Complete baseline pixel/material replay passed. Failed wrapper status is preserved.',
        photographic_improvement_claimed=False)
    h.save(out / 'qualification.json', qualification)
    h.save(full / 'completion.json', dict(status=receipt['status'], sources_unchanged=False,
        original_wrapper_failed=True, qualified_frozen_executable_output=True,
        qualification=h.ref(out / 'qualification.json'),
        reports=[h.ref(q) for q in sorted((full / 'output').rglob('*')) if q.is_file()],
        photographic_improvement_claimed=False))
    print(json.dumps(qualification))


if __name__ == '__main__':
    main()
