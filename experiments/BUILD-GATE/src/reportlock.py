"""An exclusive lock for harnesses that mutate BUILD-GATE-4.md in place.

Written after a real failure, not as a precaution. `negctl_s13.py` was left
running in the background while section 15 was spliced into the same file.
The two raced: the harness had captured a backup from before section 15
existed and restored it after every planted flip, repeatedly deleting a
section another process was writing. Worse, when the harness was stopped
mid-flip its `finally` never ran, so a PLANTED CONCLUSION REVERSAL -- "This
knob fixes the mottle" in place of "cannot fix" -- was left sitting in the
report. It was caught only because the pinned CONCLUSIONS table happened to
list that exact reversal as forbidden.

Two lessons are encoded here:

  1. Only one mutating harness at a time. `O_EXCL` makes that structural
     rather than a thing to remember.
  2. The lock records the PID and the file it guards, so a stale lock can be
     diagnosed instead of blindly deleted.

Multiple agents share this working tree, so this is not only about this
lane's own background jobs.
"""
import errno
import os
import sys
import time

LOCK = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    ".report-mutation.lock")


class ReportLock:
    def __init__(self, owner, path=LOCK):
        self.owner = owner
        self.path = path
        self.fd = None

    def __enter__(self):
        try:
            self.fd = os.open(self.path,
                              os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            try:
                held = open(self.path, encoding="utf-8").read().strip()
            except OSError:
                held = "<unreadable>"
            sys.exit(
                "REFUSING TO RUN: another harness holds the report mutation "
                "lock.\n  lock: %s\n  held by: %s\n"
                "Two harnesses editing BUILD-GATE-4.md at once corrupt each "
                "other's backups.\nIf that process is genuinely dead, delete "
                "the lock file by hand after\nchecking the report for a "
                "planted mutation left behind by its abort."
                % (self.path, held))
        os.write(self.fd, ("%s pid=%d started=%s"
                           % (self.owner, os.getpid(),
                              time.strftime("%Y-%m-%d %H:%M:%S")))
                 .encode("utf-8"))
        os.close(self.fd)
        self.fd = None
        return self

    def __exit__(self, *exc):
        try:
            os.unlink(self.path)
        except OSError:
            pass
        return False
