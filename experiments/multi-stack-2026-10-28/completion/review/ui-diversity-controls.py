"""Root-scheduled product15 diversity checks; no engine job, no RAW access.
Run against a live helper-owned workspace granting only the completed-output root.
The source UI must include select_session_output and whole-bundle export.
"""
import argparse, importlib.util, json, shutil, sys, time
from pathlib import Path
p=Path(__file__).with_name('ui-completion-controls.py');sp=importlib.util.spec_from_file_location('controls',p);h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)

def wait_photo(ctl):
    return ctl.wait(lambda s: not any(s['busy'].values()) and not (s.get('session') or {}).get('selection_busy',False) and s['photo_ready'] and not s['saved_diagnostics']['loading'],seconds=240)

def main():
    p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,required=True);p.add_argument('--session-file',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--catalog',type=Path,required=True);p.add_argument('--grant-id',required=True);p.add_argument('--relative-run',required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--bundle-export-parent');p.add_argument('--bundle-folder',default='complete-view-bundle');p.add_argument('--capture',action='store_true');args=p.parse_args()
    ctl=h.Control(args)
    ctl.mutate({'operation':'import_completed_session','grant_id':args.grant_id,'relative_path':args.relative_run})
    state=wait_photo(ctl); assert state['error'] is None, state['error']
    outputs=state['session']['layers']; assert len(outputs)==2
    original_settings=state['settings']; records=[]
    for index,path in enumerate(outputs):
        ctl.mutate({'operation':'select_session_output','index':index});state=wait_photo(ctl)
        assert Path(state['session']['selected_output']).resolve()==Path(path).resolve()
        assert state['settings']==original_settings, 'Viewing an output mutated saved recipe'
        names=state['saved_diagnostics']['available'];matches=[n for n in names if 'flags' in n.lower()]
        name=matches[0] if matches else None
        inspected=state
        if state['session']['mode']=='independent_views': assert name,names
        if name:
            ctl.mutate({'operation':'inspect_session_diagnostic','map':name,'opacity':.45,'sample_uv':[.5,.45]})
            inspected=ctl.wait(lambda s:not s['saved_diagnostics']['loading'] and s['saved_diagnostics']['selected']==name)
            assert inspected['saved_diagnostics']['error'] is None
        h.write(args.evidence/f'view-{index:02}-snapshot.json',inspected)
        if args.capture:
            catalog=args.evidence/f'view-{index:02}-catalog.json';shutil.copyfile(args.catalog,catalog)
            for zoom in [1,8]:
                command=['screenshot','--open-run',str(args.run),'--catalog',str(catalog),'--png',str(args.evidence/f'view-{index:02}-zoom-{zoom}.png'),'--size','1440x940','--photo-zoom',str(zoom),'--photo-center','.5,.45']
                if name: command += ['--diagnostic-map',name,'--diagnostic-opacity','.45','--diagnostic-sample','.5,.45']
                reply=ctl.run(command)
                assert reply['data']['state']=='screenshot_saved'
        export_name=f'{args.run.name}-view-{index+1:02}.png'
        ctl.mutate({'operation':'export','file_name':export_name,'format':'png','color_space':'srgb','hdr':False})
        exported_photo=ctl.wait(lambda s:not s['busy']['export'],seconds=240)
        assert exported_photo['error'] is None and exported_photo['export'], exported_photo.get('error')
        assert exported_photo['settings']==original_settings
        h.write(args.evidence/f'view-{index:02}-photo-export.json',exported_photo)
        records.append({'index':index,'output':path,'map':name,'photo_export':exported_photo['export']})
    before=ctl.snapshot()[1];ctl.mutate({'operation':'select_session_output','index':len(outputs)},expected=1);after=ctl.snapshot()[1]
    assert before['settings']==after['settings'] and before['session']==after['session']
    if args.bundle_export_parent:
        assert state['session']['mode']=='independent_views'
        ctl.mutate({'operation':'export_view_bundle','grant_id':args.grant_id,'relative_parent':args.bundle_export_parent,'folder_name':args.bundle_folder})
        exported=ctl.wait(lambda s:not s['export_capabilities']['view_bundle']['busy'],seconds=300)
        assert exported['error'] is None and exported['export_capabilities']['view_bundle']['last_export']
        # Existing destination refuses; completed bytes must remain untouched.
        ctl.mutate({'operation':'export_view_bundle','grant_id':args.grant_id,'relative_parent':args.bundle_export_parent,'folder_name':args.bundle_folder})
        refused=ctl.wait(lambda s:not s['export_capabilities']['view_bundle']['busy'],seconds=300);assert refused['error'] and 'exists' in refused['error'].lower()
        relative=args.bundle_export_parent.rstrip('/\\')+'/'+args.bundle_folder
        ctl.mutate({'operation':'import_completed_session','grant_id':args.grant_id,'relative_path':relative});reopened=wait_photo(ctl)
        assert reopened['session']['mode']=='independent_views' and len(reopened['session']['layers'])==2
        h.write(args.evidence/'relocated-reopen.json',reopened)
    ctl.finish({'outputs':records,'settings_unchanged':True,'out_of_range_refused':True,'actual_gpu_requires_visual_inspection':args.capture,'complete_bundle_export_requested':bool(args.bundle_export_parent)})
if __name__=='__main__':main()
