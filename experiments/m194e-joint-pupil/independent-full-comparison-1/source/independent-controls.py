"""Preregistered analytic and reference-instrument controls; preserves each run."""
import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "2"
import argparse
import dataclasses
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys
import traceback
import numpy as np
import scipy
from scipy.integrate import quad

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("independent_model", HERE/"independent-model.py")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    sources = {}
    for name in ("independent-model.py", "independent-controls.py", "independent-design.md"):
        shutil.copyfile(HERE/name, args.output/name)
        sources[name] = digest(HERE/name)
    result = dict(schema="m194e-independent-instrument-controls-v1", status="RUNNING",
                  sources=sources, argv=sys.argv, python=sys.version, numpy=np.__version__,
                  scipy=scipy.__version__, checks=[], registered_failure_policy="preserve first failure")
    budget = m.Budget()

    def check(name, actual, expected, tolerance, *, min_difference=None):
        error = float(np.max(np.abs(np.asarray(actual)-np.asarray(expected))))
        passed = error <= tolerance if min_difference is None else error >= min_difference
        entry = dict(name=name, actual=actual, expected=expected, max_abs_difference=error,
                     tolerance=tolerance, minimum_power=min_difference, passed=passed)
        result["checks"].append(entry)
        (args.output/"partial.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf8")
        if not passed:
            raise AssertionError(f"{name}: {error=}")

    def render(scene, frame, xy, cell=False, eps=.000125, **kw):
        return m.render(scene, frame, xy, cell=cell, eps=eps, budget=budget, **kw)[0]

    try:
        scene, frame, c, n = m.alternative_scene(), m.alternative_frame(), (37.23, 24.61), (12/13, 5/13)
        for dc in (0., 10000., 20000.):
            null = dataclasses.replace(scene, foreground=m.Radiance(dc), background=m.Radiance(dc))
            for xy in (c, (10., 12.), (70., 42.)):
                check(f"flat-first-{dc}-{xy}", render(null, frame, xy, True), dc, 1e-7)

        # Independent rectangular Fourier integral, including a clipped rectangle.
        for lo in (-.5, .1):
            poly = m.clip(m.SQUARE, (1., 0.), lo)
            for k in ((0., 0.), (.43, .79), (2.1, -.31), (-.72, 1.6)):
                real = quad(lambda x: quad(lambda y: math.cos(k[0]*x+k[1]*y), -.5, .5,
                                          epsabs=1e-12)[0], lo, .5, epsabs=1e-12)[0]
                imag = quad(lambda x: quad(lambda y: math.sin(k[0]*x+k[1]*y), -.5, .5,
                                          epsabs=1e-12)[0], lo, .5, epsabs=1e-12)[0]
                z = m.polygon_fourier(poly, k)
                check(f"polygon-fourier-{lo}-{k}", [z.real,z.imag], [real,imag], 1e-11)
        area, moment = m.moments(m.clip(m.SQUARE, (1., 0.), .1))
        check("polygon-area-first-moment", [area,*moment], [.4,.12,0.], 1e-14)

        d_f, d_b = 11*(.53-.8), 11*(.53-.4)
        for sign in (1., -1.):
            slope = sign*5/d_b
            bg = m.Radiance(15-slope*m.dot(n,c), (slope*n[0],slope*n[1]))
            rayscene = dataclasses.replace(scene, foreground=m.Radiance(30.), background=bg)
            values = m.evaluate_rays(rayscene, frame, c, [(-n[0],-n[1]), n])
            expected = [30., 20.] if sign == 1 else [30., 10.]
            check(f"R1-rays-{sign}", values, expected, 1e-10)
            check(f"R1-mean-{sign}", sum(values)/2, 25. if sign == 1 else 20., 1e-10)
            check(f"R1-separate-means-destroyer-{sign}", 22.5, sum(values)/2, 0., min_difference=2.)
            permuted = m.evaluate_rays(rayscene, frame, c, [n,(-n[0],-n[1])])
            check(f"R1-pupil-inversion-gauge-{sign}", sum(permuted)/2, sum(values)/2, 1e-10)

        for slope in (-800., 0., 800.):
            affine = m.alternative_scene("affine", slope)
            expected = 11000+slope*d_b*2/(3*math.pi)
            actual = render(affine, frame, c)
            check(f"R2-continuous-affine-{slope}", actual, expected, .02)
            if slope:
                check(f"R2-separate-means-{slope}", 11000., expected, 0., min_difference=200.)
                wrong = render(affine, frame, c, unsigned=True)
                check(f"R2-unsigned-{slope}", wrong, expected, 0., min_difference=400.)

        constants = m.alternative_scene("constant")
        for h in (-.73, -.21, .34, .81):
            xy = tuple(c[j]-h*abs(d_f)*n[j] for j in range(2))
            fraction = (math.acos(h)-h*math.sqrt(1-h*h))/math.pi
            expected = 9000+3000*fraction
            actual = render(constants, frame, xy)
            check(f"R3-disc-segment-{h}", actual, expected, .02)
            centre = m.evaluate_rays(constants, frame, xy, [(0.,0.)])[0]
            check(f"R3-pupil-centre-destroyer-{h}", centre, expected, 0., min_difference=100.)
        for side, xy in (("absent", (1.,1.)), ("full",(80.,60.))):
            a = render(constants, frame, xy)
            changed = dataclasses.replace(constants, foreground=m.Radiance(17000.)) if side == "absent" else dataclasses.replace(constants, background=m.Radiance(4000.))
            check(f"R3-hidden-layer-{side}", render(changed,frame,xy), a, 1e-8)
        # Focused foreground at its edge is deterministically foreground.
        check("R3-focused-foreground", render(constants,dataclasses.replace(frame,inverse_focus=.8),c),12000.,.02)

        for sign in (1.,-1.):
            cellscene = m.Scene(1.25,2.5,(1.,0.),.1,m.Radiance(30.),m.Radiance(10.,(sign*4,0.)))
            actual = render(cellscene,dataclasses.replace(frame,K=0.),(0.,0.),True)
            expected = 18-sign*.48
            check(f"R4-shared-cell-{sign}",actual,expected,.02)
            check(f"R4-separate-cell-means-{sign}",18.,expected,0.,min_difference=.4)
            check(f"R4-centre-sample-{sign}",m.evaluate_rays(cellscene,dataclasses.replace(frame,K=0.),(0.,0.),[(0.,0.)])[0],expected,0.,min_difference=1.)

        # Independent continuous affine half-disc moment after the chosen T.
        affine, transformed = m.alternative_scene("affine"), m.alternative_frame(True)
        def affine_point_oracle(fr):
            q0 = fr.transform(c)
            normal = fr.pull(n)
            length = math.hypot(*normal)
            normal = tuple(v/length for v in normal)
            cut = -(m.dot(n,q0)-affine.offset)/(d_f*length)
            bg_fraction = (math.acos(cut)-cut*math.sqrt(1-cut*cut))/math.pi
            first = 2*(1-cut*cut)**1.5/(3*math.pi)
            return 12000*(1-bg_fraction)+affine.background.value(q0)*bg_fraction+d_b*m.dot(fr.pull(affine.background.affine),normal)*first
        oracle = affine_point_oracle(transformed)
        check("R5-transformed-affine",render(affine,transformed,c),oracle,.02)
        q0 = transformed.transform(c)
        chief_only = dataclasses.replace(frame,b=(q0[0]-c[0],q0[1]-c[1]))
        check("R5-chief-only-destroyer",render(affine,chief_only,c),oracle,0.,min_difference=.02)
        # Exact polygon oracle for a tilted K0 cell, independent numerical path.
        no_pupil = dataclasses.replace(transformed,K=0.)
        q0 = no_pupil.transform(c)
        gn = no_pupil.pull(n)
        poly = m.clip(m.SQUARE,gn,affine.offset-m.dot(n,q0))
        area,mom = m.moments(poly)
        bgrad = no_pupil.pull(affine.background.affine)
        cell_oracle = 12000*area+affine.background.value(q0)*(1-area)-m.dot(bgrad,mom)
        check("R4-transformed-cell",render(affine,no_pupil,c,True),cell_oracle,.02)
        # Direct x/y quadrature on the same local K0 field, with exact y crossing.
        def column(dx):
            cut = (affine.offset-m.dot(n,q0)-gn[0]*dx)/gn[1]
            breaks = sorted(set([-.5,.5]+([cut] if -.5<cut<.5 else [])))
            return sum(quad(lambda dy: m.evaluate_rays(affine,no_pupil,(c[0]+dx,c[1]+dy),[(0.,0.)])[0],lo,hi,epsabs=1e-7)[0] for lo,hi in zip(breaks[:-1],breaks[1:]))
        xbreaks = sorted(set([-.5,.5]+[(affine.offset-m.dot(n,q0)-gn[1]*dy)/gn[0] for dy in (-.5,.5) if -.5<(affine.offset-m.dot(n,q0)-gn[1]*dy)/gn[0]<.5]))
        nested = sum(quad(column,lo,hi,epsabs=1e-7)[0] for lo,hi in zip(xbreaks[:-1],xbreaks[1:]))
        check("R4-nested-Cartesian-reduction",nested,cell_oracle,.0005)

        # Fixed re-chosen samples; all retained, no favorable subset.
        errors = []
        count = 0
        for shift in (0.,.137):
            texture = m.alternative_scene(shift=shift)
            for transformed_flag in (False,True):
                fr = m.alternative_frame(transformed_flag)
                points = []
                for y in (6,15,24,35,46,55):
                    base = (c[0]-5/12*(y-c[1]),float(y))
                    points.extend(tuple(base[j]+distance*n[j] for j in range(2)) for distance in (-4.1,-1.3,-.17,.29,1.7,4.7))
                    points.append(tuple(float(round(v)) for v in base))
                for xy in points:
                    for cell in (False,True):
                        primary = render(texture,fr,xy,cell)
                        refined = render(texture,fr,xy,cell,.0000078125)
                        errors.append(abs(primary-refined))
                        count += 1
        check("rechosen-reference-refinement",max(errors),0.,.0005)
        result["rechosen_evaluations"] = count
        result["status"] = "PASS_REFERENCE_INSTRUMENT_ONLY"
    except Exception as exc:
        result["status"] = "INSTRUMENT_INVALID" if not isinstance(exc,m.Refusal) else "UNCOMMISSIONED_NUMERICS"
        result["exception"] = str(exc)
        result["traceback"] = traceback.format_exc()
    finally:
        result["budget"] = budget.receipt()
        result["source_unchanged"] = all(digest(HERE/k)==v for k,v in sources.items())
        (args.output/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf8")
        print(json.dumps({k:result[k] for k in ("status","budget","source_unchanged")}))
    return 0 if result["status"]=="PASS_REFERENCE_INSTRUMENT_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
