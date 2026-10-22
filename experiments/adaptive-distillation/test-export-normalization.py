"""Conversion controls for large, nearly constant and asymmetric feature planes."""
import importlib.util
import copy
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import onnx
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
    def test_bounded_pooling_with_awkward_extents_and_anchor_outliers(self):
        # Independent shapes include prime extents and non-power-of-two groups.
        # A large value at the chosen anchor makes naive full-width pooling fail
        # this same FP64 comparison; keep the difficult input in the assertion.
        for number, (shape, groups) in enumerate([
                ((2, 15, 127, 193), 3), ((1, 20, 65, 129), 5),
                ((1, 24, 192, 256), 4)]):
            native = torch.nn.GroupNorm(groups, shape[1], eps=1e-5).eval()
            with torch.no_grad():
                native.weight.copy_(torch.linspace(-1.7, 1.3, shape[1]))
                native.bias.copy_(torch.linspace(.3, -.27, shape[1]))
            yy, xx = np.mgrid[:shape[-2], :shape[-1]]
            near = np.broadcast_to(.4 + 2e-5 * np.sin(xx / 7) * np.cos(yy / 11), shape).copy().astype(np.float32)
            near += np.linspace(-3e-5, 3e-5, shape[1], dtype=np.float32)[None, :, None, None]
            outlier = near.copy()
            outlier[:, :, 0, 0] = 32
            rng = np.random.default_rng(20261022 + number)
            fixtures = [near, np.full(shape, .4, np.float32), outlier,
                        rng.normal(.1, .9, shape).astype(np.float32)]
            original_state = {key: value.clone() for key, value in native.state_dict().items()}
            with torch.inference_mode():
                original_output = native(torch.from_numpy(near)).clone()
            model = EXPORT.portable_model(torch.nn.Sequential(native))
            with tempfile.TemporaryDirectory(prefix="strehl-pooling-tree-") as directory:
                path = Path(directory) / "normalization.onnx"
                torch.onnx.export(model, torch.from_numpy(near), str(path),
                                  input_names=["input"], output_names=["output"],
                                  opset_version=17, dynamo=False)
                graph = onnx.load(path)
                pools = [node for node in graph.graph.node if node.op_type == "AveragePool"]
                self.assertTrue(pools)
                self.assertFalse(any(node.op_type in ("ReduceMean", "InstanceNormalization")
                                     for node in graph.graph.node))
                for node in pools:
                    attributes = {a.name: onnx.helper.get_attribute_value(a) for a in node.attribute}
                    self.assertLessEqual(int(np.prod(attributes["kernel_shape"])), 8)
                options = ort.SessionOptions()
                options.intra_op_num_threads = 4
                runtime = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
                weight, bias = (native.weight.detach().numpy().astype(np.float64),
                                native.bias.detach().numpy().astype(np.float64))
                for value in fixtures:
                    reference = oracle(value, groups, native.eps, weight, bias)
                    actual = runtime.run(["output"], {"input": value})[0]
                    np.testing.assert_allclose(actual, reference, rtol=2e-4, atol=2e-5)
                    with torch.inference_mode():
                        double = copy.deepcopy(native).double()(torch.from_numpy(value).double()).numpy()
                    np.testing.assert_allclose(double, reference, rtol=1e-9, atol=1e-10)
                    if value is near:
                        wrong_epsilon = oracle(value, groups, 1e-9, weight, bias)
                        self.assertFalse(np.allclose(actual, wrong_epsilon, rtol=2e-4, atol=2e-5))
            # Conversion must not silently change the independent reference.
            self.assertIs(type(native), torch.nn.GroupNorm)
            for key, value in native.state_dict().items():
                self.assertTrue(torch.equal(value, original_state[key]))
            with torch.no_grad():
                model[0].weight.add_(1)
            with torch.inference_mode():
                self.assertTrue(torch.equal(native(torch.from_numpy(near)), original_output))

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
