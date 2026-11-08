'use strict';
const $ = id => document.getElementById(id);
let key=sessionStorage.getItem('strehl-pairing')||'',state=null,online=false,sending=false,dirty=false,editRevision=null,selecting=false,drag=null,previewGeneration=-1,previewBusy=false,previewUrl=null;
const fragment=new URLSearchParams(location.hash.slice(1));
if(fragment.has('key')){key=fragment.get('key');sessionStorage.setItem('strehl-pairing',key);history.replaceState(null,'',location.pathname);}
function notice(text){$('notice').textContent=text;}
function paired(){return /^[a-f0-9]{48}$/.test(key);}
function showPairing(){const active=paired();$('pairing').hidden=active;$('workspace').hidden=!active;$('capture-footer').hidden=!active;}
function id(){return Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(16).padStart(2,'0')).join('');}
async function api(path,options={}){return fetch(path,{cache:'no-store',credentials:'omit',...options,headers:{'Authorization':`Bearer ${key}`,...options.headers},signal:AbortSignal.timeout(10000)});}
function duration(seconds){const s=Math.ceil(Math.max(0,seconds||0));return s>=3600?`${Math.floor(s/3600)}h ${String(Math.floor(s/60)%60).padStart(2,'0')}m ${String(s%60).padStart(2,'0')}s`:`${Math.floor(s/60)}m ${String(s%60).padStart(2,'0')}s`;}
async function command(command,planRevision=null){
 if(!state||!online||sending)return false;
 sending=true;render();let ok=false;
 const request={id:id(),camera_revision:state.camera_revision,plan_revision:planRevision??state.plan_revision,sequence_id:state.sequence_id,command};
 try{const response=await api('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)});const result=await response.json();if(!response.ok)throw Error(result.error||'Command was refused');receive(result.state);notice('');ok=true;}
 catch(error){notice(error.name==='TimeoutError'||error instanceof TypeError?'Response lost. Check the live status before issuing another command; nothing was retried.':error.message);}
 finally{sending=false;render();}return ok;
}
function receive(next){if(!state||(next.camera_revision>=state.camera_revision&&next.plan_revision>=state.plan_revision))state=next;}
function resetSettings(){dirty=false;editRevision=null;render();}
function render(){
 if(!state)return;
 const s=state,edit=online&&s.editable&&!sending,active=['capturing','scanning','paused'].includes(s.phase),fresh=edit&&s.preview.fresh;
 $('demo-label').hidden=!s.demo;$('connection-label').textContent=online?(s.connected?'● Camera connected':'● Remote connected'):'○ Remote offline';
 $('camera-connect').textContent=s.connected?'Disconnect':'Connect camera';$('camera-connect').disabled=!online||sending||s.busy||['connecting','disconnecting'].includes(s.phase);
 $('position').textContent=s.position??'—';$('start-position').textContent=s.start_set?s.plan.start:'Not marked';$('end-position').textContent=s.end_set?s.plan.end:'Not marked';
 document.querySelectorAll('[data-jog]').forEach(b=>{const target=(s.position??0)+Number(b.dataset.jog);b.disabled=!edit||s.position===null||target<0||target>65535;});
 document.querySelectorAll('[data-mark]').forEach(b=>b.disabled=!edit||s.position===null);
 document.querySelectorAll('[data-go]').forEach(b=>b.disabled=!edit||!(b.dataset.go==='true'?s.start_set:s.end_set));
 for(const [name,property] of [['step','step'],['settle-ms','settle_ms'],['approach','approach'],['timeout','capture_timeout_s']]){const input=$(name);if(!dirty&&document.activeElement!==input)input.value=s.plan[property];input.disabled=!edit;}
 $('settings-actions').hidden=!dirty;$('settings-actions').querySelector('button').disabled=!edit;
 $('plan-count').textContent=s.plan_error|| (s.planned?`${s.planned.toLocaleString()} RAWs · ${s.plan.end>=s.plan.start?'increasing':'decreasing'} sweep`:'Mark both focus bounds');
 $('initial-estimate').textContent=!active&&s.initial_seconds!==null?`Initial estimate ~${duration(s.initial_seconds)}`:'';
 $('start').disabled=!edit||!s.planned||dirty;$('start').hidden=active;
 $('pause').disabled=!online||sending||!active||s.pending_control===2;$('pause').textContent=s.phase==='paused'?'Resume':'Pause';$('stop').disabled=!online||sending||!active;
 $('survey').disabled=!fresh||!s.start_set||!s.end_set||Math.abs(s.plan.end-s.plan.start)<8||dirty;$('select-roi').disabled=!fresh;
 $('battery').textContent=`Battery ${s.battery===null?'—':s.battery+'%'}`;$('card').textContent=`Card ~${s.card_remaining===null?'—':s.card_remaining.toLocaleString()} left`;
 $('preview-info').textContent=s.preview.error||(s.preview.available?`${s.preview.width} × ${s.preview.height} · ${s.preview.fresh?'live':s.preview.age_seconds===null?'waiting for a fresh frame':`last frame ${Math.floor(s.preview.age_seconds)}s ago`}`:'Waiting for preview');
 $('preview-empty').hidden=!!previewUrl&&s.connected;
 if(!s.connected){if(previewUrl)URL.revokeObjectURL(previewUrl);previewUrl=null;$('preview').removeAttribute('src');$('preview').hidden=true;$('roi').hidden=true;previewGeneration=-1;$('preview-empty').querySelector('h2').textContent='Bring the subject into focus';$('preview-empty').querySelector('p').textContent='Connect the camera to begin.';}
 else if(!previewUrl){$('preview-empty').querySelector('h2').textContent='Waiting for live preview';$('preview-empty').querySelector('p').textContent='You can still jog focus and mark bounds using the camera display.';}
 if(!drag)drawRoi(s.roi);
 const ratios=s.magnifier_ratios.join(',');if($('magnifier').dataset.ratios!==ratios){$('magnifier').replaceChildren(...s.magnifier_ratios.map(r=>{const o=document.createElement('option');o.value=r;o.textContent=r===0?'Off':`${r/10}×`;return o;}));$('magnifier').dataset.ratios=ratios;}
 $('magnifier-control').hidden=!s.magnifier_ratios.length;$('magnifier').disabled=!edit;if(s.magnifier_current!==null)$('magnifier').value=s.magnifier_current;
 $('run-message').textContent=!online?'Remote offline · capture continues on the laptop':active&&s.pending_control===2?'Stopping after the active operation…':active&&s.pending_control===1&&s.phase!=='paused'?'Pausing after the active operation…':s.message;
 $('progress').max=s.total||1;$('progress').value=s.completed;$('run-count').textContent=s.total?`${s.completed} / ${s.total}`:'';
 $('timer').textContent=s.timer?s.timer.label:'RAWs stay on SD · pause/stop finish the active operation';
 $('survey-result').hidden=!s.samples.length;
 if(s.samples.length)curves(s.samples);
 $('suggestion').textContent=s.suggestion?`Suggested ${s.suggestion.start} → ${s.suggestion.end}`:'Surveying focus…';
 $('suggestion-detail').textContent=s.suggestion?.explanation||'Preview texture is a focusing aid; inspect both boundaries.';
 $('apply-bounds').disabled=!edit||!s.suggestion||s.suggestion.clipped;
}
function drawRoi(roi){if(!roi||!previewUrl||!state?.connected)return;const box=$('roi');box.hidden=false;box.style.left=`${roi.x*100}%`;box.style.top=`${roi.y*100}%`;box.style.width=`${roi.width*100}%`;box.style.height=`${roi.height*100}%`;}
function curves(samples){const canvas=$('curves'),w=canvas.clientWidth||600,h=90;canvas.width=w;canvas.height=h;const ctx=canvas.getContext('2d');ctx.clearRect(0,0,w,h);const max=Math.max(0.00001,...samples.flatMap(s=>s.scores));ctx.strokeStyle='#e6b45070';ctx.lineWidth=1;for(let tile=0;tile<samples[0].scores.length;tile++){ctx.beginPath();samples.forEach((s,i)=>{const x=i/Math.max(1,samples.length-1)*w,y=h-4-(s.scores[tile]/max)*(h-8);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();}}
async function preview(){if(previewBusy||!state?.preview.available||state.preview.generation===previewGeneration)return;previewBusy=true;try{const response=await api('/api/preview');if(!response.ok||response.status===204)return;const blob=await response.blob();if(!paired()||!state?.connected||!state.preview.available)return;const next=URL.createObjectURL(blob);const previous=previewUrl;previewUrl=next;previewGeneration=Number(response.headers.get('x-preview-generation'));$('preview').src=next;$('preview').hidden=false;$('preview-empty').hidden=true;if(previous)URL.revokeObjectURL(previous);drawRoi(state.roi);}catch{}finally{previewBusy=false;}}
async function poll(){if(paired()){try{const response=await api('/api/state');if(response.status===401){key='';sessionStorage.removeItem('strehl-pairing');notice('Pairing expired. Open a new link from the camera laptop.');showPairing();}else if(response.ok){receive(await response.json());const reconnect=!online;online=true;if(reconnect)notice('');render();preview();}else throw Error('Remote unavailable');}catch{online=false;render();}}setTimeout(poll,350);}
$('pair-form').addEventListener('submit',e=>{e.preventDefault();let value=$('pair-key').value.trim();try{if(value.includes('://'))value=new URLSearchParams(new URL(value).hash.slice(1)).get('key')||'';}catch{}key=value;if(paired()){sessionStorage.setItem('strehl-pairing',key);$('pair-key').value='';notice('');showPairing();}else notice('Use the complete pairing link or key from Strehl Capture.');});
$('unpair').addEventListener('click',()=>{key='';sessionStorage.removeItem('strehl-pairing');online=false;state=null;if(previewUrl)URL.revokeObjectURL(previewUrl);previewUrl=null;$('preview').removeAttribute('src');$('preview').hidden=true;showPairing();});
$('camera-connect').addEventListener('click',()=>command({op:state.connected?'disconnect':'connect'}));
document.querySelectorAll('[data-jog]').forEach(b=>b.addEventListener('click',()=>command({op:'jog',delta:Number(b.dataset.jog)})));
document.querySelectorAll('[data-mark]').forEach(b=>b.addEventListener('click',()=>command({op:'mark',start:b.dataset.mark==='true'})));
document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>command({op:'go',start:b.dataset.go==='true'})));
for(const name of ['step','settle-ms','approach','timeout'])$(name).addEventListener('input',()=>{if(!dirty)editRevision=state.plan_revision;dirty=true;$('settings-actions').hidden=false;});
$('settings-form').addEventListener('submit',async e=>{e.preventDefault();const ok=await command({op:'settings',step:Number($('step').value),settle_ms:Number($('settle-ms').value),approach:Number($('approach').value),capture_timeout_s:Number($('timeout').value)},editRevision);if(ok)resetSettings();});
$('reset-settings').addEventListener('click',resetSettings);
$('start').addEventListener('click',()=>command({op:'start'}));$('pause').addEventListener('click',()=>command({op:state.phase==='paused'?'resume':'pause'}));$('stop').addEventListener('click',()=>command({op:'stop'}));$('survey').addEventListener('click',()=>command({op:'survey'}));$('apply-bounds').addEventListener('click',()=>command({op:'apply_bounds'}));
function zoom(){const value=Number($('zoom').value);$('zoom-value').textContent=`${value}×`;$('preview-inner').style.width=`${value*100}%`;}
$('zoom').addEventListener('input',zoom);$('fit').addEventListener('click',()=>{$('zoom').value=1;zoom();$('preview-box').scrollTo(0,0);});
$('select-roi').addEventListener('click',()=>{selecting=!selecting;$('select-roi').classList.toggle('selected',selecting);$('preview-box').classList.toggle('selecting',selecting);$('preview-help').textContent=selecting?'Drag a rectangle around the subject.':'Enlarge to inspect focus; scroll or swipe to pan.';$('zoom').value=1;zoom();$('preview-box').scrollTo(0,0);});
function point(event){const r=$('preview').getBoundingClientRect();return{x:Math.max(0,Math.min(1,(event.clientX-r.left)/r.width)),y:Math.max(0,Math.min(1,(event.clientY-r.top)/r.height))};}
function rectangle(a,b){return{x:Math.min(a.x,b.x),y:Math.min(a.y,b.y),width:Math.abs(a.x-b.x),height:Math.abs(a.y-b.y)};}
$('preview').addEventListener('pointerdown',event=>{if(!selecting||!state.editable)return;event.preventDefault();drag=point(event);$('preview').setPointerCapture(event.pointerId);});
$('preview').addEventListener('pointermove',event=>{if(drag)drawRoi(rectangle(drag,point(event)));});
$('preview').addEventListener('pointerup',async event=>{if(!drag)return;const roi=rectangle(drag,point(event));drag=null;selecting=false;$('preview-help').textContent='Enlarge to inspect focus; scroll or swipe to pan.';$('select-roi').classList.remove('selected');$('preview-box').classList.remove('selecting');if(roi.width>=.05&&roi.height>=.05)await command({op:'roi',roi});else notice('Select a larger subject rectangle.');render();});
$('preview').addEventListener('pointercancel',()=>{drag=null;render();});
$('magnifier').addEventListener('change',()=>command({op:'magnify',ratio:Number($('magnifier').value),x:Math.round((state.roi.x+state.roi.width/2)*639),y:Math.round((state.roi.y+state.roi.height/2)*479)}));
showPairing();poll();
