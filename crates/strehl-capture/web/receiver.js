'use strict';
const $=id=>document.getElementById(id),store='strehl-receiver-pairing';
let key='',dirty=false;
try{key=localStorage.getItem(store)||'';}catch{}
const fragment=new URLSearchParams(location.hash.slice(1)).get('key');
if(fragment){key=fragment;history.replaceState(null,'',location.pathname);}
function remember(){try{localStorage.setItem(store,key);}catch{}}
remember();
async function api(path,body){const response=await fetch(path,{method:body?'POST':'GET',headers:{Authorization:`Bearer ${key}`,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(7000)});const data=await response.json();if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);return data;}
async function poll(){try{const s=await api('/api/status');$('pair-form').hidden=true;$('settings').hidden=false;$('connection-label').textContent='Ready to receive';if(!dirty){$('folder').value=s.folder;$('compress-raw').checked=s.compress_raw!==false;}$('space').textContent=`${(s.free_bytes/2**30).toFixed(1)} GiB available`;$('latest').textContent=s.latest.path?`${s.latest.path} · ${((s.latest.storage_bytes??s.latest.bytes)/2**20).toFixed(1)} MiB on disk${s.latest.storage_encoding==='strehl-archive-v1'?` · ${Math.max(0,100*(1-s.latest.storage_bytes/s.latest.bytes)).toFixed(0)}% disk space saved · lossless`:''} · SHA-256 verified${s.latest.encoding==='strehl-raw-v1'?` · ${Math.max(0,100*(1-s.latest.wire_bytes/s.latest.bytes)).toFixed(0)}% fewer transfer bytes`:''}`:'No RAW received in this session.';}catch(e){$('connection-label').textContent='Receiver unavailable';$('notice').textContent=e.message;if(e.message.includes('Pair'))$('pair-form').hidden=false;}setTimeout(poll,2000);}
$('pair-form').addEventListener('submit',e=>{e.preventDefault();const value=$('pair-key').value.trim();try{key=new URL(value).hash.split('key=')[1]||value;}catch{key=value;}remember();$('pair-key').value='';$('notice').textContent='';});
$('folder').addEventListener('input',()=>{dirty=true;});
$('compress-raw').addEventListener('change',()=>{dirty=true;});
$('folder-form').addEventListener('submit',async e=>{e.preventDefault();try{const r=await api('/api/folder',{folder:$('folder').value.trim(),compress_raw:$('compress-raw').checked});dirty=false;$('notice').textContent=r.message;}catch(error){$('notice').textContent=error.message;}});
if(!['127.0.0.1','localhost','[::1]'].includes(location.hostname))for(const element of $('folder-form').elements)element.disabled=true;
poll();
