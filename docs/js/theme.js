/**
 * Theme module — light / dark / system tri-state with persistence
 * Applies data-theme on <html>; CSS variables handle the rest.
 */
const STORAGE_KEY = 'llm-news-theme';
const VALID = ['light', 'dark', 'system'];

function systemPrefersDark() {
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function resolve(theme) {
  if (theme === 'system') return systemPrefersDark() ? 'dark' : 'light';
  return theme;
}

function apply(theme) {
  const effective = resolve(theme);
  document.documentElement.setAttribute('data-theme', effective);
  document.documentElement.setAttribute('data-theme-choice', theme);
  // Update toggle button labels/active state
  document.querySelectorAll('[data-theme-option]').forEach(btn => {
    const active = btn.getAttribute('data-theme-option') === theme;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-pressed', String(active));
  });
  return effective;
}

export function initTheme() {
  let saved = 'system';
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (VALID.includes(stored)) saved = stored;
  } catch (e) { /* storage may be unavailable */ }

  apply(saved);

  // React to OS theme changes when in system mode
  if (window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => {
      const choice = document.documentElement.getAttribute('data-theme-choice');
      if (choice === 'system') apply('system');
    };
    if (mq.addEventListener) mq.addEventListener('change', onChange);
    else if (mq.addListener) mq.addListener(onChange);
  }

  // Wire toggle buttons
  document.querySelectorAll('[data-theme-option]').forEach(btn => {
    btn.addEventListener('click', () => {
      const choice = btn.getAttribute('data-theme-option');
      if (!VALID.includes(choice)) return;
      apply(choice);
      try { localStorage.setItem(STORAGE_KEY, choice); } catch (e) { /* noop */ }
    });
  });
}
