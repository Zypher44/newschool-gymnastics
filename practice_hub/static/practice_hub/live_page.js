/* Update existing Django forms without a full-page reload. */
(() => {
  'use strict';
  if (!document.querySelector('[data-live-page]') || !window.fetch) return;
  let busy = false;
  const root = () => document.querySelector('[data-live-page]');
  function notify(message, error = false) {
    const status = root()?.querySelector('[data-live-messages]');
    if (status) { status.textContent = message; status.className = error ? 'alert alert-danger' : 'ph-live-status'; }
  }
  async function update(url, options = {}, historyMode = 'push', source = null) {
    if (busy) return;
    const current = root();
    const before = new CustomEvent('live:before-navigate', {bubbles:true, cancelable:true, detail:{source, method:options.method || 'GET'}});
    if (!current.dispatchEvent(before)) return;
    busy = true;
    const scroll = window.scrollY;
    const toolsOpen = current.querySelector('.ph-tools')?.open;
    const focused = document.activeElement;
    const timerId = focused?.closest('form')?.querySelector('[name=timer_athlete]')?.value;
    const name = focused?.name;
    current.setAttribute('aria-busy', 'true');
    if (current.id === 'ph-practice') current.inert = true;
    notify('Updating…');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch(url, {...options, credentials:'same-origin', cache:'no-store',
        signal:controller.signal, headers:{'X-Requested-With':'XMLHttpRequest', ...(options.headers || {})}});
      if (!response.ok) throw new Error(`Request failed (${response.status}).`);
      const page = new DOMParser().parseFromString(await response.text(), 'text/html');
      const replacement = page.querySelector(`[data-live-page][id="${current.id}"]`);
      if (!replacement || new URL(response.url || url, location.href).pathname !== location.pathname) {
        throw new Error('The page could not be updated. Refresh to check your sign-in and current data.');
      }
      const status = replacement.querySelector('[data-live-messages]');
      if (status) page.querySelectorAll('.main-content > .alert').forEach(alert => {
        const copy = alert.cloneNode(true);
        copy.querySelectorAll('button').forEach(button => button.remove());
        status.append(copy);
      });
      if (toolsOpen && replacement.querySelector('.ph-tools')) replacement.querySelector('.ph-tools').open = true;
      const target = new URL(response.url || url, location.href);
      if (historyMode === 'push' && (options.method !== 'POST' || response.redirected) && target.href !== location.href) history.pushState({}, '', target.href);
      replacement.inert = false;
      current.replaceWith(replacement);
      document.dispatchEvent(new CustomEvent('live:updated', {detail:{root:replacement}}));
      if (timerId && name) {
        const form = Array.from(replacement.querySelectorAll('.ph-child-timer')).find(f => f.querySelector('[name=timer_athlete]')?.value === timerId);
        form?.querySelector(`[name="${name}"]`)?.focus({preventScroll:true});
      }
      window.scrollTo({top:scroll, behavior:'instant'});
    } catch (error) {
      // A failed response may follow a successful save. Never resubmit a POST automatically.
      notify((error.message || 'Update failed.') + ' Your displayed changes are kept. Refresh to check whether the last action saved before trying again.', true);
    } finally {
      clearTimeout(timeout);
      busy = false;
      root()?.removeAttribute('aria-busy');
      if (root()?.id === 'ph-practice') root().inert = false;
    }
  }
  document.addEventListener('click', event => {
    const anchor = event.target.closest('a');
    if (!anchor || !root()?.contains(anchor) || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || anchor.target || anchor.download) return;
    const url = new URL(anchor.href, location.href);
    if (url.origin !== location.origin || url.pathname !== location.pathname || url.hash) return;
    event.preventDefault();
    update(url.href, {}, 'push', anchor);
  });
  document.addEventListener('submit', event => {
    const form = event.target;
    if (!root()?.contains(form)) return;
    const submitter = event.submitter;
    if (['open_skill', 'open_routine'].includes(submitter?.value)) return;
    const url = new URL(form.action || location.href, location.href);
    if (url.origin !== location.origin || url.pathname !== location.pathname) return;
    event.preventDefault();
    const data = new FormData(form);
    if (submitter?.name) data.append(submitter.name, submitter.value);
    if (form.method.toLowerCase() === 'get') {
      url.search = new URLSearchParams(data).toString();
      update(url.href, {}, 'push', form);
    } else update(url.href, {method:'POST', body:data}, 'push', form);
  });
  window.addEventListener('popstate', () => update(location.href, {}, 'none', null));
})();
