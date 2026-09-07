"""Additive registered controls. Definitions only until the joint execution gate."""
from contextlib import contextmanager
from fractions import Fraction as F
import hashlib
import json
import math
import struct
import traceback
import warnings

INTERVALS = (
    ('A', -.875, -.125), ('B', .125, .625), ('C', -.3125, .9375), ('D', -1., 1.),
    ('E', -1., float.fromhex('-0x1.ffffffffffff9p-1')),
    ('F', float.fromhex('0x1.fffffffffffe9p-1'), 1.))
POLYNOMIALS = (('constant', (2., 0., 0.)), ('affine', (3., 2., 0.)),
               ('signed', (-.375, 1., 0.)), ('quadratic', (1., 1., 1.)))


@contextmanager
def patched(obj, name, value):
    original = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, original)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def run(r, budget, catalog, output, check):
    """Use the caller's single live budget; no clock/counter reset here."""
    ni = r.ni
    started = budget.receipt()
    result = dict(schema='m194g-normalized-interval-controls-v1', status='RUNNING',
                  method=r.METHOD, direct=[], faults=[], checks=[], work_before=started,
                  work_after=None, exception=None, traceback=None)
    original_quad = r.quad
    original_cartesian_quad = r.m.quad

    def publish(name, passed, evidence):
        item = dict(name='normalized-interval-'+name, passed=bool(passed), evidence=evidence)
        result['checks'].append(item)
        check(item['name'], item['passed'], item['evidence'])

    def polynomial(interval, poly, mode='off'):
        ident, a, b = interval
        pname, coeff = poly
        width = b-a
        scale = width*max(1., sum(abs(x) for x in coeff))
        request = 2.**-40*scale
        limit = 256.*2.**-52*scale
        fa, fb = F(a), F(b)
        oracle = sum(F(c)*(fb**(j+1)-fa**(j+1))/(j+1) for j,c in enumerate(coeff))
        hooks = 0
        collected = []
        delegated = []
        call_hash = hashlib.sha256()
        delegated_calls = 0
        work_before = budget.evaluations
        def observer(u, t, value, weighted):
            nonlocal hooks
            hooks += 1
            if mode == 'count':
                collected.append([u.hex(), t.hex(), float(value).hex(), float(weighted).hex()])
        normalizer = ni.Normalizer(r.TARGETS['primary'], None if mode == 'off' else observer)
        def function(t):
            budget.tick()
            return coeff[0]+coeff[1]*t+coeff[2]*t*t
        def observed_quad(fn, lo, hi, **kwargs):
            nonlocal delegated_calls
            item = dict(left=lo, right=hi, kwargs=dict(kwargs), returned=None)
            delegated.append(item)
            def observed(u):
                nonlocal delegated_calls
                value = fn(u)
                delegated_calls += 1
                call_hash.update(struct.pack('<dd', u, value))
                return value
            pair = original_quad(observed, lo, hi, **kwargs)
            item['returned'] = list(pair)
            return pair
        row = dict(interval=ident, polynomial=pname, mode=mode, a=a, b=b, coefficients=list(coeff),
                   request=request, error_limit=limit, oracle_fraction=str(oracle), value=None, indicator=None,
                   exception=None, warnings=[], delegated=delegated, numerical_ok=False, delegation_ok=False)
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always', r.IntegrationWarning)
                value, indicator = normalizer.quad(observed_quad, function, a, b,
                                                   epsabs=request, epsrel=0., limit=128)
            row['warnings'] = [dict(category=w.category.__name__, message=str(w.message)) for w in caught]
            row.update(value=value, indicator=indicator)
            row['numerical_ok'] = (math.isfinite(value) and math.isfinite(indicator) and 0 <= indicator <= request
                                   and not caught and abs(F(value)-oracle) <= F(limit))
            row['delegation_ok'] = (len(delegated) == 1 and delegated[0]['left'] == 0. and delegated[0]['right'] == 1.
                                    and canonical(delegated[0]['kwargs']) == canonical(dict(epsabs=request, epsrel=0., limit=128))
                                    and struct.pack('<dd', *delegated[0]['returned']) == struct.pack('<dd', value, indicator)
                                    and delegated_calls > 0)
        except Exception as exc:
            row['exception'] = repr(exc)
        row.update(hook_calls=hooks, collected=collected, normalized=normalizer.receipt(),
                   actual_integrand_calls=budget.evaluations-work_before,
                   delegated_callbacks=delegated_calls, delegated_sample_sha256=call_hash.hexdigest())
        row['accounting_ok'] = (row['actual_integrand_calls'] == normalizer.integrand_calls == delegated_calls
                                and normalizer.intervals == 1)
        row['signature'] = dict(value=None if row['value'] is None else float(row['value']).hex(),
                                indicator=None if row['indicator'] is None else float(row['indicator']).hex(),
                                callbacks=delegated_calls, samples=call_hash.hexdigest(),
                                warnings=row['warnings'], exception=row['exception'])
        budget.check()
        return row

    try:
        baseline = {}
        for interval in INTERVALS:
            for poly in POLYNOMIALS:
                for mode in ('off', 'count', 'placebo'):
                    row = polynomial(interval, poly, mode)
                    result['direct'].append(row)
                    baseline[interval[0], poly[0], mode] = row
        publish('polynomial-oracles', len(result['direct']) == 72 and all(x['numerical_ok'] for x in result['direct']),
                dict(rows=result['direct'], expected_rows=72))
        publish('delegated-request', all(x['delegation_ok'] for x in result['direct']),
                dict(checked_calls=72, convention='same physical epsabs, weighted callback, unscaled returned pair'))
        equal = True
        for interval in INTERVALS:
            for poly in POLYNOMIALS:
                off, count, placebo = [baseline[interval[0],poly[0],mode] for mode in ('off','count','placebo')]
                equal &= canonical(off['signature']) == canonical(count['signature']) == canonical(placebo['signature'])
                equal &= off['hook_calls'] == len(off['collected']) == 0
                equal &= count['hook_calls'] == len(count['collected']) == count['delegated_callbacks'] > 0
                equal &= placebo['hook_calls'] == count['hook_calls'] and placebo['collected'] == []
        publish('observer-null', equal, dict(pairs=24, modes=['off','count','placebo'], active_count_collection=True))

        nodes = []
        unit_nodes = (0., 2.**-20, .25, .5, .75, 1.-2.**-20, 1.)
        for ident,a,b in INTERVALS:
            mapped = []
            def driver(fn, lo, hi, **kwargs):
                for u in unit_nodes:
                    fn(u)
                return (0., 0.)
            def function(t):
                budget.tick()
                mapped.append(t)
                return 1.
            n = ni.Normalizer(r.TARGETS['primary'])
            n.quad(driver, function, a, b, epsabs=1e-6, epsrel=0., limit=128)
            good = mapped[0].hex() == a.hex() and mapped[-1].hex() == b.hex() and mapped == sorted(mapped)
            for u,t in zip(unit_nodes,mapped):
                exact = F(a)+(F(b)-F(a))*F(u)
                tolerance = 2*max(math.ulp(a),math.ulp(b),math.ulp(float(exact)))
                good &= abs(F(t)-exact) <= F(tolerance)
            nodes.append(dict(interval=ident, mapped_hex=[t.hex() for t in mapped], passed=bool(good)))
        invalid = []
        for a,b in ((0.,0.),(.5,-.5),(-2.,0.),(0.,2.),(float('nan'),1.),(-1.,float('inf'))):
            touched = []
            def forbidden(*args,**kwargs):
                touched.append(True)
                return 0.,0.
            rejected = False
            try:
                ni.Normalizer(r.TARGETS['primary']).quad(forbidden, lambda t: 0., a,b,epsabs=1e-6,epsrel=0.,limit=128)
            except ni.IntervalRefusal:
                rejected = True
            invalid.append(dict(domain=[repr(a),repr(b)], refused=rejected, dependency_untouched=not touched))
        for u in (-.125,1.125,float('nan'),float('inf')):
            touched = []
            def bad_node(fn,lo,hi,**kwargs):
                fn(u)
                return 0.,0.
            rejected = False
            try:
                ni.Normalizer(r.TARGETS['primary']).quad(bad_node, lambda t: touched.append(t) or 0., -.5,.5,epsabs=1e-6,epsrel=0.,limit=128)
            except ni.IntervalRefusal:
                rejected = True
            invalid.append(dict(unit=repr(u), refused=rejected, integrand_untouched=not touched))
        publish('node-domain', all(x['passed'] for x in nodes) and all(x['refused'] and all(v for k,v in x.items() if k.endswith('untouched')) for x in invalid),
                dict(mapped=nodes, invalid=invalid))

        def fault(name, field, function, interval, poly, contract=False):
            before = baseline[interval[0],poly[0],'off']
            with patched(ni, field, function):
                changed = polynomial(interval,poly)
            restored = polynomial(interval,poly)
            live = changed['delegated_callbacks'] > 0
            returned = (changed['exception'] is None and isinstance(changed['value'],float)
                        and math.isfinite(changed['value']))
            scalar_error = (abs(F(changed['value'])-F(changed['oracle_fraction'])) if returned else None)
            actual_request = (changed['delegated'][0]['kwargs'].get('epsabs')
                              if len(changed['delegated']) == 1 else None)
            request_changed = (isinstance(actual_request,float) and math.isfinite(actual_request)
                               and struct.pack('<d',actual_request) != struct.pack('<d',changed['request']))
            detected = request_changed if contract else scalar_error is not None and scalar_error > F(changed['error_limit'])
            passed = (before['numerical_ok'] and before['delegation_ok'] and live and detected
                      and returned
                      and restored['numerical_ok'] and restored['delegation_ok']
                      and canonical(before['signature']) == canonical(restored['signature']))
            rec = dict(name=name, active=changed, restored=restored, baseline_signature=before['signature'],
                       actual_scalar_error_fraction=None if scalar_error is None else str(scalar_error),
                       actual_scalar_error=None if scalar_error is None else float(scalar_error),
                       delegated_request_bitwise_changed=request_changed,
                       scope='delegated-call contract' if contract else 'scalar oracle', passed=passed)
            result['faults'].append(rec)
            return rec
        jacobian = []
        for interval in (INTERVALS[1],INTERVALS[4],INTERVALS[5]):
            jacobian.append(fault('omit-jacobian','weighted_sample',lambda v,w:v,interval,POLYNOMIALS[0]))
            jacobian.append(fault('repeat-jacobian','returned_integral',lambda pair,w:(pair[0]*w,pair[1]*w),interval,POLYNOMIALS[0]))
        publish('jacobian-faults', all(x['passed'] for x in jacobian), dict(cases=jacobian))
        interpolation = [fault('left-half','coordinate',lambda a,b,w,u:a+(w/2)*u,INTERVALS[2],POLYNOMIALS[1]),
                         fault('midpoint','coordinate',lambda a,b,w,u:(a+b)/2,INTERVALS[2],POLYNOMIALS[3])]
        publish('interpolation-faults', all(x['passed'] for x in interpolation), dict(cases=interpolation, midpoint_constant_affine='inert by polynomial identity'))
        requests = []
        for interval in (INTERVALS[1],INTERVALS[2]):
            requests.append(fault('request-divide-width','absolute_request',lambda e,w:e/w,interval,POLYNOMIALS[0],True))
            requests.append(fault('request-multiply-width','absolute_request',lambda e,w:e*w,interval,POLYNOMIALS[0],True))
        publish('request-faults', all(x['passed'] for x in requests), dict(cases=requests))

        case = next(c for c in catalog['cases'] if c['id'] == 'geometry-004')
        prepared = r.case_input(catalog,case)
        xy = tuple(case['native_xy'])
        target = r.TARGETS['primary']
        def actual_render():
            engine = r.Engine(budget,target)
            before = budget.receipt()
            row = dict(status='REFUSED', value=None, receipt=None, error=None)
            try:
                value, receipt = engine.render(prepared,xy,cell=True)
                row.update(status='VALUE',value=value,receipt=receipt)
            except Exception as exc:
                row['error'] = repr(exc)
            row.update(engine=engine.receipt(),work_before=before,work_after=budget.receipt())
            return row
        legacy = None
        try:
            r.m.render(prepared.scene,prepared.frame,xy,cell=True,eps=target,budget=budget)
        except r.Refusal as exc:
            legacy = str(exc)
        good_geometry = actual_render()
        publish('historical-refusal', legacy is not None and 'Extremely bad integrand behavior' in legacy and good_geometry['status'] == 'VALUE',
                dict(case_id=case['id'], legacy_refusal=legacy, normalized=good_geometry))

        def warning_quad(fn,lo,hi,**kwargs):
            fn(.375)
            warnings.warn('normalized-interval-control-warning',r.IntegrationWarning)
            return 0.,0.
        with patched(r.m,'quad',warning_quad):
            warning_good = actual_render()
        original_normalized_quad = ni.Normalizer.quad
        def swallowed(self,*args,**kwargs):
            with warnings.catch_warnings(record=True):
                warnings.simplefilter('always',r.IntegrationWarning)
                return original_normalized_quad(self,*args,**kwargs)
        with patched(r.m,'quad',warning_quad), patched(ni.Normalizer,'quad',swallowed):
            warning_bad = actual_render()
        with patched(r.m,'quad',warning_quad):
            warning_restored = actual_render()
        class Sentinel(RuntimeError):
            pass
        exceptional = []
        for which in ('callback','quad'):
            def fail_quad(*args,**kwargs):
                raise Sentinel('quad')
            def fail_callback(t):
                budget.tick()
                raise Sentinel('callback')
            found = None
            raw = fail_quad if which == 'quad' else original_cartesian_quad
            with patched(r.m,'quad',raw):
                try:
                    with ni.Normalizer(target).installed(r.m):
                        r.m.quad(fail_callback,-.5,.5,epsabs=1e-6,epsrel=0.,limit=128)
                except Sentinel as exc:
                    found = str(exc)
                inside_restored = r.m.quad is raw
            exceptional.append(dict(kind=which, sentinel=found, passed=found==which and inside_restored and r.m.quad is original_cartesian_quad and r.quad is original_quad))
        nested = False
        with ni.Normalizer(target).installed(r.m):
            try:
                with ni.Normalizer(target).installed(r.m):
                    pass
            except ni.IntervalRefusal:
                nested = True
        warning_pass = (warning_good['status'] == warning_restored['status'] == 'REFUSED'
                        and warning_good['error'] == warning_restored['error']
                        and 'normalized-interval-control-warning' in warning_good['error']
                        and warning_bad['status'] == 'VALUE'
                        and all(x['passed'] for x in exceptional) and nested
                        and r.m.quad is original_cartesian_quad and r.quad is original_quad)
        publish('warning-and-restoration',warning_pass,dict(valid=warning_good,suppressed=warning_bad,restored=warning_restored,exceptions=exceptional,nested_refused=nested))

        def factor():
            before = budget.factor_evaluations
            value, receipt = r.integrate_factor('disc',4.5,1e-6,budget)
            return dict(value=value,receipt=receipt,calls=budget.factor_evaluations-before)
        factor_before = factor()
        scoped = ni.Normalizer(target)
        with scoped.installed(r.m):
            factor_inside = factor()
        factor_after = factor()
        original_installed = ni.Normalizer.installed
        with patched(ni.Normalizer,'installed',lambda self,module:original_installed(self,r)):
            wrong_dependency = actual_render()
        both_error = None
        both = ni.Normalizer(target)
        with both.installed(r.m):
            try:
                with both.installed(r):
                    factor()
            except ni.IntervalRefusal as exc:
                both_error = str(exc)
        restored_geometry = actual_render()
        dependency_pass = (canonical(factor_before)==canonical(factor_inside)==canonical(factor_after)
                           and factor_before['calls'] > 0 and scoped.intervals == scoped.integrand_calls == 0
                           and wrong_dependency['status'] == 'REFUSED'
                           and 'Extremely bad integrand behavior' in (wrong_dependency['error'] or '')
                           and wrong_dependency['engine']['normalization']['intervals'] == 0
                           and both_error is not None and 'outside pupil domain' in both_error
                           and restored_geometry['status'] == 'VALUE'
                           and struct.pack('<d',restored_geometry['value']) == struct.pack('<d',good_geometry['value'])
                           and r.m.quad is original_cartesian_quad and r.quad is original_quad)
        publish('dependency-scope',dependency_pass,dict(factor_before=factor_before,factor_inside=factor_inside,factor_after=factor_after,
                wrong_dependency=wrong_dependency,both_dependencies_error=both_error,restored_geometry=restored_geometry))
        numerical_accounting = good_geometry['status'] == 'VALUE'
        if numerical_accounting:
            n = good_geometry['receipt']['normalization']
            numerical_accounting &= (n['intervals'] == good_geometry['receipt']['intervals'] == good_geometry['engine']['normalization']['intervals'] > 0
                                     and n['integrand_calls'] == good_geometry['engine']['normalization']['integrand_calls']
                                     == good_geometry['work_after']['chord_evaluations']-good_geometry['work_before']['chord_evaluations'] > 0)
        publish('complete-accounting',len(result['direct']) == 72 and all(x['accounting_ok'] for x in result['direct']) and numerical_accounting,
                dict(direct_calls=72, mandatory_accounting='independent of optional hook', numerical_geometry=good_geometry))
        budget.check()
        result['status'] = 'PASS_NORMALIZED_INTERVAL_CONTROLS_ONLY' if len(result['checks']) == 11 and all(x['passed'] for x in result['checks']) else 'UNCOMMISSIONED_NORMALIZED_INTERVAL_CONTROLS'
    except Exception as exc:
        result['status'] = 'UNCOMMISSIONED_NORMALIZED_INTERVAL_CONTROLS'
        result['exception'], result['traceback'] = repr(exc), traceback.format_exc()
    finally:
        result['work_after'] = budget.receipt()
        result['dependencies_restored'] = r.m.quad is original_cartesian_quad and r.quad is original_quad
        if not result['dependencies_restored']:
            result['status'] = 'UNCOMMISSIONED_NORMALIZED_INTERVAL_CONTROLS'
        r.write_json(output/'normalized-interval-controls.json',result)
        budget.check()
    return result
