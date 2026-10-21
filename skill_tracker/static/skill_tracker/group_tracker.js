(() => {
  const root = document.getElementById('st-tracker');
  if (!root) return;
  const save = document.getElementById('st-save');
  const list = document.getElementById('st-pending-list');
  const status = document.getElementById('st-status');
  const panels = [...root.querySelectorAll('[data-panel-athlete]')];
  const cards = [...root.querySelectorAll('.st-card')];
  const picker = root.querySelector('.st-group-picker');
  const groupData = document.getElementById('st-training-groups');
  const groups = groupData ? JSON.parse(groupData.textContent) : [];
  const groupButtons = [...root.querySelectorAll('[data-st-group]')];
  const nameButtons = [...root.querySelectorAll('[data-st-athlete]')];
  const showGroup = document.getElementById('st-show-group');
  const visibility = document.getElementById('st-visibility');
  const emptyGroup = document.getElementById('st-empty-group');
  const manage = document.getElementById('st-manage-skills');
  const storageKey = `skill-group-picker:${root.dataset.gym}:${root.dataset.user}:${root.dataset.date}`;
  let selectedGroup = '', selectedAthlete = '', entries = [], busy = false;
  const label = {wow: 'Wow', hit: 'Hit', missed: 'Attempt'};
  const token = () => {
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    const s = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
    return `${s.slice(0,8)}-${s.slice(8,12)}-${s.slice(12,16)}-${s.slice(16,20)}-${s.slice(20)}`;
  };

  function currentGroup() { return groups.find(group => group.id === selectedGroup); }
  function belongs(id) {
    const group = currentGroup();
    return !selectedGroup || Boolean(group && group.athlete_ids.includes(id));
  }
  function updatePicker() {
    if (!picker) return;
    if (selectedAthlete && (!belongs(selectedAthlete) || !nameButtons.some(button => button.dataset.stAthlete === selectedAthlete))) {
      selectedAthlete = '';
    }
    groupButtons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.stGroup === selectedGroup)));
    let names = 0, visible = 0;
    nameButtons.forEach(button => {
      button.hidden = !belongs(button.dataset.stAthlete);
      button.setAttribute('aria-pressed', String(button.dataset.stAthlete === selectedAthlete));
      if (!button.hidden) names += 1;
    });
    panels.forEach(panel => {
      const id = panel.dataset.panelAthlete;
      panel.hidden = !belongs(id) || Boolean(selectedAthlete && id !== selectedAthlete);
      if (!panel.hidden) visible += 1;
    });
    emptyGroup.hidden = names > 0;
    emptyGroup.textContent = selectedGroup ? 'No active athletes are assigned to this group.' : 'No active athletes found.';
    showGroup.disabled = !selectedAthlete;
    showGroup.textContent = selectedGroup ? 'Show whole group' : 'Show all athletes';
    if (selectedAthlete) {
      const name = nameButtons.find(button => button.dataset.stAthlete === selectedAthlete).textContent.trim();
      visibility.textContent = `Showing ${name}`;
    } else {
      const group = currentGroup();
      visibility.textContent = `${group ? group.name + ': ' : ''}Showing ${visible} athlete${visible === 1 ? '' : 's'}`;
    }
    if (manage) manage.href = manage.dataset.baseUrl + (selectedAthlete ? `?athlete=${encodeURIComponent(selectedAthlete)}` : '');
    try { sessionStorage.setItem(storageKey, JSON.stringify({group: selectedGroup, athlete: selectedAthlete})); }
    catch (error) { /* Filtering works when browser storage is unavailable. */ }
  }
  if (picker) {
    try {
      const stored = JSON.parse(sessionStorage.getItem(storageKey) || 'null');
      if (stored && typeof stored.group === 'string' && groups.some(group => group.id === stored.group)) selectedGroup = stored.group;
      if (stored && typeof stored.athlete === 'string') selectedAthlete = stored.athlete;
    } catch (error) { /* Start with all athletes if stored choices cannot be read. */ }
    if (root.dataset.selectedAthlete) {
      selectedGroup = '';
      selectedAthlete = root.dataset.selectedAthlete;
    }
    groupButtons.forEach(button => button.addEventListener('click', () => {
      selectedGroup = button.dataset.stGroup;
      selectedAthlete = '';
      updatePicker();
    }));
    nameButtons.forEach(button => button.addEventListener('click', () => {
      selectedAthlete = button.dataset.stAthlete;
      updatePicker();
    }));
    showGroup.addEventListener('click', () => {
      selectedAthlete = '';
      updatePicker();
      const first = nameButtons.find(button => !button.hidden);
      if (first) first.focus();
    });
    updatePicker();
  }

  function updatePracticeTarget(card, select) {
    const box = card.querySelector('.st-target');
    if (!box) return;
    const text = box.querySelector('.st-target-text');
    const progress = box.querySelector('progress');
    box.classList.remove('st-target-met');
    if (!select.value) {
      text.textContent = 'Choose a skill to see your coach’s attempt target.';
      progress.hidden = true;
      return;
    }
    const option = select.selectedOptions[0];
    const target = Number(option.dataset.target || 0);
    if (!Number.isInteger(target) || target <= 0) {
      text.textContent = 'No attempt target planned for this skill today.';
      progress.hidden = true;
      return;
    }
    const saved = ['wow', 'hit', 'missed'].reduce((sum, result) => sum + Number(option.dataset[result] || 0), 0);
    const unsaved = entries.filter(entry => String(entry.assignment) === select.value).length;
    text.textContent = `Coach’s target: ${target} attempts · ${saved} of ${target} saved` +
      (unsaved ? ` · ${unsaved} unsaved` : '') + (saved >= target ? ' · Goal reached!' : '');
    progress.hidden = false;
    progress.max = target;
    progress.value = Math.min(saved, target);
    progress.setAttribute('aria-label', `${saved} of ${target} attempts saved`);
    box.classList.toggle('st-target-met', saved >= target);
  }

  // V3 practice progress upgrades
  let queue;
  function applyCounts(data) {
    cards.forEach(card => {
      const panel = card.closest('[data-panel-athlete]');
      if (panel.dataset.panelAthlete !== String(data.athlete)) return;
      card.querySelectorAll('option[value]').forEach(option => {
        for (const result of ['wow','hit','missed']) option.dataset[result] = String((data.skills || []).find(x => String(x.assignment_id) === option.value && x.result === result)?.total || 0);
      });
    });
  }
  function render(items, state) {
    entries = items.filter(x => ['queued','sending','failed'].includes(x.state) && !x.undo && x.body.action === 'add').map(x => x.body);
    list.replaceChildren();
    items.filter(x => x.state !== 'saved' || x.undo).concat(items.filter(x => x.state === 'saved' && !x.undo).slice(-100)).reverse().forEach(item => {
      if (item.state === 'undone') return;
      const row = document.createElement('li'), panel = panels.find(p => p.dataset.panelAthlete === String(item.body.athlete));
      const option = root.querySelector(`option[value="${Number(item.body.assignment || item.record?.details?.assignment)}"]`);
      const result = item.record?.details?.result || item.body.result;
      const name = item.record?.details?.label || option?.dataset.skillName || 'Skill';
      const description = item.undo ? 'Undo waiting to save' : item.state === 'saved' ? (item.record?.status === 'pending' ? 'Saved · needs coach review' : 'Saved') : 'Waiting to save';
      const text = document.createElement('span'); text.textContent = `${panel?.dataset.athleteName || 'Athlete'} · ${name} · ${label[result] || result} · ${description}`;
      const undo = document.createElement('button'); undo.type = 'button'; undo.textContent = 'Undo'; undo.disabled = Boolean(item.undo);
      undo.onclick = () => queue.undo(item.id); row.append(text, undo); list.appendChild(row);
    });
    document.getElementById('st-pending-count').textContent = state.pending ? `${state.pending} change(s) waiting to save` : 'All results saved';
    status.textContent = state.error || (state.busy ? 'Saving automatically…' : state.pending ? 'Waiting to save. Results will retry automatically.' : 'Autosave is on. Use Undo to correct an accidental tap.');
    if (!state.storageOK && state.pending) status.textContent += ' Keep this tab open until saved; browser storage is unavailable.';
    save.textContent = 'Retry save'; save.disabled = state.pending === 0 || state.busy;
    cards.forEach(card => {
      const select = card.querySelector('select'); if (!select) return;
      card.querySelectorAll('[data-result]').forEach(button => button.disabled = !select.value);
      updatePracticeTarget(card, select);
      const option = select.selectedOptions[0];
      if (select.value) card.querySelector('.st-counts').textContent = `Saved today: ${option.dataset.wow || 0} Wow · ${option.dataset.hit || 0} Hit · ${option.dataset.missed || 0} Attempt`;
    });
  }
  queue = new window.TrackerAutosave({kind:'skill', gym:root.dataset.gym, user:root.dataset.user, date:root.dataset.date,
    saveUrl:root.dataset.autosaveUrl, stateUrl:root.dataset.stateUrl, csrf:()=>document.querySelector('#st-token [name=csrfmiddlewaretoken]').value,
    counts:applyCounts, render});
  cards.forEach(card => {
    const select = card.querySelector('select'); if (!select) return;
    select.onchange = () => queue.draw();
    card.querySelectorAll('[data-result]').forEach(button => button.onclick = () => {
      if (!select.value) return;
      queue.add({athlete:card.closest('[data-panel-athlete]').dataset.panelAthlete, assignment:Number(select.value), result:button.dataset.result}, button);
    });
  });
  save.onclick = () => queue.retry();
  queue.start();
})();
