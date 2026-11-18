"""Install the exposure/burst-capable controller and bridge with the existing
rollback deployment (configuration, keys, marks and plan preserved)."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    'controls_deploy', ROOT / 'experiments/native-capture-controls-2026-11-13/deploy.py')
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
d.OUT = ROOT / 'outputs/a7cr-calibration-2026-11-14'

if __name__ == '__main__':
    d.main()
