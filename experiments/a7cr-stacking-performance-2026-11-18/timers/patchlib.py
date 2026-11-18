"""Exact, asserted text replacements on the scratch copy (never the product tree).

An edit is (old, new) or (old, new, occurrence). An edit whose `new` text is
already present and whose `old` text no longer matches is skipped, so a script
can be run again after a later edit in it failed.
"""
import os

# The scratch copy to patch: never the product tree.
ROOT = os.environ.get('STREHL_SCRATCH') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')


def patch(rel, edits, append=None):
    path = os.path.join(ROOT, rel)
    assert os.path.abspath(path).startswith(os.path.abspath(ROOT)), path
    raw = open(path, 'rb').read()
    crlf = b'\r\n' in raw
    text = raw.decode('utf-8')
    if crlf:
        text = text.replace('\r\n', '\n')
    done = 0
    for i, edit in enumerate(edits):
        old, new = edit[0], edit[1]
        which = edit[2] if len(edit) > 2 else None
        n = text.count(old)
        if new in text:
            continue
        if which is None:
            assert n == 1, '%s: edit %d matches %d times: %r' % (rel, i, n, old[:70])
            text = text.replace(old, new)
        else:
            assert n > which, '%s: edit %d matches %d times, wanted #%d' % (rel, i, n, which)
            at = -1
            for _ in range(which + 1):
                at = text.index(old, at + 1)
            text = text[:at] + new + text[at + len(old):]
        done += 1
    if append and append not in text:
        text = text.rstrip('\n') + '\n' + append + '\n'
    if crlf:
        text = text.replace('\n', '\r\n')
    open(path, 'wb').write(text.encode('utf-8'))
    print('patched', rel, done, 'of', len(edits), 'edits')
