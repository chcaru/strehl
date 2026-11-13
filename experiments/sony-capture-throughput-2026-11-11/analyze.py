from pathlib import Path
import hashlib
import json
import statistics
import rawpy

repo=Path(__file__).resolve().parents[2]
out=repo/'outputs/sony-capture-throughput-2026-11-11'
old=json.loads((repo/'outputs/pi-capture-performance-2026-11-11/overlap-stack.json').read_text())
events_path=Path(old['stack'])/'events.jsonl'
events=[json.loads(line) for line in events_path.read_text().splitlines()]
rows=[]
for n in range(1,6):
    def event(name, ordinal=n):
        return next(e for e in events if e['event']==name and e['data'].get('ordinal')==ordinal)
    f=event('focus_intent');fc=event('focus_complete');c=event('capture_intent')
    done=event('capture_buffered');previous=event('capture_buffered',n-1)
    camera=done['data']['response']['camera_seconds']
    rows.append({'ordinal':n,'preview_and_loop_s':(f['unix_ms']-previous['unix_ms'])/1000,
                 'focus_s':(fc['unix_ms']-f['unix_ms'])/1000,
                 'pre_capture_s':(c['unix_ms']-fc['unix_ms'])/1000,'camera_s':camera,
                 'capture_remaining_s':(done['unix_ms']-c['unix_ms'])/1000-camera})
attribution={'source':str(events_path),'sha256':hashlib.sha256(events_path.read_bytes()).hexdigest(),
             'per_frame':rows,'means':{key:statistics.mean(r[key] for r in rows) for key in rows[0] if key!='ordinal'},
             'exposure_s':2,'settle_s':.5}
(out/'existing-cadence-attribution.json').write_text(json.dumps(attribution,indent=2)+'\n')
probe=json.loads((out/'direct-probe.json').read_text())
pilot=json.loads((out/'direct-probe-pilot.json').read_text())
arms=json.loads((out/'settle-comparison.json').read_text())
props=['ShutterSpeed','IsoSensitivity','FNumber','FileType','RAW_FileCompressionType','StillImageStoreDestination']
settings={k:probe['settings']['properties'][k]['value'] for k in props}
assert settings=={k:pilot['settings']['properties'][k]['value'] for k in props}
for arm in arms:
    assert settings=={k:arm['manifest']['initial_status']['properties'][k]['value'] for k in props}
invalid=[{'group':label,'ordinal':f['ordinal'],'focus':f['focus']}
         for label,r in [('pilot',pilot),('refined',probe)] for f in r['frames']
         if f['focus']['requested']!=f['focus']['readback']]
report={'settings_unchanged':settings,'physical_raws':len(probe['frames'])+len(pilot['frames'])+sum(len(a['files']) for a in arms),
        'focus_unverified_probe_frames':invalid,'rawpy_version':rawpy.__version__,
        'cpu_load_before_refined_probe':probe['load_before'],'bridge_sha256':probe['bridge_sha256'],
        'app_intervals':[{'settle_ms':a['settle_ms'],'seconds':a['interval_seconds']} for a in arms],
        'liveview_capture_s':{str(v):[f['capture_seconds'] for f in probe['frames'] if f['live_view']==v] for v in [True,False]},
        'usb_bulk_service_s':[f['usb_large_span_seconds'] for f in probe['frames']],
        'usb_service_MBps':[f['usb_large_bytes']/f['usb_large_span_seconds']/1e6 for f in probe['frames']],
        'compression':probe['compression']}
compressed=probe['compression'][0]
report['sequential_compression_break_even_MBps']=(compressed['input_bytes']-compressed['compressed_bytes'])/compressed['seconds']/1e6
report['projections']=[{'case':name,'MB_per_plane':size,'seconds_at_25_MBps':size/25,
                        'seconds_at_assumed_75_MBps':size/75,'GB_for_900_planes':size*900/1000}
                       for name,size in [('A7CR ordinary example',75),('A7CR four-shot example',500),('A7CR sixteen-shot example',2000)]]
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'physical_raws':report['physical_raws'],'means':attribution['means'],
                  'usb_MBps':report['usb_service_MBps'],'compression_break_even_MBps':report['sequential_compression_break_even_MBps']}))
