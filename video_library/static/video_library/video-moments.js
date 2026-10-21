/* Human feedback on actual paused video frames. No screenshots, AI or external API. */
(() => {
  const NS = 'http://www.w3.org/2000/svg';
  const colors = new Set(['#ef4444', '#facc15', '#3b82f6', '#22c55e']);
  const tools = new Set(['pen', 'arrow', 'line', 'circle']);
  const copy = value => JSON.parse(JSON.stringify(value));
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const timeLabel = value => Math.floor(value / 60) + ':' + (value % 60).toFixed(2).padStart(5, '0');
  function bind(root) {
    if (root.dataset.bound) return;
    root.dataset.bound = 'true';
    const video = document.getElementById(root.dataset.playerId);
    const status = root.querySelector('[data-status]');
    const say = (message, error = false) => { status.textContent = message; status.classList.toggle('vm-error', error); };
    if (!video) { say('The video player is unavailable.', true); return; }
    const coach = root.dataset.isCoach === 'true';
    const editor = root.querySelector('[data-editor]');
    const comment = root.querySelector('[data-comment]');
    const visibility = root.querySelector('[data-visibility]');
    const list = root.querySelector('[data-notes]');
    const more = root.querySelector('[data-more]');
    const retry = root.querySelector('[data-retry]');
    const stage = document.createElement('div');
    stage.className = 'vm-stage';
    video.parentNode.insertBefore(stage, video);
    stage.append(video);
    video.style.objectFit = 'contain';
    const svg = document.createElementNS(NS, 'svg');
    svg.classList.add('vm-overlay');
    svg.setAttribute('viewBox', '0 0 1000 1000');
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.setAttribute('aria-label', 'Coach drawing on the selected video moment');
    stage.append(svg);
    const notes = new Map();
    let nextPage = null;
    let draft = null;
    let shown = null;
    let drawing = false;
    let tool = 'pen';
    let color = '#ef4444';
    let stroke = null;
    let pointer = null;
    let dirty = false;
    let busy = false;
    let seekTicket = 0;
    let loadTicket = 0;

    function node(tag, attributes) {
      const element = document.createElementNS(NS, tag);
      for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
      return element;
    }
    function frameBounds() {
      const rect = video.getBoundingClientRect();
      const parent = stage.getBoundingClientRect();
      if (!video.videoWidth || !video.videoHeight || !rect.width || !rect.height) return null;
      const scale = Math.min(rect.width / video.videoWidth, rect.height / video.videoHeight);
      const width = video.videoWidth * scale, height = video.videoHeight * scale;
      const left = rect.left + (rect.width - width) / 2, top = rect.top + (rect.height - height) / 2;
      Object.assign(svg.style, { left: (left - parent.left) + 'px', top: (top - parent.top) + 'px',
                                width: width + 'px', height: height + 'px' });
      return { left, top, width, height };
    }
    function validShape(shape) {
      return shape && tools.has(shape.tool) && colors.has(shape.color) && Array.isArray(shape.points) &&
        shape.points.length >= 2 && shape.points.length <= 400 &&
        shape.points.every(point => Array.isArray(point) && point.length === 2 &&
          point.every(value => finite(value) && value >= 0 && value <= 1));
    }
    function paintShape(shape) {
      if (!validShape(shape)) return;
      const points = shape.points.map(point => point.map(value => value * 1000));
      const first = points[0], last = points[points.length - 1];
      const common = { fill: 'none', stroke: shape.color, 'stroke-width': 3,
                       'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'vector-effect': 'non-scaling-stroke' };
      if (shape.tool === 'pen') svg.append(node('polyline', { ...common, points: points.map(point => point.join(',')).join(' ') }));
      else if (shape.tool === 'circle') svg.append(node('ellipse', { ...common,
        cx: (first[0] + last[0]) / 2, cy: (first[1] + last[1]) / 2,
        rx: Math.abs(first[0] - last[0]) / 2, ry: Math.abs(first[1] - last[1]) / 2 }));
      else {
        svg.append(node('line', { ...common, x1: first[0], y1: first[1], x2: last[0], y2: last[1] }));
        if (shape.tool === 'arrow') {
          // Construct the arrow head in screen pixels so portrait clips do not distort it.
          const bounds = frameBounds();
          if (!bounds) return;
          const dx = (last[0] - first[0]) * bounds.width / 1000;
          const dy = (last[1] - first[1]) * bounds.height / 1000;
          const length = Math.hypot(dx, dy);
          if (length < 1) return;
          const ux = dx / length, uy = dy / length;
          const wings = [-1, 1].map(sign => [last[0] + (-ux * 12 + sign * uy * 6) * 1000 / bounds.width,
                                              last[1] + (-uy * 12 - sign * ux * 6) * 1000 / bounds.height]);
          svg.append(node('polyline', { ...common, points: [wings[0], last, wings[1]].map(p => p.join(',')).join(' ') }));
        }
      }
    }
    function matched(moment) {
      return moment && video.paused && !video.seeking && video.readyState >= 2 &&
        finite(video.currentTime) && Math.abs(video.currentTime - moment.timestamp_seconds) <= 0.05;
    }
    function renderOverlay() {
      const moment = draft || shown;
      svg.replaceChildren();
      const visible = frameBounds() && matched(moment);
      svg.style.display = visible ? 'block' : 'none';
      svg.classList.toggle('vm-drawing', Boolean(visible && drawing && draft));
      stage.classList.toggle('vm-editing', Boolean(visible && drawing && draft));
      if (visible) {
        for (const shape of (moment.drawing || [])) paintShape(shape);
        if (stroke) paintShape(stroke);
      }
    }
    function setDrawing(value) {
      drawing = Boolean(value && coach && draft);
      const button = root.querySelector('[data-toggle-draw]');
      if (button) { button.setAttribute('aria-pressed', String(drawing)); button.textContent = drawing ? 'Finish drawing' : 'Draw on this frame'; }
      renderOverlay();
    }
    function setBusy(value) {
      busy = value;
      root.querySelectorAll('button').forEach(button => { button.disabled = value; });
      if (comment) comment.readOnly = value;
      if (visibility) visibility.disabled = value;
      const picker = root.querySelector('[data-color]');
      if (picker) picker.disabled = value;
    }
    function draftBlocked() {
      if (busy) return true;
      if (draft && dirty) { say('Save or cancel your current draft before opening another moment.', true); return true; }
      return false;
    }
    function resetDraft() {
      draft = null; dirty = false; stroke = null; pointer = null;
      if (editor) editor.hidden = true;
      setDrawing(false);
    }
    function editDraft(note) {
      draft = note ? copy(note) : { timestamp_seconds: Number(video.currentTime.toFixed(3)), comment: '', drawing: [], visibility: 'private' };
      shown = null; dirty = false;
      editor.hidden = false;
      comment.value = draft.comment;
      visibility.value = draft.visibility;
      root.querySelector('[data-draft-label]').textContent = note ? 'Edit moment' : 'New moment';
      root.querySelector('[data-draft-time]').textContent = timeLabel(draft.timestamp_seconds);
      root.querySelector('[data-save]').textContent = note ? 'Save changes' : 'Save moment';
      setDrawing(false);
    }
    async function ready(ticket) {
      if (video.readyState >= 2) return ticket === seekTicket;
      return new Promise(resolve => {
        const done = ok => {
          window.clearTimeout(timer);
          video.removeEventListener('loadeddata', loaded);
          video.removeEventListener('error', failed);
          resolve(ok && ticket === seekTicket);
        };
        const loaded = () => done(true);
        const failed = () => done(false);
        const timer = window.setTimeout(failed, 10000);
        video.addEventListener('loadeddata', loaded, { once: true });
        video.addEventListener('error', failed, { once: true });
        video.preload = 'auto';
        if (video.readyState === 0) video.load();
      });
    }
    async function seekTo(timestamp) {
      const ticket = ++seekTicket;
      video.pause();
      setDrawing(false);
      svg.style.display = 'none';
      if (!await ready(ticket)) { if (ticket === seekTicket) say('The video frame is unavailable. Check playback and try again.', true); return false; }
      if (!finite(timestamp) || timestamp < 0 || (finite(video.duration) && timestamp > video.duration)) {
        say('This moment is outside the playable video.', true); return false;
      }
      if (video.seeking || Math.abs(video.currentTime - timestamp) > 0.0005) {
        const completed = await new Promise(resolve => {
          let finished = false;
          const finish = ok => {
            if (finished) return;
            finished = true;
            window.clearTimeout(timer);
            ['seeked', 'loadeddata', 'canplay'].forEach(name => video.removeEventListener(name, settled));
            video.removeEventListener('error', failed);
            resolve(ok && ticket === seekTicket);
          };
          const settled = () => {
            if (ticket !== seekTicket) { finish(false); return; }
            if (!video.seeking && video.readyState >= 2 && Math.abs(video.currentTime - timestamp) <= 0.05) finish(true);
          };
          const failed = () => finish(false);
          const timer = window.setTimeout(failed, 10000);
          ['seeked', 'loadeddata', 'canplay'].forEach(name => video.addEventListener(name, settled));
          video.addEventListener('error', failed, { once: true });
          video.currentTime = timestamp;
        });
        if (!completed) { if (ticket === seekTicket) say('That video frame could not be shown. Try its timestamp again.', true); return false; }
      }
      renderOverlay();
      return ticket === seekTicket;
    }
    async function capture(draw) {
      if (!coach || draftBlocked()) return;
      const ticket = ++seekTicket;
      video.pause();
      if (!await ready(ticket)) { if (ticket === seekTicket) say('Wait for the video frame to load, then try again.', true); return; }
      if (video.seeking && !await seekTo(video.currentTime)) return;
      video.pause();
      if (!finite(video.currentTime) || !frameBounds()) { say('This video frame is not ready for feedback.', true); return; }
      editDraft(null);
      setDrawing(draw);
      say('Selected ' + timeLabel(draft.timestamp_seconds) + '. New feedback is private until you choose another audience.');
      if (!draw) comment.focus();
    }
    async function api(url, data) {
      const options = { credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' } };
      if (data) {
        options.method = 'POST';
        options.headers['Content-Type'] = 'application/json';
        options.headers['X-CSRFToken'] = root.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        options.body = JSON.stringify(data);
      }
      const response = await window.fetch(url, options);
      let body;
      try { body = await response.json(); }
      catch { throw new Error(response.status === 403 ? 'Access or your sign-in session changed. Refresh before trying again.' : 'Feedback is unavailable. Refresh and check your sign-in.'); }
      if (!response.ok) throw new Error(body.error || 'Feedback could not be saved or loaded.');
      return body;
    }
    function changeUrl(id) { return root.dataset.changeUrl.replace('/0/', '/' + id + '/'); }
    function button(text, action, className = 'btn btn-sm btn-outline-primary') {
      const element = document.createElement('button');
      element.type = 'button'; element.className = className; element.textContent = text;
      element.addEventListener('click', action);
      return element;
    }
    function renderNotes() {
      list.replaceChildren();
      const sorted = [...notes.values()].sort((a, b) => a.timestamp_seconds - b.timestamp_seconds || a.id - b.id);
      if (!sorted.length) { const empty = document.createElement('p'); empty.className = 'vm-hint'; empty.textContent = coach ? 'No visible feedback yet. Pause at a moment to add the first coaching cue.' : 'Your coach has not shared moment feedback yet.'; list.append(empty); }
      for (const note of sorted) {
        const card = document.createElement('article'); card.className = 'vm-note'; card.dataset.noteId = note.id;
        const header = document.createElement('div'); header.className = 'vm-note-header';
        header.append(button('▶ ' + timeLabel(note.timestamp_seconds), async () => {
          if (draftBlocked()) return;
          resetDraft(); shown = note;
          if (await seekTo(note.timestamp_seconds)) say('Showing feedback at ' + timeLabel(note.timestamp_seconds) + '.');
        }));
        const author = document.createElement('span'); author.className = 'vm-note-meta';
        author.textContent = note.author + (note.drawing.length ? ' · Drawing attached' : ''); header.append(author); card.append(header);
        if (note.comment) { const body = document.createElement('p'); body.className = 'vm-note-body'; body.textContent = note.comment; card.append(body); }
        if (coach) {
          const audience = document.createElement('span'); audience.className = 'vm-note-meta';
          audience.textContent = ({ private: 'Only author', coaches: 'Coaches', athlete: 'Athlete', parents: 'Athlete & parents' })[note.visibility] || 'Private'; card.append(audience);
        }
        if (coach && note.can_edit) {
          const actions = document.createElement('div'); actions.className = 'vm-note-actions';
          actions.append(button('Edit', async () => {
            if (draftBlocked()) return;
            editDraft(note);
            if (await seekTo(note.timestamp_seconds)) say('Editing the saved moment. Changes are not saved yet.');
          }, 'btn btn-sm btn-outline-secondary'));
          let armed = false, timer;
          const remove = button('Delete', async () => {
            if (draftBlocked()) return;
            if (!armed) { armed = true; remove.textContent = 'Confirm delete'; timer = window.setTimeout(() => { armed = false; remove.textContent = 'Delete'; }, 5000); return; }
            window.clearTimeout(timer); setBusy(true);
            try {
              await api(changeUrl(note.id), { action: 'delete', updated_at: note.updated_at });
              if (draft?.id === note.id) resetDraft();
              if (shown?.id === note.id) { shown = null; renderOverlay(); }
              await loadNotes(true); say('Moment feedback deleted.');
            } catch (error) { say(error.message, true); retry.hidden = false; }
            finally { setBusy(false); }
          }, 'btn btn-sm btn-outline-danger');
          actions.append(remove); card.append(actions);
        }
        list.append(card);
      }
      more.hidden = !nextPage;
    }
    async function loadNotes(reset = false) {
      const page = reset ? 1 : nextPage;
      if (!page) return;
      const ticket = ++loadTicket;
      const url = new URL(root.dataset.listUrl, window.location.href);
      url.searchParams.set('page', page);
      const result = await api(url.toString());
      if (ticket !== loadTicket) return false;
      if (reset) notes.clear();
      for (const note of result.notes) notes.set(note.id, note);
      nextPage = result.next_page;
      renderNotes(); retry.hidden = true;
      return true;
    }
    function position(event) {
      const bounds = frameBounds();
      if (!bounds) return null;
      return [Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width)),
              Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height))];
    }
    svg.addEventListener('pointerdown', event => {
      if (!drawing || busy || !matched(draft) || pointer !== null || (event.button !== undefined && event.button !== 0)) return;
      if (draft.drawing.length >= 50) { say('This moment already has 50 shapes. Undo or clear a shape before adding more.', true); return; }
      const point = position(event);
      if (!point) return;
      event.preventDefault(); pointer = event.pointerId;
      stroke = { tool, color, points: [point, point] };
      if (svg.setPointerCapture) svg.setPointerCapture(pointer);
      renderOverlay();
    });
    svg.addEventListener('pointermove', event => {
      if (!stroke || pointer !== event.pointerId || !matched(draft)) return;
      const point = position(event);
      if (!point) return;
      event.preventDefault();
      if (stroke.tool === 'pen') {
        if (stroke.points.length < 400) stroke.points.push(point);
        else stroke.points[399] = point;
      } else stroke.points[1] = point;
      renderOverlay();
    });
    function finishStroke(event, cancel = false) {
      if (pointer !== event.pointerId) return;
      if (stroke && !cancel && matched(draft)) {
        const count = draft.drawing.reduce((total, shape) => total + shape.points.length, 0) + stroke.points.length;
        if (count <= 5000) { draft.drawing.push(stroke); dirty = true; }
        else say('The drawing has too many points. Undo or simplify it before saving.', true);
      }
      if (svg.hasPointerCapture?.(pointer)) svg.releasePointerCapture(pointer);
      stroke = null; pointer = null; renderOverlay();
    }
    svg.addEventListener('pointerup', event => finishStroke(event));
    svg.addEventListener('pointercancel', event => finishStroke(event, true));
    svg.addEventListener('lostpointercapture', event => { if (pointer === event.pointerId) finishStroke(event, true); });
    const on = (selector, action) => root.querySelector(selector)?.addEventListener('click', action);
    on('[data-capture]', () => capture(false));
    on('[data-draw-new]', () => capture(true));
    on('[data-return-frame]', async () => { if (!busy && draft) await seekTo(draft.timestamp_seconds); });
    on('[data-toggle-draw]', async () => {
      if (busy || !draft) return;
      if (drawing) { setDrawing(false); return; }
      if (await seekTo(draft.timestamp_seconds)) setDrawing(true);
    });
    on('[data-cancel]', () => { if (busy) return; ++seekTicket; shown = null; resetDraft(); say('Draft cancelled.'); });
    on('[data-undo]', () => { if (!busy && draft?.drawing.length) { draft.drawing.pop(); dirty = true; renderOverlay(); } });
    on('[data-clear]', () => { if (!busy && draft?.drawing.length) { draft.drawing = []; dirty = true; renderOverlay(); } });
    root.querySelectorAll('[data-tool]').forEach(item => item.addEventListener('click', () => {
      if (busy || !tools.has(item.dataset.tool)) return;
      tool = item.dataset.tool;
      root.querySelectorAll('[data-tool]').forEach(button => { const selected = button.dataset.tool === tool; button.classList.toggle('active', selected); button.setAttribute('aria-pressed', String(selected)); });
    }));
    root.querySelector('[data-color]')?.addEventListener('change', event => { if (colors.has(event.target.value)) color = event.target.value; });
    comment?.addEventListener('input', () => { dirty = true; });
    visibility?.addEventListener('change', () => { dirty = true; });
    editor?.addEventListener('submit', async event => {
      event.preventDefault();
      if (busy || !draft) return;
      if (stroke) { say('Finish your current stroke before saving.', true); return; }
      const payload = { ...copy(draft), comment: comment.value.trim(), visibility: visibility.value };
      if (!payload.comment && !payload.drawing.length) { say('Add a comment or drawing before saving.', true); return; }
      setBusy(true);
      try {
        const result = await api(draft.id ? changeUrl(draft.id) : root.dataset.listUrl,
                                 draft.id ? { ...payload, action: 'update' } : payload);
        resetDraft(); shown = result.note;
        try { await loadNotes(true); } catch { retry.hidden = false; }
        notes.set(result.note.id, result.note); renderNotes();
        const revealed = await seekTo(result.note.timestamp_seconds);
        say('Saved at ' + timeLabel(result.note.timestamp_seconds) + '.' + (revealed ? '' : ' Tap its timestamp to retry showing the frame.'));
      } catch (error) { say(error.message + ' Your draft has been kept.', true); retry.hidden = false; }
      finally { setBusy(false); }
    });
    on('[data-more]', async () => { if (busy) return; setBusy(true); try { await loadNotes(); } catch (error) { say(error.message, true); retry.hidden = false; } finally { setBusy(false); } });
    on('[data-retry]', async () => { if (busy) return; setBusy(true); try { await loadNotes(true); say(draft && dirty ? 'Feedback reloaded. Cancel your draft and edit the current version to resolve conflicts.' : 'Feedback reloaded.'); } catch (error) { say(error.message, true); } finally { setBusy(false); } });
    video.addEventListener('play', () => { setDrawing(false); renderOverlay(); });
    video.addEventListener('seeking', () => { setDrawing(false); svg.style.display = 'none'; });
    ['loadedmetadata', 'loadeddata', 'seeked', 'pause', 'timeupdate'].forEach(name => video.addEventListener(name, renderOverlay));
    video.addEventListener('error', () => { setDrawing(false); svg.style.display = 'none'; say('The video could not be loaded. Saved comments remain available below.', true); });
    window.addEventListener('resize', renderOverlay);
    if (window.ResizeObserver) new window.ResizeObserver(renderOverlay).observe(video);
    loadNotes(true).then(loaded => { if (loaded && !draft && !shown) say('Choose a timestamp to view feedback.'); }).catch(error => { say(error.message, true); retry.hidden = false; });
  }
  function start() { document.querySelectorAll('[data-video-moments]').forEach(bind); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
