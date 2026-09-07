"""M194b bounded producer. No RAW files or production algorithms are loaded.

M25 is imported from its frozen repository path; source files are never edited.
Public build_scalar/render_scalar/color_electrons APIs permit independent re-choice.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys

for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "2"

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
M25 = ROOT / "experiments/m25-simulator/src"
sys.path.insert(0, str(M25))
from strehl_sim import render, sensor as sensor_module
from strehl_sim.config import Breathing, Capture, Optics, Sensor
from strehl_sim.scene import Layer, Scene

PREREG = HERE / "producer-preregister.json"
P = json.loads(PREREG.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def array_sha(array) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def bindings() -> dict:
    out = {}
    for name, expected in P["frozen_m25_sha256"].items():
        path = M25 / "strehl_sim" / name
        actual = sha(path)
        if actual != expected:
            raise ValueError(f"frozen M25 hash mismatch: {name}")
        out[path.relative_to(ROOT).as_posix()] = actual
    track = ROOT / P["geometry"]["source"]
    if sha(track) != P["geometry"]["source_sha256"]:
        raise ValueError("published scale-track hash mismatch")
    ladder = json.loads(track.read_text())["ladder"]
    values = [float(np.exp(ladder[str(j)]["ln"] - ladder["144"]["ln"]))
              for j in P["geometry"]["rungs"]]
    values[4] = 1.0
    if not np.allclose(values, P["geometry"]["scales"], rtol=0, atol=2e-16):
        raise ValueError("frozen scale sequence differs from published derived values")
    out[track.relative_to(ROOT).as_posix()] = sha(track)
    out[Path(__file__).relative_to(ROOT).as_posix()] = sha(Path(__file__))
    return out


def configured_sensor(width=320, height=240):
    p = P["sensor"]
    return Sensor(model="M194b explicit synthetic coefficients", width=width,
                  height=height, black=p["black"], white=p["white"],
                  pixel_pitch_um=P["optics"]["pixel_pitch_um"], cfa="RGGB",
                  gain_divisor=640.0, base_iso=100.0, read_noise_e_low=4.0,
                  read_noise_e_high=4.0, second_base_iso=400.0, hot_fraction=0.0)


def wave_value(x, y, waves, phase_shift=0.0):
    result = np.zeros(np.broadcast_shapes(np.shape(x), np.shape(y)), dtype=np.float64)
    for amplitude, fx, fy, phase in waves:
        result += amplitude * np.cos(2*np.pi*(fx*x + fy*y) + phase + phase_shift)
    return result


def build_scalar(scene="plane", *, width=320, height=240, supersample=4,
                 margin=48, phase_shift=0.0, center=(183.0, 101.0),
                 scales=None, focuses=None, seed=701, noise=False):
    """Return scalar Scene and M25 config; canonical integer sensor centres.

    Independent callers may re-choose shape, S, phase, centre and scale/focus
    vectors without changing the frozen first benchmark parameters.
    """
    if scene not in ("flat", "plane"):
        raise ValueError("M25 path is deliberately scalar flat or plane")
    scales = np.array(P["geometry"]["scales"] if scales is None else scales, dtype=float)
    focuses = np.arange(len(scales), dtype=float) if focuses is None else np.asarray(focuses, dtype=float)
    if scales.shape != focuses.shape or scales.ndim != 1:
        raise ValueError("scale/focus shape mismatch")
    yy = (np.arange((height+2*margin)*supersample)[:,None]+.5)/supersample-margin-.5
    xx = (np.arange((width+2*margin)*supersample)[None,:]+.5)/supersample-margin-.5
    rad = np.full((len(yy), xx.shape[1]), P["scenes"][scene]["electron_dc"], dtype=float)
    if scene == "plane":
        rad += wave_value(xx, yy, P["scenes"]["plane"]["waves"], phase_shift)
    sc = Scene([Layer(rad, np.ones_like(rad), 4.0, scene)], supersample,
               (height, width), scene)
    cfg = render.RenderConfig(
        sensor=configured_sensor(width, height),
        optics=Optics(n_marked=8.0,magnification=1.0,pupil_ratio=1.0,wavelength_nm=535.0),
        capture=Capture(iso=160.0,n_frames=len(scales),coc_px_per_frame=1.5,gain_pp=0.0),
        breathing=Breathing(total_scale_change=0.0,
            centre_x_px=center[0]-width/2+.5-.5/supersample,
            centre_y_px=center[1]-height/2+.5-.5/supersample,
            tx_px=0.0,ty_px=0.0,rotation_rad=0.0),
        margin_px=margin,seed=seed,fpn=False,shot=noise,read=noise,
        gain_dn_per_e=.25,channel_scale=(.75,1.0,.6),
        chromatic_diffraction=False,with_diffraction=True,resampler_order=3,channels="rgb")
    return sc, cfg, scales, focuses


@contextlib.contextmanager
def observe_exposure(mode):
    """Delegate unmodified inputs; disabled placebo allocates matching storage.

    Scoped to this single-process producer. Never installed in another worker.
    """
    if mode not in ("original", "on", "placebo"):
        raise ValueError(mode)
    original = render.expose
    cached, visits = [], []
    def delegate(electrons, *args, **kwargs):
        visits.append({"shape":list(electrons.shape), "dtype":str(electrons.dtype)})
        if mode == "on":
            cached.append(np.array(electrons, dtype=np.float64, copy=True))
        else:
            # Real allocation/write with observation disabled; data not used.
            scratch = np.empty(electrons.shape, dtype=np.float64)
            scratch.fill(0.0)
        return original(electrons, *args, **kwargs)
    try:
        if mode != "original":
            render.expose = delegate
        yield cached, visits
    finally:
        render.expose = original


def render_scalar(scene="plane", *, observer="on", **kwargs):
    sc, cfg, scales, focuses = build_scalar(scene, **kwargs)
    original = render.expose
    with observe_exposure(observer) as (cached, visits):
        stack = render.render_stack(sc, cfg, scale_series=scales,
            gain_series=np.ones(len(scales)),focus_planes=focuses)
    if render.expose is not original:
        raise AssertionError("exposure delegate not restored")
    return stack.frames, (np.stack(cached) if cached else None), visits


def integrated_wave(x,y,waves, *, scale=1.0, center=(183.,101.), phase_shift=0.0):
    """Independent continuous unit-cell integration in each source frame.

    Frame z samples q=c+(z-c)/scale. The transformed frequency is f/scale.
    This is analytic sensor irradiance; it claims no chromatic PSF model.
    """
    qx = center[0] + (x-center[0])/scale
    qy = center[1] + (y-center[1])/scale
    out = np.zeros(np.broadcast_shapes(np.shape(x),np.shape(y)))
    for a,fx,fy,phase in waves:
        out += a*np.sinc(fx/scale)*np.sinc(fy/scale)*np.cos(
            2*np.pi*(fx*qx+fy*qy)+phase+phase_shift)
    return out


def analytic_color_rgb(*, width=320,height=240,scale=1.,center=(183.,101.),
                       phase_shift=0.,chroma=True):
    x,y = np.arange(width)[None,:],np.arange(height)[:,None]
    p = P["scenes"]["color"]
    args = dict(scale=scale,center=center,phase_shift=phase_shift)
    light = p["dc"] + integrated_wave(x,y,p["luminance_waves"],**args)
    redblue = integrated_wave(x,y,p["red_blue_chroma"],**args) if chroma else 0.
    green = integrated_wave(x,y,p["green_chroma"],**args) if chroma else 0.
    return np.stack((light+redblue,light+green,light-redblue),axis=-1)


def color_electrons(*, width=320,height=240,scales=None,center=(183.,101.),
                    phase_shift=0.,chroma=True):
    scales = P["geometry"]["scales"] if scales is None else scales
    return np.stack([sensor_module.mosaic(analytic_color_rgb(width=width,height=height,
        scale=s,center=center,phase_shift=phase_shift,chroma=chroma) /
        np.array(P["sensor"]["wb"])[None,None,:] / .25) for s in scales])


def expose_cached(expected, *, seed=701,noise=True):
    rng = np.random.default_rng(seed)
    sensor = configured_sensor(expected.shape[2],expected.shape[1])
    return np.stack([sensor_module.expose(e,160.,sensor,None,rng,
        shot=noise,read=noise,gain_dn_per_e=.25) for e in expected])


def manifest_for(scene, repeat, files, expected_hash, sources, command):
    return {"schema":"m194b-known-scene-v1", "scene":scene,
        "noise_enabled":repeat is not None,"repeat":repeat,"sensor":P["sensor"],
        "geometry":{"reference_index":4,"scale_centre_native":[183.,101.],
            "frames":[{"index":k,"focus":float(k),"scale":s}
                      for k,s in enumerate(P["geometry"]["scales"])]},
        "frames":files, "producer":{"preregistration_sha256":sha(PREREG),
            "source_sha256":sources,"expected_electrons_sha256":expected_hash,
            "command":command}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--commission",type=Path,required=True)
    args = parser.parse_args()
    sources = bindings()
    commission = json.loads(args.commission.read_text())
    if commission.get("preregistration_sha256") != sha(PREREG):
        raise ValueError("commission belongs to different preregistration")
    if commission.get("producer_sha256") != sha(Path(__file__)):
        raise ValueError("commission belongs to different producer source")
    required = {
        "flat":["flat-dc","aperture-cfa-quantization","noise-law","observer-on-off-placebo"],
        "plane":["flat-dc","aperture-cfa-quantization","noise-law","observer-on-off-placebo",
                 "defocus-diffraction","plane-numerical-convergence"],
        "color":["aperture-cfa-quantization","analytic-color-geometry"],
        "color-null":["aperture-cfa-quantization","analytic-color-geometry"]}
    args.out.mkdir(parents=True,exist_ok=False)
    summary = {"schema":"m194b-producer-result-v1","status":"running", "manifests":[],"refused_scenes":{},
               "commission_sha256":sha(args.commission),"sources_before":sources,
               "preregistration_sha256":sha(PREREG)}
    write_json(args.out/"producer-result.json",summary)
    for scene in ("flat","plane","color","color-null"):
        failed = [name for name in required[scene] if commission["groups"][name]["status"] != "pass"]
        if failed:
            summary["refused_scenes"][scene]=failed
            write_json(args.out/"producer-result.json",summary)
            print(f"refused {scene}: {failed}",flush=True)
            continue
        if scene in ("color","color-null"):
            expected = color_electrons(chroma=scene=="color")
        else:
            cached_path = args.commission.parent/commission["cache"][scene]["path"]
            if sha(cached_path) != commission["cache"][scene]["sha256"]:
                raise ValueError("cache byte binding failed")
            expected = np.load(cached_path,allow_pickle=False)
        if expected.shape != (9,240,320) or not np.isfinite(expected).all():
            raise ValueError("expected-electron shape/finiteness failure")
        cache_path = args.out/f"{scene}-expected-electrons.npy"
        np.save(cache_path,expected,allow_pickle=False)
        seeds = P["scenes"][scene]["noise_seeds"]
        for repeat in [None]+seeds:
            label = "noise-off" if repeat is None else f"seed-{repeat}"
            case = args.out/scene/label
            (case/"frames").mkdir(parents=True)
            raw = expose_cached(expected,seed=701 if repeat is None else repeat,noise=repeat is not None)
            files=[]
            rails=int(np.count_nonzero((raw==0)|(raw==15360)))
            if rails:
                raise AssertionError("unexpected benchmark source rails")
            for k,frame in enumerate(raw):
                path=case/"frames"/f"frame-{k:02}.cfa"
                frame.astype("<u2").tofile(path)
                files.append({"index":k,"path":path.relative_to(case).as_posix(),
                              "bytes":path.stat().st_size,"sha256":sha(path)})
            manifest=manifest_for(scene,repeat,files,sha(cache_path),sources,sys.argv)
            path=case/"manifest.json"
            write_json(path,manifest)
            summary["manifests"].append({"path":path.relative_to(args.out).as_posix(),
                                        "sha256":sha(path),"source_rail_count":rails})
            write_json(args.out/"producer-result.json",summary)
        print(f"produced {scene}: {1+len(seeds)} variants",flush=True)
    summary["sources_after"]=bindings()
    if summary["sources_after"]!=sources:
        raise AssertionError("source binding changed")
    summary["status"]="complete" if not summary["refused_scenes"] else "partial-refusal"
    write_json(args.out/"producer-result.json",summary)
    print(json.dumps({"status":summary["status"],"manifests":len(summary["manifests"]),
                      "output":str(args.out.resolve())}))
    if summary["refused_scenes"]:
        raise SystemExit(2)


if __name__=="__main__":
    main()
