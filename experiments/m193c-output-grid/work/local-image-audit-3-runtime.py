"""Passive, bounded runtime-source census for the separately granted saved audit3.
No imports here: the owning audit preloads the exact stdlib globals before NumPy.
This module is executed in a private definition namespace, never sys.modules.
"""
LAYOUT=('alias','kind','class_module','class_qualname','canonical_file','reported_file',
 'spec_origin','loader_module','loader_qualname','module_cached','spec_raw_cached',
 'class_owner_file','loader_owner_file','proxy_owner_file')
TYPING_SIZE=122330
TYPING_SHA='26506916777c5fb375f98d13824895adb110565a12a9674c03cb596332e13c43'


def require(value,message):
 if not value:raise ValueError(message)


def raw_class(cls):
 require(type in type.__dict__['__mro__'].__get__(type(cls),type),'genuine class object metadata')
 return type.__dict__['__dict__'].__get__(cls,type)


def raw_module(module):
 # The descriptor is taken from the immutable base type, bypassing subclass hooks.
 require(types.ModuleType in type.__dict__['__mro__'].__get__(type(module),type),'genuine module inheritance')
 return types.ModuleType.__dict__['__dict__'].__get__(module,types.ModuleType)


def class_name(cls):
 raw_class(cls)
 m=type.__dict__['__module__'].__get__(cls,type)
 q=type.__dict__['__qualname__'].__get__(cls,type)
 require(type(m) is str and type(q) is str and len(m)<=256 and len(q)<=256,'bounded concrete class identity')
 return m,q


def scalar(value):
 require(value is None or type(value) is str and len(value)<=2048,'bounded raw string metadata')
 return value


def regular_module(value):
 return types.ModuleType in type.__dict__['__mro__'].__get__(type(value),type)


def registry_delta(oldrows,oldobjects,rows,objects):
 oi=dict(oldobjects);ni=dict(objects);old={r['alias']:r for r in oldrows};new={r['alias']:r for r in rows}
 require(len(oi)==len(oldobjects)==len(oldrows)==len(old) and len(ni)==len(objects)==len(rows)==len(new),'complete unique registry association')
 return dict(added=sorted(ni.keys()-oi.keys()),missing=sorted(oi.keys()-ni.keys()),
  rebound=sorted(k for k in ni.keys()&oi.keys() if ni[k]!=oi[k]),
  changed=sorted(k for k in new.keys()&old.keys() if new[k]!=old[k]))


def lifecycle(delta):
 require(not delta['missing'],'existing runtime alias missing')
 require(not delta['rebound'],'existing runtime alias rebound')
 require(not delta['changed'],'existing runtime raw metadata changed')


