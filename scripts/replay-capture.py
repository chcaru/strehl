#!/usr/bin/env python3
"""Replay a recorded capture run into a new folder, as the receiver wrote it.

Stacking during capture (`strehl follow`, and the desktop's Capture screen)
can be exercised without a camera: this re-creates a finished run's folder
file by file, in the order and at the pace its `transfer-receipts.jsonl`
records (scaled by --speed). Each RAW is written, then its receipt appended;
each `events.jsonl` upload becomes the journal prefix of the recorded length,
replaced atomically; `result.json` arrives last.

RAWs are hard-linked when the destination is on the source's volume (no
copy, nothing written to the source) and copied otherwise. The source is
only read. The destination must not exist.

With --registry RECEIVER_JSON the new run is also registered in
`<RECEIVER_JSON without .json>.runs.json`, as the receiver registers a run,
so a desktop launched with capture settings naming RECEIVER_JSON sees the
replay as the capture in progress. Use a scratch receiver configuration:
never a real receiver's.

    python scripts/replay-capture.py SOURCE_RUN DEST_PARENT [--speed 3]
        [--registry SCRATCH/receiver.json] [--copy]

Prints the new run's folder first, then one line per file.
"""
import argparse
import json
import os
import shutil
import sys
import time


def receipts(run):
    with open(os.path.join(run, "transfer-receipts.jsonl"), encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return sorted(rows, key=lambda r: r["saved_unix_ms"])


def replace_with(dest, name, data):
    tmp = os.path.join(dest, f".{name}.replay-partial")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    # Windows refuses to replace a file another process is reading (an
    # engine following the run reads events.jsonl every second); the
    # receiver tries again briefly, and so does this.
    for attempt in range(40):
        try:
            os.replace(tmp, os.path.join(dest, name))
            return
        except PermissionError:
            if attempt == 39:
                raise
            time.sleep(0.025)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("source", help="a finished capture run folder")
    p.add_argument("parent", help="folder to create the replayed run in")
    p.add_argument("--speed", type=float, default=1.0, help="replay this many times faster")
    p.add_argument("--registry", help="scratch receiver.json whose runs.json gets the run")
    p.add_argument("--copy", action="store_true", help="copy RAWs instead of hard-linking")
    a = p.parse_args()
    source = os.path.abspath(a.source)
    rows = receipts(source)
    with open(os.path.join(source, "events.jsonl"), "rb") as f:
        events = f.read()
    run = f"stack-{int(time.time() * 1000)}-{os.getpid()}"
    dest = os.path.join(os.path.abspath(a.parent), run)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    os.mkdir(dest)
    if a.registry:
        index = os.path.splitext(a.registry)[0] + ".runs.json"
        runs = {}
        if os.path.exists(index):
            with open(index, encoding="utf-8") as f:
                runs = json.load(f)
        runs[run] = {"folder": dest}
        with open(index + ".partial", "w", encoding="utf-8") as f:
            json.dump(runs, f)
        os.replace(index + ".partial", index)
    print(dest, flush=True)
    started = time.monotonic()
    t0 = rows[0]["saved_unix_ms"]
    log = open(os.path.join(dest, "transfer-receipts.jsonl"), "a", encoding="utf-8")
    for r in rows:
        due = (r["saved_unix_ms"] - t0) / 1000.0 / a.speed
        wait = due - (time.monotonic() - started)
        if wait > 0:
            time.sleep(wait)
        name = r["logical_name"]
        stored = os.path.basename(r["path"].replace("\\", "/"))
        if name == "events.jsonl":
            replace_with(dest, name, events[: r["bytes"]])
        elif name.endswith(".ARW"):
            src, dst = os.path.join(source, stored), os.path.join(dest, stored)
            if a.copy:
                shutil.copyfile(src, dst)
            else:
                os.link(src, dst)
        else:
            with open(os.path.join(source, stored), "rb") as f:
                replace_with(dest, stored, f.read())
        row = dict(r, path=os.path.join(dest, stored))
        log.write(json.dumps(row) + "\n")
        log.flush()
        os.fsync(log.fileno())
        print(f"{time.monotonic() - started:8.1f} s  {name}", flush=True)
    log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
