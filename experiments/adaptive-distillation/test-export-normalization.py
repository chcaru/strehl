"""Conversion controls for large, nearly constant and asymmetric feature planes."""
import importlib.util
import copy
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import onnxruntime as ort
import torch

spec = importlib.util.spec_from_file_location("normalization_export", Path(__file__).with_name("export-v4.py"))
EXPORT = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = EXPORT
spec.loader.exec_module(EXPORT)
torch.set_num_threads(4)


def oracle(value, groups, epsilon, weight, bias):
    grouped = value.astype(np.float64).reshape(value.shape[0], groups, -1)
    centered = grouped - grouped.mean(-1, keepdims=True)
    result = (centered / np.sqrt((centered * centered).mean(-1, keepdims=True) + epsilon)).reshape(value.shape)
    if weight is not None:
        shape = (1, -1) + (1,) * (value.ndim - 2)
        result = result * weight.reshape(shape) + bias.reshape(shape)
    return result


class NormalizationExportTests(unittest.TestCase):
    def test_real_shapes_and_nearly_constant_planes(self):
        rng = np.random.default_rng(913)
        cases = [(1, 24, 192, 256), (2, 64, 24, 32), (1, 48, 96, 128)]
        for shape in cases:
            c = shape[1]
            yy, xx = np.mgrid[:shape[-2], :shape[-1]]
            pattern = .003 * np.sin(xx / 19) + .002 * np.cos(yy / 13)
            flat = np.broadcast_to(.4 + pattern, shape).copy().astype(np.float32)
            flat += np.linspace(-.0003, .0003, c, dtype=np.float32)[None, :, None, None]
            for affine in (False, True):
                native = torch.nn.GroupNorm(4, c, eps=1e-5, affine=affine).eval()
                if affine:
                    with torch.no_grad():
                        native.weight.copy_(torch.linspace(.7, 1.3, c))
                        native.bias.copy_(torch.linspace(-.2, .1, c))
                model = EXPORT.portable_model(torch.nn.Sequential(native))
                self.assertIs(type(native), torch.nn.GroupNorm)
                self.assertIsInstance(model[0], EXPORT.PortableGroupNorm)
                if affine:
                    self.assertNotEqual(native.weight.data_ptr(), model[0].weight.data_ptr())
                with tempfile.TemporaryDirectory(prefix="strehl-normalization-") as directory:
                    path = Path(directory) / "normalization.onnx"
                    torch.onnx.export(model, torch.from_numpy(flat), str(path),
                                      input_names=["input"], output_names=["output"],
                                      opset_version=17, dynamo=False)
                    options = ort.SessionOptions()
                    options.intra_op_num_threads = 4
                    runtime = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
                    for value in (flat, rng.normal(.2, .3, shape).astype(np.float32), np.full(shape, .4, np.float32)):
                        weight = None if not affine else native.weight.detach().numpy().astype(np.float64)
                        bias = None if not affine else native.bias.detach().numpy().astype(np.float64)
                        reference = oracle(value, 4, native.eps, weight, bias)
                        actual = runtime.run(["output"], {"input": value})[0]
                        with torch.inference_mode():
                            original = native(torch.from_numpy(value)).numpy()
                            double = copy.deepcopy(native).double()(torch.from_numpy(value).double()).numpy()
                        self.assertEqual(actual.dtype, np.float32)
                        np.testing.assert_allclose(actual, reference, rtol=2e-4, atol=2e-5)
                        np.testing.assert_allclose(double, reference, rtol=1e-9, atol=1e-10)
                        # Native FP32 fused affine evaluation itself loses precision
                        # near zero on almost-flat fields (independently observed
                        # 2.235e-5 here). Assert its error bound across ALL samples;
                        # do not exclude that case or make it the mathematical oracle.
                        # Full trained-model parity retains the original strict gate
                        # in export-v4.py against untouched native FP32 inference.
                        self.assertLess(float(np.max(np.abs(original - reference))), 5e-5)
                        if value is flat:
                            wrong = oracle(value, 2, native.eps, weight, bias)
                            self.assertGreater(float(np.max(np.abs(actual - wrong))), .001,
                                               "fixture must reject the wrong grouping")


if __name__ == "__main__":
    unittest.main()
