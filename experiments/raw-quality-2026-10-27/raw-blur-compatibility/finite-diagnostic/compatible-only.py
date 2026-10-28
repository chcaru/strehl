"""Observe the unrun structured case without changing or qualifying its fit."""
from pathlib import Path
import hashlib
import importlib.util
import sys

path = Path(__file__).resolve().with_name("controls.py")
assert hashlib.sha256(path.read_bytes()).hexdigest() == "4886faa2ccdd5e2faf076cbbf20409b32b66bdaefd836c214f3ddc95ad5c73bc"
spec = importlib.util.spec_from_file_location("fixed_compatible_observation", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.ORDER = ("compatible",)
module.main()
