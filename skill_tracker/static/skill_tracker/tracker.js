(() => {
  const root = document.getElementById('st-tracker');
  if (!root) return;
  const save = document.getElementById('st-save');
  const list = document.getElementById('st-pending-list');
  const status = document.getElementById('st-status');
  let entries = [], busy = false;
  const label = {wow:'Wow',hit:'Hit',missed:'Attempt'};
  const token = () => {
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
    const s = Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
    return `${s.slice(0,8)}-${s.slice(8,12)}-${s.slice(12,16)}-${s.slice(16,20)}-${s.slice(20)}`;
  };
  function redraw() {
    list.replaceChildren();
    entries.forEach((entry,index) => {
      const li = document.createElement('li');
      const text = document.createElement('span'); text.textContent = `${entry.event} · ${entry.name}`;
      const badge = document.createElement('span'); badge.className = `st-badge st-${entry.result}`; badge.textContent = label[entry.result];
      const undo = document.createElement('button'); undo.type='button';undo.textContent='Undo';undo.disabled=busy;
      undo.setAttribute('aria-label',`Undo ${label[entry.result]} for ${entry.name}`);
      undo.onclick=()=>{entries.splice(index,1);redraw();};li.append(text,badge,undo);list.append(li);
    });
    document.getElementById('st-pending-count').textContent = `${entries.length} unsaved result${entries.length===1?'':'s'}`;
    save.disabled = busy || !entries.length;
    root.querySelectorAll('.st-card').forEach(card => {
      const select = card.querySelector('select');if (!select) return;
      select.disabled = busy;
      card.querySelectorAll('[data-result]').forEach(button=>button.disabled=busy||!select.value);
      const option = select.selectedOptions[0];
      const counts = card.querySelector('.st-counts');
      if (!select.value) {counts.textContent='Choose a skill to see today’s totals.';return;}
      const count = result => Number(option.dataset[result]) + entries.filter(e=>String(e.assignment)===select.value&&e.result===result).length;
      counts.textContent = `Today: ${count('wow')} Wow · ${count('hit')} Hit · ${count('missed')} Attempt (includes unsaved)`;
    });
  }
  root.querySelectorAll('.st-card').forEach(card=>{
    const select=card.querySelector('select');if(!select)return;
    select.onchange=redraw;
    card.querySelectorAll('[data-result]').forEach(button=>button.onclick=()=>{
      if (busy || !select.value) return;
      if (entries.length>=500) {status.textContent='Save these results before adding more.';return;}
      entries.push({assignment:Number(select.value),result:button.dataset.result,token:token(),
        name:select.selectedOptions[0].textContent,event:card.querySelector('h2').textContent});
      status.textContent=`${label[button.dataset.result]} added. Save practice when you’re finished.`;redraw();
    });
  });
  save.onclick=async()=>{
    if(busy||!entries.length)return;
    busy=true;redraw();status.textContent='Saving practice…';
    try {
      const response=await fetch(root.dataset.saveUrl,{method:'POST',credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRFToken':document.querySelector('#st-token [name=csrfmiddlewaretoken]').value},
        body:JSON.stringify({athlete:root.dataset.athlete,date:root.dataset.date,entries:entries.map(({assignment,result,token})=>({assignment,result,token}))})});
      let data;try{data=await response.json();}catch{throw new Error('Unable to save. Check your connection or sign-in, then try again.');}
      if(!response.ok||!data.ok)throw new Error(data.error||'Unable to save. Please try again.');
      entries=[];window.location.reload();
    } catch(error){busy=false;status.textContent=error.message;redraw();}
  };
  window.addEventListener('beforeunload',event=>{if(entries.length){event.preventDefault();event.returnValue='';}});
  redraw();
})();
