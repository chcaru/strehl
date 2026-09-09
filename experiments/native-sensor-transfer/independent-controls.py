"""Twenty fixed private/control groups for the independent native transfer reader.
Source-only until the root release. This module imports no numerical library or
producer; the already-authenticated entry point supplies its independent modules.
No fixture, source or RAW is opened here. Actual-evidence controls complete later.
"""
import copy
import math
from types import SimpleNamespace

IDS = tuple(f'{i:02d}' for i in range(1, 21))
NAMES = ('owned-decode-lifetime', 'same-raw-address', 'camera-white-policy',
         'paper-temporal-estimator', 'dark-temporal-estimator', 'matched-covariance',
         'disjoint-signal-reference', 'immutable-model-and-q-scale', 'clamp-domain',
         'finite-stencil-boundary', 'phase-taps-temporal-axis', 'energy-is-not-noise',
         'input-headroom', 'input-illumination', 'input-motion', 'route-beta-scope',
         'observer-byte-neutrality', 'weight-branches', 'conditional-quantiles',
         'saved-execution-authority')


class Suite:
    def __init__(self, np, numerics, decode, tick):
        self.np, self.n, self.d, self.tick = np, numerics, decode, tick
        self.rows = {i: {'id': i, 'name': name, 'status': 'UNVISITED', 'variants': []}
                     for i, name in zip(IDS, NAMES)}
        self.active = None

    def start(self, i):
        self.tick()
        self.n.need(self.rows[i]['status'] == 'UNVISITED', 'control group visited twice')
        self.active = self.rows[i]
        self.active['status'] = 'RUNNING'

    def check(self, name, operation, error=None, evidence=None):
        self.tick()
        row = {'name': name, 'expected_error': error, 'observed_error': None, 'passed': False}
        if evidence is not None:row['evidence']=evidence
        self.active['variants'].append(row)
        try:
            value = operation()
            self.n.need(error is None, 'destroyer did not refuse')
            self.n.need(value is True, 'control positive must return literal True')
            row['passed'] = True
        except ValueError as exc:
            row['observed_error'] = str(exc)
            if error is not None and str(exc) == error:
                row['passed'] = True
            else:
                raise
        self.tick()

    def fact(self, test, reason):
        self.n.need(bool(test), reason)
        return True

    def end(self, pending=False):
        self.n.need(self.active['variants'] and all(v['passed'] for v in self.active['variants']),
                    'empty or failed control group')
        self.active['status'] = 'PENDING_ACTUAL' if pending else 'PASS'
        self.active = None

    def reopen(self, i):
        self.tick()
        self.n.need(self.rows[i]['status'] == 'PENDING_ACTUAL', 'actual control completion state')
        self.active = self.rows[i]
        self.active['status'] = 'RUNNING'

    def output(self, complete=False):
        rows = [self.rows[i] for i in IDS]
        if complete:
            self.n.need(all(r['status'] == 'PASS' for r in rows), '20 complete control groups required')
        return rows

    def temporal_literal(self):
        return self.np.asarray([996., 1004., 996., 1004., 1000.]).reshape(5, 1)

    def initial(self):
        np, n, d = self.np, self.n, self.d
        self.start('01')
        raw = SimpleNamespace(raw_image=np.fromfunction(lambda y,x: 500+31*y+3*x,(12,16),dtype=int).astype('uint16'),
                              sizes=SimpleNamespace(raw_height=12,raw_width=16), color_desc=b'RGBG',
                              raw_color=lambda y,x: ((0,1),(3,2))[y%2][x%2])
        raw.raw_image_visible = np.zeros((10,14),dtype='uint16')
        owned, metadata = d.owned_roi(raw,np,(4,2,8,6),(12,16))
        expected = np.fromfunction(lambda y,x: 500+31*(y+2)+3*(x+4),(6,8),dtype=int).astype('uint16')
        self.check('literal-copy-address', lambda: self.fact(np.array_equal(owned,expected) and
                   metadata['letters']==['R','G','G','B'], 'literal owned address'))
        self.check('borrowed-view-refuses',lambda:d.owned_roi(raw,np,(4,2,8,6),(12,16),copy=False),
                   'owned sensor copy inside lifetime')
        raw.raw_image.fill(0)
        self.check('poison-after-close-surrogate',lambda:self.fact(np.array_equal(owned,expected), 'owned lifetime witness'))
        raw.raw_image[:] = np.fromfunction(lambda y,x:500+31*y+3*x,(12,16),dtype=int).astype('uint16')
        self.check('restored-copy',lambda:self.fact(np.array_equal(d.owned_roi(raw,np,(4,2,8,6),(12,16))[0],expected), 'restored copy'))
        self.end()

        self.start('02')
        correct,_=d.owned_roi(raw,np,(4,2,8,6),(12,16)); shifted,_=d.owned_roi(raw,np,(6,2,8,6),(12,16))
        expected_bytes=correct.astype('<u2').tobytes(); _,row_hashes=d.roi_hashes(correct,np)
        def roi_test(value):
            d.compare_roi(value,expected_bytes,row_hashes,np)
            return True
        self.check('same-buffer-same-address',lambda:roi_test(correct))
        self.check('two-column-shift',lambda:roi_test(shifted),'whole sensor ROI u16 disagreement')
        self.check('restored-address',lambda:roi_test(correct))
        self.end()

        self.start('03')
        wm={'indices':[0,1,3,2],'letters':['R','G','G','B'],'black':[512]*4,
            'generic_white':16383,'camera_white':[12000]*4}
        primary={'black':512,'white':12000}
        def white(value):
            v=d.white_authority(value,primary)
            return v['selected_white']==12000 and v['method']=='equal-positive-used-camera-channels'
        self.check('camera-white-positive',lambda:white(wm))
        variants=(('wrong-camera', [11000]*4,12000,'selected camera white disagrees with primary'),
                  ('mixed-camera',[12000,12000,11000,12000],16383,'mixed used-channel camera white'),
                  ('absent-camera',None,12000,'camera white metadata required; no generic fallback'),
                  ('bool-camera',[12000,True,12000,12000],16383,'camera white positive integer entries'))
        for name,camera,generic,error in variants:
            changed={**wm,'camera_white':camera,'generic_white':generic}
            self.check(name,lambda v=changed:white(v),error)
            self.check(name+'-restored',lambda:white(wm))
        self.end()

        self.start('04')
        a=self.temporal_literal(); t=n.temporal(a)
        self.check('literal-pair-and-all',lambda:self.fact(t['pair_df']==2 and t['all_df']==4 and
                   float(t['pair_variance'][0])==32 and float(t['all_variance'][0])==16,'paper literal variance'))
        self.check('centered-pair-destroyer',lambda:n.same_real(np.zeros(1),t['pair_variance']), 'binary64 prediction disagreement')
        self.check('factor-two-destroyer',lambda:n.same_real(t['pair_variance']*2,np.asarray([32.])), 'binary64 prediction disagreement')
        self.check('restored-paper',lambda:n.same_real(n.temporal(a)['pair_variance'],np.asarray([32.])))
        self.end()

        self.start('05')
        dark=np.asarray([996.,1004.]*11).reshape(22,1); td=n.temporal(dark)
        self.check('eleven-pair-literal',lambda:self.fact(td['pair_df']==11 and td['all_df']==21 and
                   float(td['pair_variance'][0])==32 and float(td['all_variance'][0])==352/21,'dark literal variance'))
        self.check('population-divisor',lambda:n.same_real(np.asarray([16.]),td['all_variance']), 'binary64 prediction disagreement')
        self.check('missing-dark-pair',lambda:n.temporal(dark[:-2]),'fixed temporal population')
        self.check('restored-dark',lambda:n.same_real(n.temporal(dark)['pair_variance'],np.asarray([32.])))
        self.end()

        self.start('06')
        equal=n.covariance(a,a); opposite=n.covariance(a,2000-a)
        self.check('same-green-covariance',lambda:self.fact(float(equal[0][0])==32 and float(opposite[0][0])==-32 and
                   float(n.temporal((a+a)/2)['pair_variance'][0])==32 and
                   float(n.temporal((a+2000-a)/2)['pair_variance'][0])==0,'literal matched covariance'))
        self.check('false-green-independence',lambda:n.same_real(np.asarray([16.]),np.asarray([32.])), 'binary64 prediction disagreement')
        fields=np.broadcast_to(a.reshape(5,1,1),(5,128,128)).copy()
        counts=[]
        for p in range(4):
            for dx,dy in ((1,0),(0,1),(1,1),(1,-1)):
                left,right=n.overlap(fields,fields,dx,dy); cov=n.covariance(left,right)[0]
                counts.append(cov.size)
                self.check(f'plane-{p}-offset-{dx}-{dy}',lambda c=cov:n.same_real(c,np.full(c.shape,32.)))
        self.active['neighbour_scope']='Constant neighbour witness powers sign/covariance/overlap counts; it cannot reject a wrong address with the same constant data and shape.'
        self.check('overlap-counts',lambda:self.fact(counts==[16256,16256,16129,16129]*4,'neighbour literal overlap'))
        self.check('restored-green',lambda:n.same_real(n.covariance(a,a)[0],np.asarray([32.])))
        self.end()

        gains=[n.f32(n.f32(160)/n.f32(436.8))]*4; rn=[n.f32(4.2)]*4
        self.start('07')
        reference=np.full((256,256),1512,dtype='uint16'); changed=reference+np.uint16(16)
        reference_role={'original_ordinals':[4],'estimator':'single-held-frame4'}
        qa,qg,_,_=n.prediction(reference,512,gains,rn,reference_role); qb,qgb,_,_=n.prediction(changed,512,gains,rn,reference_role)
        self.check('held-signal-disjoint',lambda:n.same_real(n.temporal(a)['pair_variance'],np.asarray([32.])))
        self.check('plane-sixteen-g',lambda:n.same_real(qb-qa,np.full(qa.shape,16*gains[0])))
        self.check('green-eight-g',lambda:n.same_real(qgb-qg,np.full(qg.shape,8*gains[0])))
        self.check('all-five-signal-substitution',lambda:n.prediction(reference,512,gains,rn,{'original_ordinals':[0,1,2,3,4],'estimator':'all-five-mean'}),'fixed disjoint signal reference',evidence={'required':reference_role,'changed':{'original_ordinals':[0,1,2,3,4],'estimator':'all-five-mean'}})
        self.check('restored-held-signal',lambda:n.same_real(n.prediction(reference,512,gains,rn,reference_role)[1],qg))
        self.end()

        self.start('08')
        model=n.model_admit
        self.check('literal-profile-operands',lambda:model(gains,rn))
        self.check('gain-times-four',lambda:model([v*4 for v in gains],rn),'immutable profile operands')
        self.check('gain-restored',lambda:model(gains,rn))
        self.check('read-electrons-times-four',lambda:model(gains,[v*4 for v in rn]),'immutable profile operands')
        self.check('read-electrons-restored',lambda:model(gains,rn))
        self.check('literal-q-four-ratio',lambda:self.fact(n.ratio(32,128)['ratio']==n.ratio(32,32)['ratio']/4,'q scale ratio'))
        self.check('wrong-q-normalization',lambda:n.same_real(np.asarray([.25]),np.asarray([1.])), 'binary64 prediction disagreement')
        self.check('q-restored',lambda:n.same_real(np.asarray([n.ratio(32,32)['ratio']]),np.asarray([1.])))
        self.end()

        self.start('09')
        signed=np.asarray([-4.,4.,-4.,4.,0.]).reshape(5,1)
        pre=n.temporal(signed)['pair_variance']; post=n.temporal(np.maximum(signed,0))['pair_variance']
        self.check('clamp-nonlinearity',lambda:self.fact(float(pre[0])==32 and float(post[0])==8,'clamp literal domains'))
        self.check('signed-clamped-domain-swap',lambda:n.same_real(pre,post),'binary64 prediction disagreement')
        self.check('restored-clamped-domain',lambda:n.same_real(post,np.asarray([8.])))
        self.end()

        self.start('10')
        constant=np.full((128,128),1024,dtype=np.float32)
        impulse=np.zeros((128,128),dtype=np.float32); impulse[0,0]=1
        gc,lc=n.pyramid(constant); gi,li=n.pyramid(impulse)
        self.check('constant-dc-null',lambda:self.fact(all(bool((v==0).all()) for v in lc[:4]) and
                   bool((lc[4]==1024).all()),'constant Laplacian null'))
        self.check('corner-impulse-exercised',lambda:self.fact(all(bool((v!=0).any()) for v in li[:4]), 'corner impulse exercise'))
        operators=n.independent_operators()
        y,x=np.indices((128,128)); q=17+(x+3*y)/32
        predicted,_=n.diagonal_prediction(q,operators)
        for k in range(4):
            self.tick(); side=n.SIDES[k]
            for x0,y0 in ((0,0),(1,0),(0,1),(1,1),(side-1,side-1)):
                self.check(f'diagonal-k{k}-x{x0}-y{y0}',lambda k=k,x0=x0,y0=y0:n.same_real(
                    np.asarray(predicted[k][y0,x0]),np.asarray(n.direct_diagonal(q,k,x0,y0,operators))))
            def partition(k=k):
                rows=n.support(k); lo,hi=((5,121),(7,57),(7,25),(7,9))[k]
                phase=((3364,3422,3422,3481),(625,650,650,676),(81,90,90,100),(1,2,2,4))[k]
                self.fact(tuple(int(m.sum()) for _,m in rows[:4])==phase,'fixed support parity counts')
                for j,(px,py) in enumerate(((0,0),(1,0),(0,1),(1,1))):
                    for x0,y0 in ((lo,lo),(lo-1,lo),(hi,hi),(hi+1,hi),(0,0),(n.SIDES[k]-1,n.SIDES[k]-1)):
                        actual=bool(rows[j][1][y0,x0])
                        expected=lo<=x0<=hi and lo<=y0<=hi and x0%2==px and y0%2==py
                        self.fact(actual is expected and bool(rows[j+4][1][y0,x0]) is ((not (lo<=x0<=hi and lo<=y0<=hi)) and x0%2==px and y0%2==py), 'fixed support boundary membership')
                return self.fact(sum(int(m.sum()) for _,m in rows)==n.SIDES[k]**2,'support partition literal')
            self.check(f'partition-k{k}',partition,evidence={'full_phase_counts':list(((3364,3422,3422,3481),(625,650,650,676),(81,90,90,100),(1,2,2,4))[k]),'safe_interval':list(((5,121),(7,57),(7,25),(7,9))[k])})
        correct=n.direct_diagonal(q,0,0,0,operators)
        wrong=n.direct_diagonal(q,0,0,0,operators,duplicate_fault=True)
        self.check('duplicate-address-fault-exercised',lambda:self.fact(correct>0 and wrong<correct,'duplicate address power'))
        self.check('uncoalesced-corner',lambda:n.same_real(np.asarray(wrong),np.asarray(correct)),'binary64 prediction disagreement')
        self.check('restored-coalesced-corner',lambda:n.same_real(np.asarray(n.direct_diagonal(q,0,0,0,operators)),np.asarray(correct)))
        self.end()

        self.start('11')
        y,x=np.indices((128,128))
        cube=np.stack([1000+20*t+(t+1)*(3*x+7*y+((13*x+29*y)%17)) for t in range(5)]).astype(np.float32)
        original_gaussian,original_lap=n.pyramid(cube[0])
        scalar_evidence=[]; operators=n.independent_operators(); gg,ee=operators
        double_lap=n.pyramid(cube[0],np.float64)[1][0]
        for x0,y0 in ((0,0),(64,64)):
            h=np.outer(gg[0][y0],gg[0][x0])-np.outer(ee[0][y0],ee[0][x0])
            positions=np.argwhere(h!=0)
            terms=[{'x':int(xx),'y':int(yy),'weight':float(h[yy,xx]),'input_dn':float(cube[0,yy,xx])} for yy,xx in positions]
            scalar=sum(term['weight']*term['input_dn'] for term in terms)
            n.same_real(np.asarray(scalar),np.asarray(double_lap[y0,x0]),'independent scalar stencil operand disagreement')
            scalar_evidence.append({'xy':[x0,y0],'nonzero_terms':terms,'scalar_sum':scalar,'separable_value':float(double_lap[y0,x0])})
        self.active['independent_scalar_stencils']=scalar_evidence
        correct_expand=n.expand_plane(original_gaussian[1],(128,128))
        wrong_phase=np.roll(correct_expand,1,axis=1)
        self.check('wrong-expand-phase',lambda:n.bit_equal(wrong_phase,correct_expand),'binary32 arithmetic disagreement')
        self.check('restored-expand-phase',lambda:n.bit_equal(n.expand_plane(original_gaussian[1],(128,128)),correct_expand))
        # Omit the actual first horizontal tap in the otherwise same five-tap reduction.
        horizontal=n.filter_axis(cube[0],1,np.arange(64)*2,np.float32)
        first=np.take(cube[0],np.maximum(np.arange(64)*2-2,0),axis=1)/np.float32(16)
        dropped=n.filter_axis(np.subtract(horizontal,first,dtype=np.float32),0,np.arange(64)*2,np.float32)
        self.check('dropped-reduce-tap',lambda:n.bit_equal(dropped,original_gaussian[1]),'binary32 arithmetic disagreement')
        self.check('restored-reduce-taps',lambda:n.bit_equal(n.reduce_plane(cube[0]),original_gaussian[1]))
        spatial=np.stack([n.pyramid(v)[1][0] for v in cube])
        smoothed=np.stack([(cube[max(t-1,0)]+2*cube[t]+cube[min(t+1,4)])/4 for t in range(5)])
        wrong_temporal=np.stack([n.pyramid(v)[1][0] for v in smoothed])
        expected_temporal=n.temporal(spatial)['pair_variance']
        self.check('unwanted-time-axis-smoothing',lambda:n.same_real(n.temporal(wrong_temporal)['pair_variance'],expected_temporal), 'binary64 prediction disagreement')
        self.check('restored-two-dimensional-only',lambda:n.same_real(n.temporal(spatial)['pair_variance'],expected_temporal))
        self.end()

        self.start('12')
        texture=n.literal_texture_array().astype(np.float32)
        laps=n.pyramid(texture)[1]; repeated=np.stack([laps[0]]*5)
        true_q=n.temporal(repeated)['pair_variance']; measured_e=n.energy(laps[0])
        self.check('texture-with-zero-temporal-noise',lambda:self.fact(float(measured_e[64,64])>0 and bool((true_q==0).all()), 'energy temporal distinction exercise'))
        self.check('energy-used-as-temporal-noise',lambda:n.same_real(measured_e,true_q),'binary64 prediction disagreement')
        self.check('restored-temporal-noise',lambda:n.same_real(n.temporal(repeated)['pair_variance'],np.zeros((128,128))))
        self.end()

        self.start('13')
        raw=np.full((5,256,256),1512,dtype='uint16')
        def headroom(values):
            v=n.paper_nuisance(values,512,12000)
            n.need(v['headroom_ok'], 'paper input headroom refusal')
            return True
        self.check('positive-paper-headroom',lambda:headroom(raw))
        for name,value in (('black-plus63',575),('white-minus63',11937)):
            wrong=raw.copy(); wrong[0,0,0]=value
            self.check(name,lambda wrong=wrong:headroom(wrong),'paper input headroom refusal')
            self.check(name+'-restored',lambda:headroom(raw))
        self.check('dark-domain-is-distinct',lambda:self.fact(float(n.temporal(signed)['pair_variance'][0])==32,
                   'dark signed domain not paper headroom'))
        self.end()

        self.start('14')
        same=np.stack([n.literal_texture_array()]*5)
        def illumination(values):
            result=n.input_screens(values)[0]
            n.need(not result['triggered'],'input illumination refusal')
            return True
        self.check('literal-structured-baseline',lambda:illumination(same))
        offset=same.copy(); offset[0]+=32
        scale=same.copy(); scale[0]=np.floor(scale[0]*1.02+0.5)
        for name,wrong in (('frame-zero-plus32',offset),('frame-zero-times1.02',scale)):
            self.check(name,lambda wrong=wrong:illumination(wrong),'input illumination refusal')
            self.check(name+'-restored',lambda:illumination(same))
        self.active['source_bound_scope']='Input screen has no noise-model operand; this is source separation, not a numerical corroboration.'
        self.end()

        self.start('15')
        def motion(values):
            result=n.input_screens(values)[1]
            n.need(not result['low_texture'], 'motion low-texture unresolved')
            n.need(not result['triggered'],'input gross-motion refusal')
            return True
        self.check('zero-map-baseline',lambda:motion(same))
        shifted=same.copy(); shifted[0]=n.literal_texture_array(1,0)
        result=n.input_screens(shifted)[1]
        first=result['comparisons'][0]
        self.check('opposite-sampling-direction-exercised',lambda:self.fact(any(r['dx']==-1 and r['dy']==0 and r['trigger'] for r in first['scores']), 'literal motion direction'))
        self.check('shift-plus-one',lambda:motion(shifted),'input gross-motion refusal')
        self.check('restored-zero-map',lambda:motion(same))
        self.check('constant-field-unresolved',lambda:motion(np.full((5,128,128),1000.)), 'motion low-texture unresolved')
        self.check('restored-texture',lambda:motion(same))
        self.end()

        self.start('16')
        prefix=[.5,.25,.125]; white=.0625
        self.check('no-map-white',lambda:n.beta_admit(0,[],3,False,white,white))
        self.check('placed-measured',lambda:n.beta_admit(1,prefix,2,True,prefix[2],white))
        self.check('placed-k3-white',lambda:n.beta_admit(1,prefix,3,False,white,white))
        self.check('stale-no-map-prefix',lambda:n.beta_admit(0,prefix,0,True,prefix[0],white),'beta supplied prefix')
        self.check('no-map-restored',lambda:n.beta_admit(0,[],0,False,white,white))
        self.check('fabricated-k3-measured',lambda:n.beta_admit(1,prefix,3,True,white,white),'beta measured-source association')
        self.check('k3-restored',lambda:n.beta_admit(1,prefix,3,False,white,white))
        self.check('wrong-selected-beta',lambda:n.beta_admit(1,prefix,0,True,prefix[0]*4,white),'selected beta disagreement')
        self.check('selected-restored',lambda:n.beta_admit(1,prefix,0,True,prefix[0],white))
        self.end()

        self.start('17')
        self.check('actual-evidence-pending',lambda:self.fact(True,'actual evidence deferred'))
        self.end(pending=True)

        self.start('18')
        witnesses=((1.,1.,2.),(65.,1.,2.),(65.,1.,3.92),(2**-74,0.,2.),
                   (2**-149,0.,3.92),(2**100,0.,3.92),(2**-149,0.,1.))
        refs=[]
        for i,(ev,floor,p) in enumerate(witnesses):
            expected=n.weight_reference(ev,floor,1,1,p); refs.append(expected)
            actual=n.f32(expected['weight'])
            branch=('threshold-zero','p2-square','log-exp','p2-square','log-exp','log-exp','p1-direct')[i]
            literal=(0.,1.,1.,0.,math.exp(-80),math.exp(80),0.)[i]
            clamp=('not-applicable','not-applicable','none','not-applicable','lower','upper','not-applicable')[i]
            def branch_check(actual=actual,expected=expected,branch=branch,literal=literal,clamp=clamp,i=i):
                n.weight_admit(actual,expected)
                self.fact(expected['branch']==branch and expected['above'] is (i!=0),'literal weight branch/side')
                self.fact(expected.get('exponent_clamp','not-applicable')==clamp,'literal exponent clamp side')
                self.fact(n.bits(actual)==n.bits(n.f32(literal)),'literal finite weight witness')
                return True
            self.check(f'weight-witness-{i}',branch_check,evidence={'E':ev,'F':floor,'p':n.f32(p),'actual_weight':actual,
                'independent_reference':expected,'literal_weight':literal,'required_branch':branch,'required_clamp':clamp,
                'source_only_p1_outside_actual_population':i==6})
        self.check('p2-tiny-underflow-exercised',lambda:self.fact(refs[3]['above'] and refs[3]['weight']==0 and refs[3]['exact'], 'p2 underflow witness'))
        self.check('log-positive-excess-rounded-r-zero',lambda:self.fact(refs[4]['above'] and refs[4]['rounded_r']==0 and refs[4]['weight']>0, 'log rounded-zero witness'))
        self.check('positive-weight-times-four',lambda:n.weight_admit(4.,refs[1]),'weight arithmetic disagreement')
        self.check('positive-weight-restored',lambda:n.weight_admit(1.,refs[1]))
        self.check('exact-zero-to-minsubnormal',lambda:n.weight_admit(2**-149,refs[3]),'weight arithmetic disagreement')
        self.check('exact-zero-restored',lambda:n.weight_admit(0.,refs[3]))
        self.end(pending=True)

        self.start('19')
        for df in (2,4,11,21):
            values=[n.chi_quantile(df,p) for p in (.025,.975)]
            if df==2:
                self.check('df2-independent-exponential',lambda:self.fact(all(abs(v+2*math.log1p(-p))<=1e-10 for v,p in zip(values,(.025,.975))), 'df2 analytic quantile'),evidence={'df':2,'quantiles':values,'analytic':[-2*math.log1p(-p) for p in (.025,.975)]})
            else:
                self.check(f'df{df}-NIST-table',lambda df=df,values=values:n.quantile_reference(df,values),evidence={'df':df,'probabilities':[.025,.975],'quantiles':values,'NIST':list(n.NIST[df]),'table_tolerance':.0005001})
                fault='df4-half-start' if df==4 else 'omit-last-half-term'
                bad=[n.chi_quantile(df,p,fault) for p in (.025,.975)]
                self.check(f'df{df}-{fault}',lambda df=df,bad=bad:n.quantile_reference(df,bad),'NIST quantile reference disagreement',evidence={'df':df,'fault':fault,'quantiles':bad,'NIST':list(n.NIST[df]),'table_tolerance':.0005001})
                self.check(f'df{df}-restored',lambda df=df:n.quantile_reference(df,[n.chi_quantile(df,p) for p in (.025,.975)]),evidence={'df':df,'restored_quantiles':values})
        self.check('wrong-degrees-of-freedom',lambda:n.variance_interval(32,5),'unsupported temporal degrees of freedom')
        self.check('unlicensed-clamped-interval',lambda:n.variance_interval(32,2,'postclamp'), 'unlicensed interval domain')
        self.check('restored-signed-interval',lambda:self.fact(n.variance_interval(32,2)['lower']<32<n.variance_interval(32,2)['upper'],'restored interval'))
        self.end()

    def authority(self, cases):
        # Actual entry-point predicates/copies are supplied; no second metadata reader.
        self.start('20')
        expected=('source-hash','file-hash','file-extent','cfa-order','missing-original',
                  'wrong-arm','wrong-observer','changed-terminal')
        self.n.need(type(cases) is list and tuple(c[0] for c in cases)==expected,
                    'fixed provenance control variants')
        for name,positive,negative,error in cases:
            self.check(name+'-positive',positive)
            self.check(name+'-destroyer',negative,error)
            self.check(name+'-restored',positive)
        self.end()

    def actual_observers(self, witnesses):
        self.reopen('17')
        self.n.need(len(witnesses)==4,'paper/dark-prefix two-route witness population')
        for label,buffers in witnesses:
            self.n.need(len(buffers)==4,'on/off/placebo/feature-off witness population')
            for i in range(1,4):
                self.check(label+f'-arm{i}',lambda left=buffers[0],right=buffers[i]:self.n.observer_equal(left,right))
        label,buffers=witnesses[0]; baseline=buffers[0]
        for role,error in (('collapsed','observer collapsed byte disagreement'),('tiff','observer whole TIFF byte disagreement')):
            bad=dict(baseline); raw=bytearray(baseline[role]); raw[len(raw)//2]^=1; bad[role]=bytes(raw)
            self.check('actual-'+role+'-bit',lambda bad=bad:self.n.observer_equal(baseline,bad),error)
            self.check('actual-'+role+'-restored',lambda:self.n.observer_equal(baseline,buffers[1]))
        self.end()

    def actual_weight(self, values):
        self.reopen('18')
        # Exactly the first retained on-frame band0 E/V/weight site is mutated;
        # actual population exercise is separately summarized over every on frame.
        e,v,w,beta,gate,p=values
        expected=self.n.weight_reference(e,v,beta,gate,p)
        self.check('actual-weight',lambda:self.n.weight_admit(w,expected))
        bad=0.0 if expected['weight']>0 else 1.0
        self.check('actual-weight-class-bit-fault',lambda:self.n.weight_admit(bad,expected),'weight arithmetic disagreement')
        self.check('actual-weight-restored',lambda:self.n.weight_admit(w,expected))
        side=expected['above']
        self.check('derived-actual-threshold-side',lambda:self.n.threshold_side_admit(side,e,v,beta,gate),
                   evidence={'E':e,'V':v,'beta':beta,'gate':gate,'derived_side':side})
        self.check('flipped-derived-threshold-metadata',lambda:self.n.threshold_side_admit(not side,e,v,beta,gate),'derived threshold-side association')
        self.check('derived-threshold-restored',lambda:self.n.threshold_side_admit(side,e,v,beta,gate))
        self.end()
