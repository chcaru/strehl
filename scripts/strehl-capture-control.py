#!/usr/bin/env python3
"""Commission Strehl Capture's actual native UI without desktop automation.

All modes explicitly use the simulator. No SDK initialization or camera activity.
"""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--exe', type=Path, required=True)
sub = parser.add_subparsers(dest='command', required=True)
shot = sub.add_parser('screenshot')
shot.add_argument('--png', type=Path, required=True)
shot.add_argument('--size', default='1366x900')
exercise = sub.add_parser('exercise')
exercise.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
command = [str(args.exe.resolve()), '--demo']
if args.command == 'screenshot':
    command += ['--offscreen-screenshot', str(args.png.resolve()), '--size', args.size]
else:
    command += ['--exercise', str(args.out.resolve())]
result = subprocess.run(command, check=False, timeout=120)
raise SystemExit(result.returncode)
