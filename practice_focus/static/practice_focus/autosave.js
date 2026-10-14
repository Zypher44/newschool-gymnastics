/* Durable outbox. Stable mutation tokens make retries and Undo safe on the server. */
(() => {
  'use strict';
  const uuid = () => {
    const b = crypto.getRandomValues(new Uint8Array(16)); b[6] = (b[6] & 15) | 64; b[8] = (b[8] & 63) | 128;
    const s = [...b].map(x => x.toString(16).padStart(2, '0')).join('');
    return `${s.slice(0,8)}-${s.slice(8,12)}-${s.slice(12,16)}-${s.slice(16,20)}-${s.slice(20)}`;
  };
  window.TrackerAutosave = class {
    constructor(options) {
      this.options = options; this.key = `tracker-outbox:v1:${options.gym}:${options.user}:${options.date}:${options.kind}`;
      this.items = []; this.busy = false; this.timer = 0; this.error = ''; this.storageOK = true; this.ready = false;
      try {
        const stored = JSON.parse(localStorage.getItem(this.key) || '[]');
        if (Array.isArray(stored)) this.items = stored.filter(x => x && x.body && x.body.kind === options.kind && x.body.date === options.date && typeof x.id === 'string').map(x => ({...x, blocked: false, state: x.state === 'sending' || (x.state === 'failed' && !x.definitelyRefused) ? 'queued' : x.state}));
      } catch (_) { this.storageOK = false; }
      window.addEventListener('online', () => this.retry());
      window.addEventListener('beforeunload', event => {
        if (this.pending().length && !this.storageOK) {event.preventDefault(); event.returnValue = '';}
      });
      window.addEventListener('storage', event => {
        if (event.key !== this.key || !event.newValue) return;
        try { this.merge(JSON.parse(event.newValue)); this.draw(); this.pump(); } catch (_) {}
      });
    }
    pending() { return this.items.filter(x => x.state === 'queued' || x.state === 'sending' || x.state === 'failed' || x.undo); }
    merge(incoming) {
      if (!Array.isArray(incoming)) return;
      const byId = new Map(this.items.map(x => [x.id, x]));
      for (const value of incoming) {
        if (!value || !value.body || value.body.kind !== this.options.kind || value.body.date !== this.options.date) continue;
        const own = byId.get(value.id);
        if (!own) this.items.push({...value, blocked:false, state:value.state === 'sending' ? 'queued' : value.state});
        else if (own.state !== 'sending' && Number(value.stamp || 0) > Number(own.stamp || 0)) Object.assign(own, value);
      }
    }
    persist() {
      // Keep pending operations regardless of age and only the latest 100 completed entries.
      const pending = this.pending();
      const completed = this.items.filter(x => !pending.includes(x)).slice(-100);
      this.items = [...completed, ...pending];
      try { localStorage.setItem(this.key, JSON.stringify(this.items)); } catch (_) { this.storageOK = false; }
    }
    draw() { this.options.render(this.items, {busy: this.busy, pending: this.pending().length, error: this.error, storageOK: this.storageOK}); }
    async start() {
      this.draw();
      try {
        const response = await fetch(`${this.options.stateUrl}?date=${encodeURIComponent(this.options.date)}`, {credentials: 'same-origin', cache: 'no-store'});
        const data = await response.json();
        if (!response.ok || !data.ok) throw Error(data.error || 'Could not refresh saved totals.');
        (data.counts || []).forEach(x => this.options.counts(x));
        for (const record of data.recent || []) {
          if (record.kind !== this.options.kind) continue;
          let item = this.items.find(x => x.id === record.token);
          if (!item) {
            item = {id: record.token, body: {kind: record.kind, date: record.date, athlete: record.athlete, ...record.details}, sent: true, stamp: Date.now()};
            this.items.push(item);
          }
          item.record = record;
          item.state = ['undone', 'rejected'].includes(record.status) ? 'undone' : 'saved';
          if (item.state === 'undone') item.undo = false;
        }
      } catch (error) { this.error = error.message || 'Unable to refresh totals. Pending results will retry.'; }
      this.ready = true; this.persist(); this.draw(); this.pump();
    }
    add(body, button) {
      if (this.pending().length >= 500) { this.error = 'Retry pending saves before adding more results.'; this.draw(); return; }
      const id = uuid();
      this.items.push({id, body: {...body, token: id, kind: this.options.kind, date: this.options.date, action: 'add'}, state: 'queued', sent: false, stamp: Date.now()});
      this.persist(); this.draw();
      window.TrackerCelebration?.play(body.result, button);
      this.pump();
    }
    remove(sourceId, athlete) {
      const id = uuid();
      this.items.push({id, body: {token: id, action: 'remove', kind: this.options.kind, date: this.options.date, source_id: sourceId, athlete}, state: 'queued', sent: false, stamp: Date.now()});
      this.persist(); this.draw(); this.pump();
    }
    undo(id) {
      const item = this.items.find(x => x.id === id);
      if (!item || item.state === 'undone' || item.undo) return;
      if (!item.sent || (item.state === 'failed' && item.definitelyRefused)) {
        item.state = 'undone';
      } else {
        item.undo = true; item.undoToken = item.undoToken || uuid();
      }
      item.stamp = Date.now(); this.persist(); this.draw(); this.pump();
    }
    retry() {
      this.error = '';
      this.items.forEach(x => {x.blocked = false; if (x.state === 'failed') x.state = 'queued';});
      clearTimeout(this.timer); this.timer = 0; this.draw(); this.pump();
    }
    async pump() {
      if (!this.ready || this.busy) return;
      const item = this.items.find(x => !x.blocked && ((x.undo && x.state === 'saved') || x.state === 'queued'));
      if (!item) return;
      this.busy = true; this.error = ''; const undo = item.undo && item.state === 'saved';
      const body = undo ? {token: item.undoToken, action: 'undo', target: item.id, kind: this.options.kind, date: this.options.date} : item.body;
      item.definitelyRefused = false; item.sent = true; item.state = 'sending'; item.stamp = Date.now(); this.persist(); this.draw();
      let permanentFailure = false;
      try {
        const response = await fetch(this.options.saveUrl, {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-CSRFToken': this.options.csrf()}, body: JSON.stringify(body)});
        const permanent = response.status >= 400 && response.status < 500 && response.status !== 409;
        permanentFailure = permanent;
        let data; try {data = await response.json();} catch (_) {
          if (permanent) { item.definitelyRefused = !undo; throw Error('Save was refused. Refresh your login, then Retry or Undo this result.'); }
          throw Error('Save confirmation was lost. Your result will retry safely.');
        }
        if (!response.ok || !data.ok) {
          if (permanent) item.definitelyRefused = !undo;
          throw Error(data.error || 'This result needs attention. Retry or Undo it.');
        }
        item.state = undo || ['undone', 'rejected'].includes(data.record?.status) || data.removed ? 'undone' : 'saved';
        if (undo || item.state === 'undone') item.undo = false;
        if (data.record) item.record = data.record;
        if (data.counts) this.options.counts(data.counts);
        this.options.committed?.(body, data);
        if (!undo) (data.milestones || []).forEach(x => window.TrackerMilestone?.(x));
        item.blocked = false;
      } catch (error) {
        item.blocked = true; item.state = undo ? 'saved' : 'failed';
        if (item.definitelyRefused && item.undo && !undo) {item.state = 'undone'; item.undo = false;}
        this.error = error.message || 'Waiting to save. Results remain in this browser.';
        if (!permanentFailure) this.timer = setTimeout(() => this.retry(), 5000);
      } finally {
        item.stamp = Date.now(); this.busy = false; this.persist(); this.draw();
        this.pump();
      }
    }
  };
  window.TrackerMilestone = milestone => {
    const key = `tracker-milestone:${milestone.id}`;
    try {if (localStorage.getItem(key)) return; localStorage.setItem(key, 'seen');} catch (_) {}
    window.TrackerCelebration?.play('wow');
    const toast = document.createElement('div'); toast.className = 'progress-milestone-toast'; toast.setAttribute('role', 'status');
    toast.textContent = milestone.title; document.body.appendChild(toast); setTimeout(() => toast.remove(), 2800);
  };
})();
