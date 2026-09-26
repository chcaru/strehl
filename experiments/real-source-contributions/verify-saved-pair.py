"""Verify saved successful Rust runs after a metadata-only cross-build wrapper refusal."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,sys
import numpy as np
import tifffile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('saved_real_trace_runner',HERE/'run.py')
r=importlib.util.module_from_spec(spec);sys.modules[spec.name]=r;spec.loader.exec_module(r)
c,f,g=r.c,r.f,r.g

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def file_ref(path):return c.ref(path.resolve())

def actual_cache(receipt):
    metadata_path=Path(receipt['candidate_cache']['path'])
    assert file_ref(metadata_path)['sha256']==receipt['candidate_cache']['sha256']
    m=read(metadata_path);binary=metadata_path.parent/m['binary']
    assert Path(m['binary']).name==m['binary'] and m['crop']==receipt['crop']
    reference=file_ref(binary)
    assert reference['sha256']==m['binary_sha256']==receipt['candidate_cache']['binary_sha256']
    plane_bytes=m['crop'][2]*m['crop'][3]*4
    assert reference['bytes']==4*plane_bytes==m['binary_bytes']
    actual=[]
    with binary.open('rb') as stream:
        for _ in range(4):
            remaining=plane_bytes;h=hashlib.sha256()
            while remaining:
                block=stream.read(min(1<<20,remaining));assert block
                h.update(block);remaining-=len(block)
            actual.append(h.hexdigest())
        assert not stream.read(1)
    assert actual==m['plane_sha256']==receipt['candidate_planes_sha256']
    return dict(metadata=file_ref(metadata_path),binary=reference,actual_plane_sha256=actual)

def historical_metadata_only(old_path,new_path,expected_pixels):
    images=[];tags=[];regions=[];details=[]
    for path in (old_path,new_path):
        with tifffile.TiffFile(path) as tiff:
            assert len(tiff.pages)==1
            p=tiff.pages[0];image=tiff.asarray()
            assert image.dtype==np.uint16 and image.shape==(4176,6268,3)
            pixels=hashlib.sha256(image.astype('<u2',copy=False).tobytes()).hexdigest()
            assert pixels==expected_pixels
            images.append(image);tags.append({int(t.code):t.value for t in p.tags.values()})
            software=p.tags[305];regions.append((software.valueoffset,software.count))
            assert isinstance(software.value,str) and software.value.startswith('strehl 0.0.0 (')
            strip=hashlib.sha256()
            with path.open('rb') as raw:
                for offset,count in zip(p.dataoffsets,p.databytecounts):
                    raw.seek(offset);value=raw.read(count);assert len(value)==count;strip.update(value)
            details.append(dict(file=file_ref(path),rgb16_le_sha256=pixels,
                encoded_strip_sha256=strip.hexdigest(),software=software.value,
                software_valueoffset=software.valueoffset,software_count=software.count))
    assert np.array_equal(images[0],images[1])
    del images
    assert tags[0].keys()==tags[1].keys()
    changed=[code for code in tags[0] if tags[0][code]!=tags[1][code]]
    assert changed==[305],f'Historical TIFF differs in non-Software tags: {changed}'
    assert tags[0][34675]==tags[1][34675] and tags[0][34675]
    assert details[0]['encoded_strip_sha256']==details[1]['encoded_strip_sha256']
    assert details[0]['file']['bytes']==details[1]['file']['bytes'] and regions[0]==regions[1]
    start,count=regions[0];position=0;different=[]
    with old_path.open('rb') as old,new_path.open('rb') as new:
        while a:=old.read(1<<20):
            b=new.read(len(a));assert len(a)==len(b)
            where=np.flatnonzero(np.frombuffer(a,dtype=np.uint8)!=np.frombuffer(b,dtype=np.uint8))
            for j in where:
                offset=position+int(j)
                assert start<=offset<start+count,'Historical raw file differs outside Software tag payload'
                different.append(offset)
            position+=len(a)
        assert not new.read(1)
    assert different
    return dict(old=details[0],new=details[1],decoded_rgb16_exact=True,icc_exact=True,
        icc_sha256=hashlib.sha256(tags[0][34675]).hexdigest(),only_changed_tag=305,
        changed_bytes=len(different),changed_offsets=different,
        zero_different_bytes_outside_software_payload=True)

def verify(on,off,out):
    assert on!=off and on.parent==off.parent==HERE
    assert out.is_relative_to(HERE) and out!=HERE and not out.exists() and out.parent.is_dir()
    # The historical wrapper failures stay visible. No completion.json is
    # written back to either run, and no refused gate is relabelled passed.
    assert not (on/'completion.json').exists() and not (off/'completion.json').exists()
    bindings=[read(p/'bindings.json') for p in (on,off)]
    assert bindings[0]['observer'] is True and bindings[1]['observer'] is False
    for key in ('sources','executable','recipe','historical','corrected_reference','controls'):
        assert bindings[0][key]==bindings[1][key]
    bound=bindings[0]
    for key in ('executable','recipe','historical','corrected_reference','controls'):
        assert file_ref(Path(bound[key]['path']))==bound[key]
    g.unchanged(bound['sources'])
    control_path=Path(bound['controls']['path']);controls=read(control_path)
    assert controls['source_bindings_unchanged'] and controls['python_commission'] and controls['rust_controls_passed']==5
    assert read(control_path.parent/'bindings.json')==dict(sources=bound['sources'],executable=bound['executable'])
    assert read(control_path.parent/'python/commission.json')['analysis']['actual_analysis_path_passed']
    for part in ('rust','python'):
        process=read(control_path.parent/part/'process.json')
        assert process['exit_code']==0 and process['error'] is None and process['terminal_job_accounting'] and not process['cleanup_errors']
    recipe=f.recipe(Path(bound['recipe']['path']));receipts=[];caches=[];run_records=[]
    old=read(Path(bound['corrected_reference']['path']))
    held_keys=('candidate_rgb16_le_sha256','candidate_planes_sha256','plan','threads','crop','source_count')
    for run in (on,off):
        process=read(run/'process.json')
        assert process['exit_code']==0 and process['error'] is None and process['terminal_job_accounting'] and not process['cleanup_errors']
        assert process['command']==[bound['executable']['path'],f.CORRECTED,'--exact','--ignored','--nocapture','--test-threads=1']
        log=(run/'process.log').read_text(encoding='utf-8',errors='replace')
        assert re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',log)==[('1','0','0')]
        config=read(run/'config.json')
        receipt=f.validate_corrected(run,recipe,config)
        assert all(receipt[key]==old[key] for key in held_keys)
        assert receipt['candidate_sha256']!=old['candidate_sha256'],'Expected historical wrapper refusal is not reproduced'
        receipts.append(receipt);caches.append(actual_cache(receipt))
        run_records.append(dict(run=str(run),original_wrapper_completion_present=False,
            rust_process=file_ref(run/'process.json'),rust_receipt=file_ref(run/'output/receipt.json'),
            rust_full_test_passed=True,original_wrapper_gate='REFUSED cross-build candidate_sha256',
            master=file_ref(run/'output/candidate.tiff')))
    old_cache=actual_cache(old)
    assert caches[0]['actual_plane_sha256']==caches[1]['actual_plane_sha256']==old_cache['actual_plane_sha256']
    assert caches[0]['binary']['sha256']==caches[1]['binary']['sha256']==old_cache['binary']['sha256']
    assert run_records[0]['master']['sha256']==run_records[1]['master']['sha256'],'Same-binary observer-on/off TIFF bytes differ'
    assert receipts[0]['candidate_rgb16_le_sha256']==receipts[1]['candidate_rgb16_le_sha256']
    assert not (off/'output/source-trace').exists()
    trace=on/'output/source-trace';trace_receipt=read(trace/'receipt.json');layout=read(trace/'layout.json')
    assert trace_receipt['sources']==layout['count']==488
    assert all(trace_receipt[key] for key in ('all_sampled_chunk_accumulators_bit_exact','all_final_accumulators_bit_exact','all_sampled_final_cfa_bit_exact'))
    assert (trace/'sources.f32').stat().st_size==488*layout['source_record_floats']*4
    assert (trace/'final-states.f32').stat().st_size==sum(map(len,layout['nodes']))*13*4
    old_master=Path(bound['corrected_reference']['path']).parent/'candidate.tiff'
    assert file_ref(old_master)['sha256']==old['candidate_sha256']
    metadata=historical_metadata_only(old_master,on/'output/candidate.tiff',old['candidate_rgb16_le_sha256'])
    g.unchanged(bound['sources']);out.mkdir()
    c.save(out/'comparison.json',dict(schema=1,status='SAVED_RUST_RESULTS_VERIFIED_WITH_EXPLICIT_HISTORICAL_METADATA_EXCEPTION',
        verifier=file_ref(Path(__file__)),original_wrapper_failures_preserved=True,
        superseded_gate='Literal cross-build candidate_sha256 identity against marigold4-fixed-1',
        replacement='Actual decoded RGB16, ICC and all merged planes exact; raw TIFF changes confined to Software tag305 build string.',
        same_binary_observer_full_tiff_byte_exact=True,all_complete_planes_exact=True,corrected_reference_pixels_and_icc_exact=True,
        historical_metadata_exception=metadata,runs=run_records,caches=caches,historical_cache=old_cache,
        source_bindings_unchanged=True,build_bindings=file_ref(on/'bindings.json'),controls=bound['controls'],
        trace_files=[file_ref(trace/name) for name in ('layout.json','receipt.json','sources.f32','final-states.f32')],
        scope='Read-only saved-result verification, no original RAW reads or rerender. No source-trace witness adequacy or quality conclusion.'))
    print('SAVED_PAIR_VERIFIED: same-binary whole TIFF and planes exact; historical difference confined to Software metadata.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('on','off','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();verify(args.on.resolve(),args.off.resolve(),args.out.resolve())
