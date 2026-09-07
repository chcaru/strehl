"""Re-sealed independent structural mutations of a completed real baseline.

No native calls. The root scorer is the subject, not the expected-value source.
Unchanged/canonical-path controls must pass; contradictions must be refused.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='2'

HERE=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def absolute(path,base):
    return str((base/Path(path)).resolve())


def relocated(index,base):
    value=copy.deepcopy(index)
    for key in ('build_record','producer_result','producer_commission'):
        value[key]['path']=absolute(value[key]['path'],base)
    for item in value['source_snapshots']:
        item['path']=absolute(item['path'],base)
    for case in value['cases']:
        for key in ('manifest_path','plan_path'):
            case[key]=absolute(case[key],base)
        for arm in case['arms']:
            arm['receipt_path']=absolute(arm['receipt_path'],base)
    for command in value['commands']:
        command['log']=absolute(command['log'],base)
        if 'consumer_evidence' in command:
            command['consumer_evidence']['path']=absolute(command['consumer_evidence']['path'],base)
    return value


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--index',type=Path,required=True)
    parser.add_argument('--expected-index-sha',required=True)
    parser.add_argument('--reader-revision',type=Path)
    parser.add_argument('--reader-revision-sha')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.index=args.index.resolve();args.out=args.out.resolve()
    if sha(args.index)!=args.expected_index_sha:
        raise ValueError('trusted original index changed')
    index=json.loads(args.index.read_text())
    if index.get('status')!='complete':
        raise ValueError('wait for complete/abort; this verifier will not score a running package')
    revision=None
    if args.reader_revision is not None:
        if sha(args.reader_revision)!=args.reader_revision_sha:
            raise ValueError('trusted reader revision changed')
        revision=json.loads(args.reader_revision.read_text())
        if revision['render_index_sha256']!=args.expected_index_sha:
            raise ValueError('reader revision belongs to another original package')
    args.out.mkdir(parents=True,exist_ok=False)
    specification=importlib.util.spec_from_file_location('controller_subject',HERE/'score-benchmark.py')
    subject=importlib.util.module_from_spec(specification)
    specification.loader.exec_module(subject)
    source_before={name:sha(HERE/name) for name in ('score-benchmark.py','score.py','run-baseline.py')}
    base=relocated(index,args.index.parent)
    cases=[]
    def run(name,value,expected):
        path=args.out/(name+'.json')
        write(path,value)
        binding=None
        if revision is not None:
            # A fresh synthetic case gets a fresh explicit revision binding;
            # the trusted previous/current analysis source hashes stay fixed.
            revised=copy.deepcopy(revision)
            revised['render_index_sha256']=sha(path)
            revised['reason']+=' Independent controller mutation/control: '+name+'.'
            revision_path=args.out/(name+'-reader-revision.json')
            write(revision_path,revised)
            binding=(revision_path,sha(revision_path))
        try:
            result=subject.score_run(path,sha(path),reader_binding=binding)
            actual=True;detail={'output_count':result['output_count'],'status':result['status']}
        except Exception as exc:
            actual=False;detail={'exception':repr(exc)}
        row={'name':name,'expected_admitted':expected,'admitted':actual,
             'correct_disposition':actual==expected,'index_sha256':sha(path),**detail}
        cases.append(row)
        print(json.dumps(row),flush=True)
    run('unchanged-absolute-path-control',base,True)
    mutations={}
    m=copy.deepcopy(base);m['commands'].pop(19);mutations['missing-final-plan-command']=m
    m=copy.deepcopy(base);m['commands'][19],m['commands'][20]=m['commands'][20],m['commands'][19]
    mutations['render-before-last-plan']=m
    m=copy.deepcopy(base);m['commands'][-1]['exit_code']=17;mutations['failed-final-controller-command']=m
    m=copy.deepcopy(base);m['commands'][-1].pop('consumer_evidence');mutations['missing-child-binding']=m
    m=copy.deepcopy(base);m['source_snapshots'].pop(0);mutations['missing-source-snapshot']=m
    m=copy.deepcopy(base);m['status']='failed';mutations['failed-completion-with-pixels']=m
    m=copy.deepcopy(base);m['cases'][2]['repeat']=701;mutations['duplicate-paired-repeat']=m
    m=copy.deepcopy(base);m['cases'][3]['arms'][0]['name']='single4';m['cases'][3]['arms'][1]['name']='full9'
    mutations['swapped-full-and-single-labels']=m
    m=copy.deepcopy(base);m['commands'][-1]['command'][-1]='different-command-log';mutations['false-parent-argv']=m
    for name in ('changed-child-executable','changed-child-subset','changed-child-result-hash'):
        m=copy.deepcopy(base)
        ref=m['commands'][-1]['consumer_evidence']
        child=json.loads(Path(ref['path']).read_text())
        if name=='changed-child-executable':
            child['command'][0]=str(HERE/'score.py')
        elif name=='changed-child-subset':
            child['environment']['STREHL_M194B_SUBSET']='all'
        else:
            child['result_sha256']='0'*64
        path=args.out/(name+'-child.json');write(path,child)
        ref['path']=str(path);ref['sha256']=sha(path)
        mutations[name]=m
    for name,value in mutations.items():
        run(name,value,False)
    run('final-unchanged-control',base,True)
    result={'scope':'independent actual run-index contradiction checks; no native calls',
        'original_index':str(args.index),'original_index_sha256':args.expected_index_sha,
        'original_reader_revision_sha256':args.reader_revision_sha,
        'original_unchanged':sha(args.index)==args.expected_index_sha,'sources_before':source_before,
        'sources_after':{name:sha(HERE/name) for name in source_before},'cases':cases,
        'pass':all(c['correct_disposition'] for c in cases)}
    result['pass']=result['pass'] and result['original_unchanged'] and result['sources_before']==result['sources_after']
    write(args.out/'result.json',result)
    raise SystemExit(0 if result['pass'] else 1)


if __name__=='__main__':
    main()
