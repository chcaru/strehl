'use strict';
const $ = id => document.getElementById(id);
const PAIRING_STORE='strehl-pairing-v2';
function validKey(value){return typeof value==='string'&&/^[a-f0-9]{48}$/.test(value);}
function stored(area,name){try{return window[area].getItem(name);}catch{return null;}}
function writeStored(area,name,value){try{if(value===null)window[area].removeItem(name);else window[area].setItem(name,value);}catch{/* Pairing still works in memory when browser storage is unavailable. */}}
function decodePairing(value){try{const saved=JSON.parse(value);if(validKey(saved?.key))return{key:saved.key,remoteSession:saved.remoteSession||''};}catch{}return null;}
const savedPairing=decodePairing(stored('localStorage',PAIRING_STORE))||decodePairing(stored('sessionStorage',PAIRING_STORE))||{key:stored('sessionStorage','strehl-pairing')||'',remoteSession:''};
let key=validKey(savedPairing.key)?savedPairing.key:'',remoteSession=savedPairing.remoteSession,state=null,online=false,sending=false,dirty=false,editRevision=null,selecting=false,drag=null,previewGeneration=-1,previewBusy=false,previewUrl=null;
let pairingVersion=0,authFailures=0,failures=0,revoked=false,polling=false,pollTimer=null;
let recoveryMessage='';
let focusPending=null,focusFlight=null,focusAnchor=null,focusDragging=false;
const fragment=new URLSearchParams(location.hash.slice(1));
if(fragment.has('key')){if(validKey(fragment.get('key'))){key=fragment.get('key');remoteSession='';}history.replaceState(null,'',location.pathname);}
function notice(text){$('notice').textContent=text;}
function paired(){return validKey(key);}
function persistPairing(){const value=paired()?JSON.stringify({key,remoteSession}):null;for(const area of ['localStorage','sessionStorage'])writeStored(area,PAIRING_STORE,value);writeStored('sessionStorage','strehl-pairing',null);}
function showPairing(){const active=paired(),repair=active&&(revoked||authFailures>=3);$('pairing').hidden=active&&!repair;$('workspace').hidden=!active||!state;$('capture-footer').hidden=!active||!state;$('pairing-title').textContent=repair?'Reconnect this browser':'Pair this browser';$('retry-pairing').hidden=!active;$('forget-pairing').hidden=!active;if(!online)$('camera-connect').disabled=true;if(!active||!state)$('camera-recovery').hidden=true;}
function clearPreview(){if(previewUrl)URL.revokeObjectURL(previewUrl);previewUrl=null;previewGeneration=-1;$('preview').removeAttribute('src');$('preview').hidden=true;}
function schedulePoll(delay=0){clearTimeout(pollTimer);pollTimer=setTimeout(poll,delay);}
function activatePairing(value){const changed=key!==value.key;pairingVersion++;key=validKey(value.key)?value.key:'';remoteSession=value.remoteSession||'';online=false;authFailures=0;failures=0;revoked=false;if(changed){state=null;dirty=false;editRevision=null;clearPreview();}persistPairing();notice(paired()?'Connecting with saved pairing…':'');showPairing();render();schedulePoll();}
function authorization(){return{key,version:pairingVersion};}
function current(auth){return paired()&&auth.version===pairingVersion&&auth.key===key;}
function sessionIdentity(response){const value=response.headers.get('x-strehl-remote-session');return /^[a-f0-9]{32}$/.test(value||'')?value:'';}
function id(){return Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(16).padStart(2,'0')).join('');}
async function api(path,options={},auth=authorization()){return fetch(path,{cache:'no-store',credentials:'omit',...options,headers:{'Authorization':`Bearer ${auth.key}`,...options.headers},signal:AbortSignal.timeout(10000)});}
function duration(seconds){const s=Math.ceil(Math.max(0,seconds||0));return s>=3600?`${Math.floor(s/3600)}h ${String(Math.floor(s/60)%60).padStart(2,'0')}m ${String(s%60).padStart(2,'0')}s`:`${Math.floor(s/60)}m ${String(s%60).padStart(2,'0')}s`;}
async function command(command,planRevision=null){
 if(!state||!online||sending)return false;
 sending=true;render();let ok=false;
 const auth=authorization();
 const request={id:id(),camera_revision:state.camera_revision,plan_revision:planRevision??state.plan_revision,sequence_id:state.sequence_id,command};
 try{const response=await api('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)},auth);const result=await response.json();if(!current(auth))return false;if(!response.ok)throw Error(result.error||'Command was refused');receive(result.state);notice('');ok=true;}
 catch(error){if(current(auth))notice(error.name==='TimeoutError'||error instanceof TypeError?'Response lost. Check the live status before issuing another command; nothing was retried.':error.message);}
 finally{sending=false;render();}return ok;
}
function receive(next){if(!state||(next.camera_revision>=state.camera_revision&&next.plan_revision>=state.plan_revision))state=next;}
function resetSettings(){dirty=false;editRevision=null;render();}
async function flushFocus(){
 if(focusFlight||focusPending===null||sending||!online||!state?.editable)return;
 const target=focusPending;focusPending=null;
 if(target===state.position)return;
 focusFlight={target,revision:state.camera_revision,sent:Date.now()};
 const ok=await command({op:'focus',target});
 if(!ok){focusFlight=null;focusPending=null;}schedulePoll(0);
}
function render(){
 if(!state)return;
 const s=state,shots=s.shots_per_plane||1,edit=online&&s.editable&&!sending,active=['capturing','scanning','paused'].includes(s.phase),fresh=edit&&s.preview.fresh;
 $('camera-recovery').hidden=!s.failure||!paired();
 if(s.failure){const tag=`${s.sequence_id}:${s.failure.message}:${s.failure.exposure_uncertain}`;if(tag!==recoveryMessage){recoveryMessage=tag;$('recovery-ack').checked=false;}$('camera-error').textContent=s.failure.message;$('recovery-count').textContent=(s.saved==null?`${s.completed} / ${s.total} captures confirmed.`:`${s.completed} / ${s.total} captured; ${s.saved} saved on PC.`)+(s.failure.exposure_uncertain?' The last exposure is uncertain; inspect the camera and saved files before reconnecting.':'');$('recovery-ack-label').hidden=!s.failure.exposure_uncertain;$('recover-camera').disabled=!online||sending||!s.failure.can_reconnect||(s.failure.exposure_uncertain&&!$('recovery-ack').checked);}else{recoveryMessage='';$('recovery-ack').checked=false;}
 $('demo-label').hidden=!s.demo;$('connection-label').textContent=online?(s.connected?'● Camera connected':'● Remote connected'):'○ Remote offline';
 $('camera-connect').textContent=s.connected?'Disconnect':'Connect camera';$('camera-connect').disabled=!online||sending||s.busy||['connecting','disconnecting'].includes(s.phase);
 $('position').textContent=s.position??'—';$('start-position').textContent=s.start_set?s.plan.start:'Not marked';$('end-position').textContent=s.end_set?s.plan.end:'Not marked';
 document.querySelectorAll('[data-jog]').forEach(b=>{const target=(s.position??0)+Number(b.dataset.jog);b.disabled=!edit||s.position===null||target<0||target>65535;});
 document.querySelectorAll('[data-mark]').forEach(b=>b.disabled=!edit||s.position===null);
 document.querySelectorAll('[data-go]').forEach(b=>b.disabled=!edit||!(b.dataset.go==='true'?s.start_set:s.end_set));
 for(const [name,property] of [['step','step'],['settle-ms','settle_ms'],['approach','approach'],['timeout','capture_timeout_s']]){const input=$(name);if(!dirty&&document.activeElement!==input)input.value=s.plan[property];input.disabled=!edit;}
 if(!online||!['ready','complete','stopped','moving'].includes(s.phase)){focusPending=null;focusFlight=null;}
 if(focusFlight&&Date.now()-focusFlight.sent>15000){focusFlight=null;focusPending=null;notice('Focus move was not confirmed; nothing was repeated.');}
 if(focusFlight&&!sending&&s.editable&&s.camera_revision>focusFlight.revision){
  if(s.position!==focusFlight.target){focusPending=null;notice('Focus did not reach the target; nothing was repeated.');}
  focusFlight=null;
 }
 const slider=$('focus-slider');
 slider.disabled=!online||(!s.editable&&!(focusFlight&&s.phase==='moving'));
 if(!focusDragging&&focusPending===null&&!focusFlight&&s.position!==null){
  if(focusAnchor===null||Math.abs(s.position-focusAnchor)>128)focusAnchor=s.position;
  slider.min=$('focus-fine').checked?Math.max(0,focusAnchor-128):0;
  slider.max=$('focus-fine').checked?Math.min(65535,focusAnchor+128):65535;slider.value=s.position;
 }
 $('focus-target').textContent=slider.value;
 $('pixel-shift').disabled=!edit||!s.pixel_shift_options?.includes(4)||!!focusFlight;
 $('pixel-shift').checked=shots===4;
 $('capacity-info').textContent=s.storage_error||(s.storage_required_bytes?`Up to ${(s.storage_required_bytes/1e9).toFixed(2)} GB including headroom. Compression savings are extra.`:'');
 if(focusPending!==null&&!focusFlight&&!sending&&s.editable)queueMicrotask(flushFocus);
 $('settings-actions').hidden=!dirty;$('settings-actions').querySelector('button').disabled=!edit;
 $('plan-count').textContent=s.plan_error|| (s.planned?`${s.planned.toLocaleString()} ${shots===4?`planes / ${(s.planned*shots).toLocaleString()} RAWs`:"RAWs"} · ${s.plan.end>=s.plan.start?'increasing':'decreasing'} sweep`:'Mark both focus bounds');
 $('initial-estimate').textContent=!active&&s.initial_seconds!==null?`Initial estimate ~${duration(s.initial_seconds)}`:'';
 $('start').disabled=!edit||!s.planned||dirty||!!s.storage_error||!!focusFlight||focusPending!==null;$('start').hidden=active||!!s.failure;
 $('review-failure').hidden=!s.failure;for(const name of ['pause','stop'])$(name).hidden=!!s.failure;
 $('pause').disabled=!online||sending||!active||s.pending_control===2;$('pause').textContent=s.phase==='paused'?'Resume':'Pause';$('stop').disabled=!online||sending||!active;
 $('survey').disabled=!fresh||!s.start_set||!s.end_set||Math.abs(s.plan.end-s.plan.start)<8||dirty;$('select-roi').disabled=!fresh;
 const host=s.storage?.mode==='host-pc',waiting=host&&['waiting_for_pc','buffer_full','transfer_failed'].includes(s.storage.state);
 $('storage-info').textContent=host?`${`${s.camera_model||"Camera"} · ${shots} RAW${shots===1?"":"s"} per plane`} → PC. RAWs use Pi RAM only; metadata is saved beside them.${s.storage.receipt?.encoding==='strehl-raw-v1'?` Lossless transfer: ${Number(s.storage.receipt.transfer_saved_percent||0).toFixed(0)}% fewer bytes; original ARWs saved.`:''}`:'A7C II · RAW → SD card. Journal stays on the camera computer.';
 $('battery').textContent=`Battery ${s.battery===null?'—':s.battery+'%'}`;$('card').textContent=host?(waiting?'Waiting for PC':s.storage.upload_MB_per_second?`${s.storage.upload_MB_per_second.toFixed(1)} RAW MB/s · ${s.storage.pending_frames||0} pending`:'PC storage'):`Card ~${s.card_remaining===null?'—':s.card_remaining.toLocaleString()} left`;
 $('preview-info').textContent=s.preview.error||(s.preview.available?`${s.preview.width} × ${s.preview.height} · ${s.preview.fresh?'live':s.preview.age_seconds===null?'waiting for a fresh frame':`last frame ${Math.floor(s.preview.age_seconds)}s ago`}`:'Waiting for preview');
 $('peaking-overlay').hidden=!$('peaking').checked||!s.preview.fresh||!s.connected;
 $('preview-empty').hidden=!!previewUrl&&s.connected;
 if(!s.connected){if(previewUrl)URL.revokeObjectURL(previewUrl);previewUrl=null;$('preview').removeAttribute('src');$('preview').hidden=true;$('roi').hidden=true;previewGeneration=-1;$('preview-empty').querySelector('h2').textContent='Bring the subject into focus';$('preview-empty').querySelector('p').textContent='Connect the camera to begin.';}
 else if(!previewUrl){$('preview-empty').querySelector('h2').textContent='Waiting for live preview';$('preview-empty').querySelector('p').textContent='You can still jog focus and mark bounds using the camera display.';}
 if(!drag)drawRoi(s.roi);
 const ratios=s.magnifier_ratios.join(',');if($('magnifier').dataset.ratios!==ratios){$('magnifier').replaceChildren(...s.magnifier_ratios.map(r=>{const o=document.createElement('option');o.value=r;o.textContent=r===0?'Off':`${r/10}×`;return o;}));$('magnifier').dataset.ratios=ratios;}
 $('magnifier-control').hidden=!s.magnifier_ratios.length;$('magnifier').disabled=!edit;if(s.magnifier_current!==null)$('magnifier').value=s.magnifier_current;
 $('run-message').textContent=!online?'Reconnecting · showing last confirmed status':active&&s.pending_control===2?`Stopping after the active ${shots===4?'four-shot group':'operation'}…`:active&&s.pending_control===1&&s.phase!=='paused'?`Pausing after the active ${shots===4?'four-shot group':'operation'}…`:s.message;
 $('progress').max=s.total||1;$('progress').value=s.saved??s.completed;$('run-count').textContent=s.total?(s.saved==null?`${s.completed} / ${s.total}`:`${s.completed} / ${s.total} planes captured · ${s.storage.saved_frames||0} / ${s.total*shots} RAWs saved`):'';
 $('timer').textContent=waiting?s.storage.message:s.timer?`${online?'':'Last confirmed · '}${s.timer.label}${s.saved!=null&&s.storage.pending_frames?` · ${s.storage.pending_frames} RAWs uploading`:''}`:host?'RAWs save to PC · pause/stop finish queued transfers':'RAWs stay on SD · pause/stop finish the active operation';
 $('survey-result').hidden=!s.samples.length;
 if(s.samples.length)curves(s.samples);
 $('suggestion').textContent=s.suggestion?`Suggested ${s.suggestion.start} → ${s.suggestion.end}`:'Surveying focus…';
 $('suggestion-detail').textContent=s.suggestion?.explanation||'Preview texture is a focusing aid; inspect both boundaries.';
 $('apply-bounds').disabled=!edit||!s.suggestion||s.suggestion.clipped;
}
function drawRoi(roi){if(!roi||!previewUrl||!state?.connected)return;const box=$('roi');box.hidden=!selecting;box.style.left=`${roi.x*100}%`;box.style.top=`${roi.y*100}%`;box.style.width=`${roi.width*100}%`;box.style.height=`${roi.height*100}%`;}
function curves(samples){const canvas=$('curves'),w=canvas.clientWidth||600,h=90;canvas.width=w;canvas.height=h;const ctx=canvas.getContext('2d');ctx.clearRect(0,0,w,h);const max=Math.max(0.00001,...samples.flatMap(s=>s.scores));ctx.strokeStyle='#e6b45070';ctx.lineWidth=1;for(let tile=0;tile<samples[0].scores.length;tile++){ctx.beginPath();samples.forEach((s,i)=>{const x=i/Math.max(1,samples.length-1)*w,y=h-4-(s.scores[tile]/max)*(h-8);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();}}
async function preview(){if(previewBusy||!online||!state?.preview.available||state.preview.generation===previewGeneration)return;previewBusy=true;const auth=authorization();try{const response=await api('/api/preview',{},auth);if(!response.ok||response.status===204)return;const blob=await response.blob();if(!current(auth)||!online||!state?.connected||!state.preview.available)return;const next=URL.createObjectURL(blob);const previous=previewUrl;previewUrl=next;previewGeneration=Number(response.headers.get('x-preview-generation'));$('preview').src=next;$('preview').hidden=false;$('preview-empty').hidden=true;if(previous)URL.revokeObjectURL(previous);drawRoi(state.roi);}catch{}finally{previewBusy=false;}}
async function poll(){
 if(polling)return;polling=true;clearTimeout(pollTimer);const auth=authorization();
 try{if(paired()){
  const response=await api('/api/state',{},auth);if(!current(auth))return;
  if(response.status===401){
   online=false;authFailures++;failures++;const identity=sessionIdentity(response);revoked=revoked||!!(identity&&remoteSession&&identity!==remoteSession);
   notice(revoked?'Web remote restarted or its links were revoked. Paste the current pairing link; no camera command was sent.':authFailures>=3?'The controller is rejecting this saved pairing. Retrying automatically; you can retry now or paste its current link.':'Connection interrupted. Retrying saved pairing; the stack is controlled on the controller.');
   showPairing();render();
  }else if(response.ok){
   const next=await response.json();if(!current(auth))return;
   const identity=sessionIdentity(response);if(identity&&identity!==remoteSession){if(remoteSession)state=null;remoteSession=identity;persistPairing();}
   receive(next);const reconnect=!online;online=true;authFailures=0;failures=0;revoked=false;if(reconnect)notice('');showPairing();render();preview();
  }else throw Error('Remote unavailable');
 }}catch{if(current(auth)){online=false;failures++;notice('Connection lost. Reconnecting automatically; the saved pairing is retained.');render();}}
 finally{polling=false;schedulePoll(!paired()?1000:!current(auth)?0:failures?Math.min(10000,500*2**Math.min(failures,5)):document.hidden?3000:350);}
}
$('pair-form').addEventListener('submit',e=>{e.preventDefault();let value=$('pair-key').value.trim();try{if(value.includes('://'))value=new URLSearchParams(new URL(value).hash.slice(1)).get('key')||'';}catch{}if(validKey(value)){$('pair-key').value='';activatePairing({key:value,remoteSession:value===key?remoteSession:''});}else notice('Use the complete pairing link or key from Strehl Capture.');});
function forgetPairing(){activatePairing({key:'',remoteSession:''});}
$('unpair').addEventListener('click',forgetPairing);
$('forget-pairing').addEventListener('click',forgetPairing);
$('copy-pairing').addEventListener('click',async()=>{
 const link=new URL('/',location.href);link.hash='key='+key;const input=$('share-link');input.value=link.href;
 try{if(!navigator.clipboard)throw Error('Clipboard unavailable');await navigator.clipboard.writeText(link.href);notice('Pairing link copied. Open it on your phone or other computer.');}
 catch{input.hidden=false;input.select();if(document.execCommand('copy')){input.hidden=true;notice('Pairing link copied. Open it on your phone or other computer.');}else notice('Copy the selected pairing link and open it on your other device.');}
});
$('retry-pairing').addEventListener('click',()=>schedulePoll());
window.addEventListener('storage',event=>{if(event.key===PAIRING_STORE)activatePairing(decodePairing(event.newValue)||{key:'',remoteSession:''});});
window.addEventListener('hashchange',()=>{const offered=new URLSearchParams(location.hash.slice(1));if(!offered.has('key'))return;const value=offered.get('key');history.replaceState(null,'',location.pathname);if(validKey(value))activatePairing({key:value,remoteSession:value===key?remoteSession:''});else notice('Use the complete pairing link or key from Strehl Capture.');});
window.addEventListener('online',()=>schedulePoll());
window.addEventListener('pageshow',()=>schedulePoll());
document.addEventListener('visibilitychange',()=>{if(!document.hidden)schedulePoll();});
$('camera-connect').addEventListener('click',()=>command({op:state.connected?'disconnect':'connect'}));
$('recovery-ack').addEventListener('change',render);
$('review-failure').addEventListener('click',()=>$('camera-recovery').scrollIntoView({block:'start'}));
$('recover-camera').addEventListener('click',()=>command({op:'recover',acknowledge_uncertain:$('recovery-ack').checked}));
function peakPreview(){
 const image=$('preview'),canvas=$('peaking-overlay');canvas.hidden=!$('peaking').checked||!state?.preview.fresh||image.hidden;
 if(canvas.hidden||!image.naturalWidth)return;
 const w=image.naturalWidth,h=image.naturalHeight;canvas.width=w;canvas.height=h;
 const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(image,0,0);
 const source=ctx.getImageData(0,0,w,h),out=ctx.createImageData(w,h),luma=new Float32Array(w*h);
 for(let i=0;i<w*h;i++)luma[i]=.2126*source.data[4*i]+.7152*source.data[4*i+1]+.0722*source.data[4*i+2];
 for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){
  const i=y*w+x;if(Math.abs(4*luma[i]-luma[i-1]-luma[i+1]-luma[i-w]-luma[i+w])*.25>=18){out.data[4*i]=0;out.data[4*i+1]=245;out.data[4*i+2]=210;out.data[4*i+3]=220;}
 }
 ctx.putImageData(out,0,0);
}
$('preview').addEventListener('load',peakPreview);
$('peaking').addEventListener('change',peakPreview);
$('focus-slider').addEventListener('pointerdown',()=>{focusDragging=true;});
window.addEventListener('pointerup',()=>{focusDragging=false;flushFocus();});
$('focus-slider').addEventListener('input',()=>{focusPending=Number($('focus-slider').value);$('focus-target').textContent=String(focusPending);flushFocus();});
$('focus-fine').addEventListener('change',()=>{focusAnchor=state?.position??null;render();});
$('pixel-shift').addEventListener('change',()=>command({op:'pixel_shift',shots:$('pixel-shift').checked?4:1}));
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
if(paired()){persistPairing();notice('Connecting with saved pairing…');}showPairing();poll();
