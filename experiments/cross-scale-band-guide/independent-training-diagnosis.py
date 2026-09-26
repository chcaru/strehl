"""Read-only training preservation diagnosis; no fitting or held pixels."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE=Path(__file__).resolve().parent
IDS=('train-multiscale-gabor-v0-n5-b7','train-unclipped-glint-v0-n9-b3',
     'train-clipped-glint-v0-n9-b3')


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    import numpy as np
    score=module(HERE/'independent-transfer-check.py','training_existing_score')
    loss=module(HERE/'independent-develop-check.py','training_independent_loss')
    pred_path=HERE/'expanded-training-infer-1/output/predictions.json'
    fit_path=HERE/'expanded-train-1/output/training.json'
    annotations_path=HERE/'training-annotations.json'
    pred=score.load(pred_path); fit=score.load(fit_path)
    annotations={r['id']:r for r in score.load(annotations_path)['cases']}
    score.need(pred['truth_read'] is False and pred['model_sha256']==fit['model_sha256'],
               'training inference/model binding differs')
    manifest=score.load(pred['dataset'])
    score.need(manifest['split']=='training' and score.sha(pred['dataset'])==fit['dataset_sha256'],
               'training data binding differs')
    score.need(score.sha(annotations_path)==fit['annotations_sha256'],'annotation changed')
    selected,=[h for h in fit['history'] if h['step']==fit['chosen_step']]
    fit_rows={r['id']:r for r in selected['cases']}
    initial_rows={r['id']:r for r in fit['history'][0]['cases']}
    records={Path(r['case']).parent.name:r for r in pred['records']}
    result=[]
    for identity in IDS:
        record=records[identity]; path=Path(record['case']); meta=score.load(path)
        score.need(score.sha(path)==record['case_sha256']==fit_rows[identity]['case_sha256'],
                   'training case binding differs')
        independent=score.load(path.parent/'independent-truth.json')
        label=independent['label']
        score.need(label['training'] is True and label['id']==identity,'nontraining case refused')
        values={k:score.array(path.parent,meta['arrays'][k],np)
                for k in ('canonical-rgb','uniform-rgb','truth-rgb')}
        values.update({k:score.array(path.parent,independent['templates'][k],np)
                       for k in ('base','near','far')})
        candidate=score.array(pred_path.parent,record['arrays']['rgb'],np)
        case={'path':path,'meta':meta,'label':label,'values':values}
        annotation=annotations[identity]
        # Existing training ROI coordinates are frozen before export/model results.
        regions=[]
        if label['family']=='multiscale-gabor':
            regions=[{'name':f'training-carrier-{j}','carrier':j,'xyxy':box}
                     for j,box in enumerate(annotation['roi_xyxy'])]
        else:
            # Core/adjacent/spread are the pre-fit glint/clipped annotation union.
            regions=[{'name':'genuine-core','xyxy':[59,55,82,79]}] if label['family']=='unclipped-glint' else []
            regions += [{'name':name,'xyxy':box} for name,box in zip(
                ('adjacent','spread'),annotations[IDS[2]]['roi_xyxy'])]
        rows=[]
        for region in regions:
            scene=score.scene(case,region,np)
            measurements={name:score.score(scene,score.crop(value,region,np),np) for name,value in
                          [('current',values['canonical-rgb']),('uniform',values['uniform-rgb']),('candidate',candidate)]}
            recovery=[]
            for c in range(3):
                for component in range(2):
                    a=measurements['current']['near_far_coefficients'][c][component]
                    b=measurements['candidate']['near_far_coefficients'][c][component]
                    if a is not None and a>=.5:
                        recovery.append({'channel':c,'component':component,'current':a,'candidate':b,
                            'capped_retention':min(1,max(0,b))/min(1,a) if b is not None else None})
            rows.append({**region,**measurements,'eligible_recoveries':recovery})
        error=np.asarray(candidate-values['truth-rgb'],dtype=np.float32)
        total,parts=loss.independent_loss(error,[],annotation,np)
        logged=fit_rows[identity]
        score.need(abs(total-logged['loss'])<=max(1e-10,1e-5*logged['loss']),
                   'independent training loss differs from selected checkpoint')
        weighted={'global_rgb':parts['rgb_mse'],'global_chroma':2*parts['chroma_mse'],
                  'green_gradient':.25*parts['green_gradient_mse'],
                  'roi_joint':.25*parts['roi_rgb_chroma_mse']}
        valid,_,_=loss.expected_masks(annotation,np)
        roi_terms=[]
        for j,box in enumerate(annotation['roi_xyxy']):
            x0,y0,x1,y1=box
            e=error[y0:y1,x0:x1].astype(np.float64)
            v=valid[y0:y1,x0:x1]
            rgb=float(np.mean(e[v]**2))
            chroma=np.stack((e[...,0]-e[...,1],e[...,2]-e[...,1]),axis=-1)
            colour=float(np.mean(chroma[v]**2))
            term=.25*(rgb+2*colour)/len(annotation['roi_xyxy'])
            roi_terms.append({'index':j,'xyxy':box,'valid_pixels':int(v.sum()),
                             'rgb_mse':rgb,'chroma_mse':colour,'case_loss_contribution':term,
                             'fraction_of_43case_mean':term/(43*selected['score'])})
        result.append({'id':identity,'regions':rows,'independent_loss':total,
            'logged_loss':logged['loss'],'weighted_terms':weighted,'roi_terms':roi_terms,
            'fraction_of_43case_mean':total/(43*selected['score']),
            'initial_case_loss':initial_rows[identity]['loss'],
            'chosen_over_initial_case_loss':total/initial_rows[identity]['loss'],
            'training_roi_note':'Exact existing normalized training ROIs; compact adjacent/spread scored separately even when not extra-ROI supervised.'})
    known_path=HERE/'developer-check-2/output/screen.json'
    known=score.load(known_path)
    curved,=[r for r in known['cases'] if r['id']=='held-curved-bright-occlusion-n9']
    old=fit_rows[curved['id']]
    result.append({'id':curved['id'],'developer_known':True,
        'windows':[{'name':r['window'],'ratios':r['candidate_reference_ratios'],
                    'failures':r['prospective_failures']} for r in curved['prospective_windows']],
        'chosen_loss':old['loss'],'fraction_of_43case_mean':old['loss']/(43*selected['score']),
        'weighted_terms':{'global_rgb':old['rgb_mse'],'global_chroma':2*old['chroma_mse'],
                          'green_gradient':.25*old['green_gradient_mse'],'roi_joint':.25*old['roi_rgb_chroma_mse']},
        'initial_case_loss':initial_rows[curved['id']]['loss'],
        'chosen_over_initial_case_loss':old['loss']/initial_rows[curved['id']]['loss']})
    score.need(not args.out.exists(),'fresh diagnosis output required')
    args.out.mkdir()
    document={'schema':1,'status':'TRAINING_ONLY_DIAGNOSIS_COMPLETE','model_sha256':fit['model_sha256'],
        'chosen_step':selected['step'],'training_mean':selected['score'],'cases':result,
        'fresh_held_read':False,'training_or_parameter_search':False,'command':[sys.executable,*sys.argv],
        'script_sha256':score.sha(__file__),'scorer_sha256':score.sha(HERE/'independent-transfer-check.py'),
        'loss_reference_sha256':score.sha(HERE/'independent-develop-check.py'),
        'inputs':[{'path':p,'sha256':s} for p,s in sorted(score.INPUTS.items())],
        'limitation':'Observed training residuals/terms; projection can credit ringing and total MSE can reward smoothing. No held bars or model changed.'}
    with (args.out/'diagnosis.json').open('x',encoding='utf-8') as handle:
        json.dump(document,handle,indent=2,allow_nan=False)


if __name__=='__main__':
    main()
