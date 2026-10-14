/* Both trackers share the existing durable outbox, save API and celebrations. */
(() => {
  'use strict';
  const controllers = new Map();
  const choices = new Map();
  const counts = new Map();
  const countTimes = new Map();
  let current = null;
  const scope = c => `${c.gym}:${c.user}:${c.date}`;
  const selectionKey = c => `${scope(c)}:${c.athlete}:${c.event}`;
  const countKey = (c, kind, athlete = c.athlete) => `${scope(c)}:${kind}:${athlete}`;
  const label = result => result === 'missed' ? 'Attempt' : result === 'wow' ? 'Wow' : 'Hit';
  function acceptCounts(config, kind, data, athlete = config.athlete) {
    const key=countKey(config,kind,String(athlete));
    const time=Date.parse(data.as_of) || 0;
    if (counts.has(key) && time<(countTimes.get(key) || 0)) return;
    counts.set(key,data[kind==='skill'?'skills':'routines'] || []);
    countTimes.set(key,time);
  }
  function controller(kind) { return current ? controllers.get(`${scope(current.config)}:${kind}`) : null; }
  function visibleItems(kind) {
    const c = controller(kind);
    if (!c || !current) return [];
    return c.items.filter(item => {
      const details = item.record?.details || item.body;
      return item.state !== 'undone' && item.body.action !== 'remove' &&
        String(item.body.athlete) === current.config.athlete && details.event === current.config.event;
    }).sort((a,b)=>(Date.parse(a.record?.created_at) || Number(a.stamp) || 0)-(Date.parse(b.record?.created_at) || Number(b.stamp) || 0));
  }
  function matchedItems(kind) {
    return visibleItems(kind).filter(item => {
      const details = item.record?.details || item.body;
      return kind === 'skill' ? String(details.assignment) === current.choice.assignment : Boolean(details.pressure) === current.choice.pressure;
    });
  }
  function refresh(kind) {
    if (!current?.root.isConnected) return;
    const {root, config, choice} = current;
    const card = root.querySelector(`[data-ip-kind="${kind}"]`);
    const c = controller(kind);
    const event = config.events.find(e => e.code === config.event);
    const skill = event.skills.find(s => s.id === choice.assignment);
    const rows = counts.get(countKey(config, kind)) || [];
    const chosen = rows.filter(x => kind === 'skill' ? String(x.assignment_id) === choice.assignment : x.event === config.event && Boolean(x.is_pressure) === choice.pressure);
    const totals = {wow:0, hit:0, missed:0};
    chosen.forEach(row => { totals[row.result] = Number(row.total) || 0; });
    const saved = totals.wow + totals.hit + totals.missed;
    const target = kind === 'skill' ? skill?.target || 0 : choice.pressure ? event.pressure_target : event.routine_target;
    const pending = matchedItems(kind).filter(item => ['queued','sending','failed'].includes(item.state) && !item.undo && !item.definitelyRefused).length;
    const goal = card.querySelector('[data-ip-goal]');
    if (kind === 'skill' && !skill) goal.textContent = event.skills.length ? 'Choose the skill you just completed.' : 'No current skills for this event. Ask your coach to assign them.';
    else goal.textContent = target ? `Coach’s target: ${saved} / ${target} saved` + (pending ? ` · ${pending} waiting to save` : '') + (saved >= target ? ' · Goal reached!' : '') : `${saved} saved today` + (pending ? ` · ${pending} waiting to save` : '');
    goal.classList.toggle('ip-met', Boolean(target && saved >= target));
    card.querySelector('[data-ip-counts]').textContent = kind === 'skill' && !skill ? '' : `Wow ${totals.wow} · Hit ${totals.hit} · Attempt ${totals.missed}`;
    card.querySelectorAll('[data-ip-result]').forEach(button => { button.disabled = !config.enabled || !c || (kind === 'skill' && !skill); });
    const items = visibleItems(kind).slice(-10).reverse();
    const log = card.querySelector('[data-ip-log]');
    log.replaceChildren();
    items.forEach(item => {
      const details = item.record?.details || item.body;
      const row = document.createElement('li'), text = document.createElement('span');
      const savedText = item.record?.status === 'pending' ? 'Saved · needs coach review' : 'Saved';
      text.textContent = `${details.label || (kind === 'routine' ? (details.pressure ? 'Pressure set' : 'Routine') : 'Skill')} · ${label(details.result)} · ${item.undo ? 'Undo saving…' : item.state === 'saved' ? savedText : 'Waiting to save'}`;
      const undo = document.createElement('button'); undo.type = 'button'; undo.textContent = 'Undo'; undo.disabled = Boolean(item.undo);
      undo.onclick = () => c.queue.undo(item.id);
      row.append(text, undo); log.append(row);
    });
    if (!items.length) {const row=document.createElement('li');row.textContent='No recent results from this account for this event.';log.append(row);}
    const state = c?.state;
    let status = !config.enabled ? 'Viewing this practice date' : !c ? 'Unable to start autosave. Refresh before recording.' : state?.busy ? 'Saving automatically…' : state?.pending ? `${state.pending} change(s) waiting to save.` : 'Autosave is on';
    if (state?.error) status = state.error;
    if (state && !state.storageOK && state.pending) status += ' Keep this tab open until saved; browser storage is unavailable.';
    card.querySelector('[data-ip-status]').textContent = status;
    card.querySelector('[data-ip-retry]').disabled = !state?.pending || Boolean(state?.busy);
    const last = items.find(item => !item.undo);
    const quickUndo = card.querySelector('[data-ip-last-undo]');
    if (quickUndo) {quickUndo.disabled=!last;quickUndo.onclick=()=>{if(last)c.queue.undo(last.id);};}
    // Keep Start Practice's plan preview in sync without reloading its timers or roster.
    if (kind === 'skill' && config.enabled) {
      document.querySelectorAll('[data-ip-plan-skill-name]').forEach(node => {
        const id=event.skills.find(skill=>skill.name===node.dataset.ipPlanSkillName)?.id;
        if (!id) return;
        const amount=rows.filter(x=>String(x.assignment_id)===id).reduce((sum,x)=>sum+Number(x.total),0);
        node.textContent = node.dataset.target ? `${amount} / ${node.dataset.target} attempts` : `${amount} logged`;
      });
    }
    if (kind === 'routine' && config.enabled) document.querySelectorAll('[data-ip-plan-pressure]').forEach(node=>{
      const pressure=node.dataset.ipPlanPressure==='true';
      const amount=rows.filter(x=>x.event===config.event && Boolean(x.is_pressure)===pressure).reduce((sum,x)=>sum+Number(x.total),0);
      node.textContent=`${amount} / ${node.dataset.target}`;
    });
    if (config.enabled) document.querySelectorAll(kind==='skill'?'[data-ip-progress-skill]':'[data-ip-progress-pressure]').forEach(node=>{
      let amount;
      if (kind==='skill') {
        const event=config.events.find(e=>e.code===node.dataset.event);
        const id=event?.skills.find(skill=>skill.name===node.dataset.ipProgressSkill)?.id;
        if (!id) return;
        amount=rows.filter(x=>String(x.assignment_id)===id).reduce((sum,x)=>sum+Number(x.total),0);
        node.querySelector('[data-ip-value]').textContent=node.dataset.target?`${amount} / ${node.dataset.target}`:String(amount);
        node.classList.toggle('pp-met',Boolean(node.dataset.target && amount>=Number(node.dataset.target)));
      } else {
        amount=rows.filter(x=>x.event===node.dataset.event && Boolean(x.is_pressure)===(node.dataset.ipProgressPressure==='true')).reduce((sum,x)=>sum+Number(x.total),0);
        node.textContent=`${amount} / ${node.dataset.target}`;
      }
    });
  }
  function ensure(kind) {
    const config = current.config;
    const key = `${scope(config)}:${kind}`;
    if (controllers.has(key) || !config.enabled || !window.TrackerAutosave) return;
    const c = {items:[], state:{}, csrf:document.querySelector('#ip-token [name=csrfmiddlewaretoken]')?.value || ''};
    c.queue = new window.TrackerAutosave({kind, gym:config.gym, user:config.user, date:config.date,
      saveUrl:config.save_url, stateUrl:config.state_url,
      csrf:()=>document.querySelector('#ip-token [name=csrfmiddlewaretoken]')?.value || c.csrf,
      counts:data=>{acceptCounts(config,kind,data,data.athlete);refresh(kind);},
      render:(items,state)=>{c.items=items;c.state=state;refresh(kind);}
    });
    controllers.set(key,c);
    c.queue.start();
  }
  function setEvent(code) {
    if (!current.config.events.some(event=>event.code===code)) return;
    current.config.event=code;
    const event=current.config.events.find(event=>event.code===code);
    const key=selectionKey(current.config);
    const choice=choices.get(key) || {assignment:event.skills.length === 1 ? event.skills[0].id : '',pressure:false};
    if (!event.skills.some(s=>s.id===choice.assignment)) choice.assignment=event.skills.length===1 ? event.skills[0].id : '';
    current.choice=choice;choices.set(key,choice);
    const select=current.root.querySelector('[data-ip-skill]');select.replaceChildren();
    const empty=document.createElement('option');empty.value='';empty.textContent=event.skills.length ? 'Choose a skill' : 'No current skills';select.append(empty);
    event.skills.forEach(skill=>{const option=document.createElement('option');option.value=skill.id;option.textContent=skill.name;select.append(option);});
    select.value=choice.assignment;select.disabled=!current.config.enabled || !event.skills.length;
    current.root.querySelectorAll('[data-ip-event]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.ipEvent===code)));
    current.root.querySelectorAll('[data-ip-pressure]').forEach(button=>button.setAttribute('aria-pressed',String((button.dataset.ipPressure==='true')===choice.pressure)));
    current.root.querySelectorAll('[data-ip-event-label]').forEach(node=>{node.textContent=event.label;});
    const cue=current.root.querySelector('[data-ip-cue]');cue.textContent=event.cue;cue.hidden=!event.cue;
    refresh('skill');refresh('routine');
  }
  function initialize() {
    const root=document.getElementById('ip-trackers'),data=document.getElementById('ip-config');
    if (!root || !data) {current=null;return;}
    let config;try {config=JSON.parse(data.textContent);}catch(_){return;}
    current={root,config,choice:{assignment:'',pressure:false}};
    for (const kind of ['skill','routine']) {
      // A delayed page response must not replace a newer save confirmation's totals.
      acceptCounts(config,kind,config.counts);
      ensure(kind);
    }
    setEvent(config.event);
    root.querySelectorAll('[data-ip-event]').forEach(button=>button.addEventListener('click',()=>setEvent(button.dataset.ipEvent)));
    root.querySelector('[data-ip-skill]').addEventListener('change',event=>{current.choice.assignment=event.target.value;refresh('skill');});
    root.querySelectorAll('[data-ip-pressure]').forEach(button=>button.addEventListener('click',()=>{current.choice.pressure=button.dataset.ipPressure==='true';setEvent(current.config.event);}));
    root.querySelectorAll('[data-ip-result]').forEach(button=>button.addEventListener('click',()=>{
      if (button.disabled || !current.config.enabled) return;
      const kind=button.closest('[data-ip-kind]').dataset.ipKind;
      const c=controller(kind),config=current.config;
      const body={athlete:config.athlete,event:config.event,result:button.dataset.ipResult,inline:true};
      if (kind==='skill') {
        body.assignment=Number(current.choice.assignment);
        body.label=config.events.find(e=>e.code===config.event).skills.find(s=>s.id===current.choice.assignment)?.name;
      } else {body.pressure=current.choice.pressure;body.label=`${config.event} ${body.pressure?'pressure set':'routine'}`;}
      c.queue.add(body,button);
    }));
    root.querySelectorAll('[data-ip-retry]').forEach(button=>button.onclick=()=>controller(button.dataset.ipRetry)?.queue.retry());
  }
  initialize();
  document.addEventListener('live:updated',initialize);
})();
