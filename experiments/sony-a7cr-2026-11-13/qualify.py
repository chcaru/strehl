"""Explicit short physical A7CR test, using the production browser API.

Never retries a start command. Retains failures and every RAW. --control pause
pauses after a member arrives, verifies the complete four-shot boundary, resumes.
--control stop stops after that boundary. Marks are diagnostic and are cleared
by the final connection check, after file verification.
"""
import argparse
import json
import time
from deploy import state, command, wait, OUT


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--planes', type=int, choices=[1, 2, 3], default=1)
    p.add_argument('--label', required=True)
    p.add_argument('--control', choices=['pause', 'stop'])
    a = p.parse_args()
    target = OUT / (a.label + '.json')
    assert not target.exists(), 'Do not overwrite test evidence'
    before = state()
    assert before['editable'] and before['shots_per_plane'] == 4
    assert before['storage'].get('pending_frames', 0) == 0
    start = before['position']
    command('mark', start=True)
    for _ in range(a.planes - 1):
        old = state()['position']
        command('jog', delta=1)
        wait(lambda s: s['editable'] and s['position'] == old + 1)
    command('mark', start=False)
    assert state()['planned'] == a.planes
    command('start')
    history = []
    sent = False
    paused = None
    end = time.monotonic() + 180
    while time.monotonic() < end:
        s = state()
        history.append({'at': time.time(), 'phase': s['phase'], 'completed': s['completed'],
                        'position': s['position'], 'storage': s['storage'],
                        'failure': s['failure'], 'timer': s['timer']})
        if a.control and not sent and s['sequence_id'] > before['sequence_id'] and s['phase'] == 'capturing' and s['storage'].get('captured_frames', 0) >= 1:
            command(a.control)
            sent = True
        if s['phase'] == 'paused' and paused is None:
            assert s['completed'] == 1 and s['storage']['saved_frames'] == 4
            assert s['storage']['pending_frames'] == 0
            time.sleep(1.2)
            check = state()
            assert check['phase'] == 'paused' and check['storage']['captured_frames'] == 4
            paused = {'completed': check['completed'], 'saved_raws': check['storage']['saved_frames'], 'held_seconds': 1.2}
            command('resume')
        if s['phase'] in ['complete', 'stopped', 'fault'] and not s['busy']:
            break
        time.sleep(.15)
    result = {'before_focus': start, 'planes': a.planes, 'control': a.control,
              'paused': paused, 'final': s, 'history': history}
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'phase': s['phase'], 'completed_planes': s['completed'],
                      'focus': s['position'], 'storage': s['storage'], 'failure': s['failure']}))
    expected = 1 if a.control == 'stop' else a.planes
    assert s['phase'] == ('stopped' if a.control == 'stop' else 'complete')
    assert s['completed'] == expected and s['storage']['saved_frames'] == expected * 4
    assert s['storage']['pending_frames'] == 0


if __name__ == '__main__': main()
