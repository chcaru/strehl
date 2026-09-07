"""Narrow M194g source loader. Execute the checked bytes, never a cached model."""
from dataclasses import dataclass
import hashlib
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
E_DIR = HERE.parent / "m194e-joint-pupil"
PINS = {
    "model.py": "a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8",
    "render.py": "487c1727ca3aab05dd66a7056fb368712ccaabbbe604818fdc8b47eda77b6e97",
}


def checked_bytes(path, expected=None):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        raw = stream.read(1_048_577)
    if len(raw) > 1_048_576:
        raise ValueError("source exceeds1MiB")
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError("pinned source mismatch: " + str(path))
    return raw, dict(path=str(path), sha256=digest, bytes=len(raw))


def execute_bytes(path, name, expected=None):
    raw, binding = checked_bytes(path, expected)
    spec = importlib.util.spec_from_loader(name, loader=None, origin=binding["path"])
    module = importlib.util.module_from_spec(spec)
    module.__file__ = binding["path"]
    module.__checked_source__ = binding
    sys.modules[name] = module
    try:
        exec(compile(raw, binding["path"], "exec"), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


@dataclass
class FrozenModules:
    model: object
    render: object
    bindings: dict

    def assert_unchanged(self):
        for filename, module in (("model.py", self.model), ("render.py", self.render)):
            binding = self.bindings[filename]
            _, current = checked_bytes(binding["path"], binding["sha256"])
            if (current != binding or module.__file__ != binding["path"]
                    or module.__checked_source__ != binding):
                raise ValueError("frozen source binding changed")
        if (self.render.file_ref is not self.model.file_ref
                or self.render.write_json is not self.model.write_json):
            raise ValueError("render no longer binds the checked model")
        return True


def load_frozen(directory=E_DIR):
    directory = Path(directory).resolve(strict=True)
    model = execute_bytes(directory / "model.py", "m194g_frozen_model", PINS["model.py"])
    missing = object()
    previous = sys.modules.get("model", missing)
    try:
        sys.modules["model"] = model
        render = execute_bytes(directory / "render.py", "m194g_frozen_render", PINS["render.py"])
    finally:
        if previous is missing:
            sys.modules.pop("model", None)
        else:
            sys.modules["model"] = previous
    bound = FrozenModules(model, render, {"model.py": model.__checked_source__,
                                         "render.py": render.__checked_source__})
    bound.assert_unchanged()
    return bound