class Inspector:
 def __init__(self,pins,reader,clock,writer,root,entry,python,package):
  self.pins=pins;self.read=reader;self.clock=clock;self.write=writer
  self.root=root;self.entry=entry;self.python=python;self.package=package
  self.files={};self.identities={};self.snapshots=[];self.observations={};self.controls=None;self.pending=None;self.pending_label=None;self.pending_pass=None;self.baseline_objects=None

 def canonical(self,value):
  scalar(value);require(value is not None,'missing declared source path')
  p=Path(value)
  require(p.is_absolute() and '..' not in p.parts,'absolute lexical module path')
  # Inspect each lexical ancestor before resolve can erase a reparse component.
  for q in (p,*p.parents):
   st=q.lstat();require(not getattr(st,'st_file_attributes',0)&1024,'non-reparse module ancestry')
  p=p.resolve()
  if p.suffix.lower() in ('.pyc','.pyo'):
   p=Path(importlib.util.source_from_cache(str(p)))
   for q in (p,*p.parents):require(not getattr(q.lstat(),'st_file_attributes',0)&1024,'non-reparse source ancestry')
   p=p.resolve()
  require(p in self.pins,'undeclared module source file')
  r=self.pins[p];require(type(r['bytes']) is int and r['bytes']>=0,'typed runtime source extent')
  return p

 def authenticate(self,value):
  p=self.canonical(value);r=self.pins[p]
  if p not in self.files:
   require(len(self.files)<2048,'bounded module file population')
   require(sum(v['bytes'] for v in self.files.values())+r['bytes']<=128*(1<<20),'bounded unique module source bytes before read')
   raw,actual=self.read(p,128*(1<<20),r)
   self.files[p]=actual;self.identities[p]=tuple(read_identities[str(p)])
  return str(p)

 def owner(self,name,values):
  require(type(name) is str and name in values and regular_module(values[name]),'class owner genuine loaded module')
  d=raw_module(values[name]);file=scalar(d.get('__file__'))
  if file is not None:return self.authenticate(file)
  require(name=='builtins' and values[name] is sys.modules['builtins'],'only pinned builtin class owner without file')
  return 'PINNED_PYTHON_BUILTINS'

 def proxy(self,name,value,values):
  require(name in ('typing.io','typing.re'),'unsupported non-module registry object')
  owner=values.get('typing');require(owner is not None and regular_module(owner),'typing proxy module owner')
  d=raw_module(owner);suffix=name.split('.')[1]
  require(value is d.get(suffix) and type(value) is d.get('_DeprecatedType'),'exact typing class and metaclass identity')
  require(class_name(type(value))==('typing','_DeprecatedType') and class_name(value)==('typing',suffix),'exact typing proxy class provenance')
  f=self.canonical(d.get('__file__'));r=self.pins[f]
  require(f==self.python.parent/'Lib/typing.py' and r['bytes']==TYPING_SIZE and r['sha256']==TYPING_SHA,'exact pinned typing owner source')
  return self.authenticate(str(f))

 def classify(self,name,module,values):
  row={key:None for key in LAYOUT};row['alias']=name
  if module is None:row['kind']='none';return row
  cm,cq=class_name(type(module));row.update(class_module=cm,class_qualname=cq)
  if not regular_module(module):
   row.update(kind='typing-class-proxy',proxy_owner_file=self.proxy(name,module,values));return row
  d=raw_module(module);reported=scalar(d.get('__file__'));cached=scalar(d.get('__cached__'))
  spec=d.get('__spec__');origin=loader=None;raw_cached=None
  if spec is not None:
   require(type(spec) is importlib.machinery.ModuleSpec,'exact passive ModuleSpec type')
   sd=object.__getattribute__(spec,'__dict__')
   origin=scalar(sd.get('origin'));raw_cached=scalar(sd.get('_cached'));loader=sd.get('loader')
  row.update(reported_file=reported,module_cached=cached,spec_origin=origin,spec_raw_cached=raw_cached)
  if type(module) is not types.ModuleType:row['class_owner_file']=self.owner(cm,values)
  if loader is not None:
   cls=loader if type in type.__dict__['__mro__'].__get__(type(loader),type) else type(loader)
   lm,lq=class_name(cls);row.update(loader_module=lm,loader_qualname=lq,loader_owner_file=self.owner(lm,values))
  if reported is not None:
   row.update(kind='module-file',canonical_file=self.authenticate(reported))
   if origin not in (None,'built-in','frozen'):require(self.canonical(origin)==Path(row['canonical_file']),'reported/spec source identity')
  elif origin=='built-in':
   require(loader is importlib.machinery.BuiltinImporter,'exact builtin loader');row['kind']='builtin'
  elif origin=='frozen':
   require(loader is importlib.machinery.FrozenImporter,'exact frozen loader');row['kind']='frozen'
  else:
   require(name=='__main__' and module is sys.modules['__main__'],'unsupported no-file module')
   raise ValueError('current audit entry must have authenticated source')
  return row

 def census(self,values):
  pairs=list(values.items());require(len(pairs)<=4096,'bounded complete alias population')
  require(all(type(k) is str and 0<len(k)<=256 for k,v in pairs),'bounded literal alias names')
  rows=[];errors=[];objects=[]
  # Retain every bounded alias/object witness before any classification can fail.
  for name,value in sorted(pairs):
   row={k:None for k in LAYOUT};row['alias']=name;row['kind']='unclassified';rows.append(row);objects.append([name,id(value)])
  self.pending=dict(rows=rows,errors=errors,processed=0,total=len(rows))
  for i,(name,value) in enumerate(sorted(pairs)):
   self.clock();row=rows[i]
   try:row['class_module'],row['class_qualname']=class_name(type(value))
   except ValueError as e:errors.append([name,'class-identity',str(e)])
  for i,(name,value) in enumerate(sorted(pairs)):
   self.clock()
   try:rows[i]=self.classify(name,value,values)
   except (ValueError,OSError,TypeError,KeyError,AttributeError) as e:
    # Fixed exception class/message only; never repr the unsupported object.
    rows[i]['kind']='unsupported';msg=str(e)
    errors.append([name,type(e).__name__,msg[:512]])
   self.pending['processed']=i+1
  return rows,errors,objects

 def pack(self,label,rows,errors,stable,delta):
  strings=[];indices={}
  def code(value):
   if value is None:return None
   require(type(value) is str,'lossless string table value')
   if value not in indices:indices[value]=len(strings);strings.append(value)
   return indices[value]
  packed=[[code(row[k]) for k in LAYOUT] for row in rows]
  file_rows=[]
  for p,r in sorted(self.files.items(),key=lambda x:str(x[0])):
   file_rows.append([code(str(p)),r['bytes'],r['sha256'],list(self.identities[p])])
  return dict(schema='m193c-passive-runtime-authority-v1',label=label,layout=list(LAYOUT),strings=strings,
   rows=packed,errors=[[code(x) for x in row] for row in errors],files=file_rows,
   stable_during_inspection=stable,delta=delta,metadata_controls=self.controls,
   scope='Module-source witnesses only; no executed cache/native-DLL/transient-module/callable-memory closure.')

 def snapshot(self,label):
  self.clock();self.pending_label=label;self.pending_pass='first-census';before=dict(sys.modules)
  if self.baseline_objects is None:self.baseline_objects=before
  rows,errors,objects=self.census(before)
  # Re-extract passively to detect insertion/rebinding/metadata changes from inspection itself.
  self.pending_pass='stability-reread';after=dict(sys.modules);later,later_errors,later_objects=self.census(after)
  stable=rows==later and errors==later_errors and objects==later_objects
  delta=dict(added=[],missing=[],rebound=[],changed=[])
  if self.snapshots:
   old,oldobj=self.snapshots[0];delta=registry_delta(old,oldobj,rows,objects)
  self.recheck()
  record=self.pack(label,rows,errors,stable,delta)
  # Save the whole bounded result before admission checks, including multiple unknowns.
  receipt=self.write(label,record,256*(1<<10))
  summary=dict(record=receipt,aliases=len(rows),files=len(self.files),unsupported=len(errors),stable=stable,
   full_record_sha256=receipt['sha256'],delta_counts={k:len(v) for k,v in delta.items()})
  self.observations[label]=summary
  require(stable,'passive census unchanged during inspection')
  require(not errors,'complete runtime has unsupported entries')
  lifecycle(delta)
  self.snapshots.append((rows,objects));return summary

 def recheck(self):
  for p,r in list(self.files.items()):self.clock();self.read(p,128*(1<<20),r)
  return dict(files=len(self.files),scope='Same-handle hashes and identities rechecked; not in-memory executable provenance.')

 def commission(self):
  results=[];self.controls=dict(rows=results,complete=False,scope='Visited injected runtime metadata cases only');base=dict(sys.modules);state_before=tuple((k,id(v)) for k,v in sorted(base.items()))
  def case(name,call,expect=None):
   got=None
   try:call()
   except ValueError as e:got=str(e)
   passed=got==expect;results.append(dict(id=name,passed=passed,rejection=got));require(passed,'runtime metadata control '+name)
  plain=types.ModuleType('audit_plain');pd=raw_module(plain);pd['__file__']=str(self.entry);pd['__spec__']=None
  class Sub(types.ModuleType):pass
  sub=Sub('audit_sub');raw_module(sub).update(pd)
  # This local test subclass is owned by the exact separately granted helper namespace.
  hit=[]
  class Trap(types.ModuleType):
   def __getattribute__(self,name):hit.append(name);raise RuntimeError('must never be called')
  trap=Trap('audit_trap');raw_module(trap).update(pd)
  case('plain-module',lambda:self.classify('audit_plain',plain,base))
  # Supply a genuine owner module for fixture classes without touching sys.modules.
  fixture=types.ModuleType('audit_fixture');raw_module(fixture).update(__file__=str(self.entry))
  Sub.__module__=Trap.__module__='audit_fixture';fixtures={**base,'audit_fixture':fixture}
  case('genuine-subclass',lambda:self.classify('audit_sub',sub,fixtures))
  try:trap.__dict__
  except RuntimeError as e:require(str(e)=='must never be called' and hit==['__dict__'],'trap can actually fire')
  else:raise ValueError('trap fixture had no rejection power')
  results.append(dict(id='lazy-hook-powered',passed=True,rejection='must never be called'));hit.clear()
  case('lazy-hook-not-executed',lambda:self.classify('audit_trap',trap,fixtures));require(hit==[],'raw module read never triggered lazy hook')
  require('typing' in base and 'typing.io' in base and 'typing.re' in base,'actual typing proxy cases visited')
  for name in ('typing.io','typing.re'):case(name+'-positive',lambda n=name:self.classify(n,base[n],base))
  case('non-typing-object',lambda:self.classify('audit_unknown',object(),base),'unsupported non-module registry object')
  case('typing-wrong-object',lambda:self.classify('typing.io',object(),base),'exact typing class and metaclass identity')
  wrong=types.ModuleType('typing');raw_module(wrong).update(raw_module(base['typing']));raw_module(wrong)['io']=object()
  case('typing-wrong-owner',lambda:self.classify('typing.io',base['typing.io'],{**base,'typing':wrong}),'exact typing class and metaclass identity')
  class Fake:pass
  wrong_meta=types.ModuleType('typing');raw_module(wrong_meta).update(raw_module(base['typing']));raw_module(wrong_meta)['io']=Fake
  case('typing-wrong-metaclass',lambda:self.classify('typing.io',Fake,{**base,'typing':wrong_meta}),'exact typing class and metaclass identity')
  rows,errs,objs=self.census({'audit_unknown_a':object(),'audit_unknown_b':object(),'audit_plain':plain})
  require(len(rows)==3 and len(errs)==2 and [r['kind'] for r in rows].count('unsupported')==2,'all unsupported rows plus positive retained')
  results.append(dict(id='all-unknowns-retained',passed=True,rejection=None))
  def transition(newrows,newobjects):lifecycle(registry_delta(rows,objs,newrows,newobjects))
  case('missing-alias',lambda:transition(rows[:-1],objs[:-1]),'existing runtime alias missing')
  changed=[list(x) for x in objs];changed[0][1]+=1
  case('rebound-alias',lambda:transition(rows,changed),'existing runtime alias rebound')
  altered=[dict(r) for r in rows];altered[0]['kind']='changed-metadata'
  case('changed-row',lambda:transition(altered,objs),'existing runtime raw metadata changed')
  pin=dict(self.pins[self.entry]);pin['sha256']=('0' if pin['sha256'][0]!='0' else '1')+pin['sha256'][1:]
  case('wrong-declared-file-hash',lambda:self.read(self.entry,128*(1<<20),pin),'bound actual FileRef')
  case('whole-fixture-restored',lambda:transition(rows,objs))
  require(state_before==tuple((k,id(v)) for k,v in sorted(sys.modules.items())),'metadata controls preserve actual registry')
  self.controls=dict(rows=results,complete=True,lazy_hook_calls=len(hit),all_unsupported_rows_retained=True,actual_typing_proxies_visited=True,
   scope='Finite injected metadata controls; no physical startup or scientific calibration claim.')
  return self.controls
