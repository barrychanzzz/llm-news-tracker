/**
 * Components — pure render functions. All dynamic strings are escaped.
 */
import { createStore } from './store.js';

export function esc(str) {
  if (str == null) return '';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}

/** Only allow safe http(s) URLs — prevents javascript: XSS */
export function safeUrl(url) {
  try {
    const u = new URL(url, window.location.href);
    return (u.protocol === 'http:' || u.protocol === 'https:') ? u.href : '#';
  } catch (e) {
    return '#';
  }
}

export function formatDate(isoStr) {
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return '—';
  const now = new Date();
  const diffH = Math.floor((now - d) / 3600000);
  const diffD = Math.floor((now - d) / 86400000);
  if (diffH < 1) return '刚刚';
  if (diffH < 24) return diffH + '小时前';
  if (diffD < 7) return diffD + '天前';
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
}

export function formatNumber(n) {
  if (!n || n === 0) {
    return '<span class="view-na" title="YouTube 限制了播放量数据的自动获取">N/A</span>';
  }
  if (n >= 10000) return (n / 10000).toFixed(1) + '万';
  return n.toLocaleString();
}

export function sortIndicator(store, key) {
  if (store.state.sortKey !== key) return '<span class="sort-icon">↕</span>';
  return store.state.sortDir === 'asc'
    ? '<span class="sort-icon active">↑</span>'
    : '<span class="sort-icon active">↓</span>';
}

export function renderStats(data) {
  document.getElementById('stat-channels').textContent = data.channels.length;
  document.getElementById('stat-videos').textContent = data.videos.length;
  document.getElementById('stat-relations').textContent = data.relations.length;
}

export function renderUpdateTime(data) {
  if (!data.generated_at) return;
  const d = new Date(data.generated_at);
  if (isNaN(d.getTime())) return;
  const local = d.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', timeZoneName: 'short',
  });
  document.getElementById('update-time').textContent = '🕐 数据更新：' + local;
}

export function renderChannelOptions(data, store) {
  const select = document.getElementById('channel-filter');
  data.channels.forEach(ch => {
    const opt = document.createElement('option');
    opt.value = ch.channel_id;
    opt.textContent = ch.name;
    select.appendChild(opt);
  });
  select.addEventListener('change', () => {
    store.state.channel = select.value;
    store.state.page = 1;
    store.set({});
  });
}

export function renderTopicChips(data, store) {
  const counts = {};
  data.videos.forEach(v => {
    (v.analysis?.topics || []).forEach(t => {
      if (t !== 'Other') counts[t] = (counts[t] || 0) + 1;
    });
  });
  const container = document.getElementById('topic-filters');
  container.innerHTML = '';
  Object.entries(counts).sort((a, b) => b[1] - a[1]).forEach(([topic, count]) => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'topic-chip';
    chip.textContent = topic + ' (' + count + ')';
    chip.setAttribute('aria-pressed', 'false');
    chip.addEventListener('click', () => store.toggleTopic(topic));
    container.appendChild(chip);
  });
  store.subscribe(() => {
    container.querySelectorAll('.topic-chip').forEach(chip => {
      const name = chip.textContent.replace(/\s*\(\d+\)$/, '');
      const active = store.state.topics.has(name);
      chip.classList.toggle('active', active);
      chip.setAttribute('aria-pressed', String(active));
    });
  });
}

export function renderTableHeader(store) {
  const thead = document.getElementById('table-head-row');
  thead.innerHTML = [
    ['channel', '频道'], ['title', '视频标题'], ['published_at', '发布时间'],
    ['view_count', '播放量'], [null, '主题标签'], [null, '主讲人'],
    [null, '深度'], [null, 'AI 内容摘要'],
  ].map(([key, label]) => {
    if (!key) return `<th>${esc(label)}</th>`;
    return `<th><button type="button" class="sort-btn" data-sort="${key}" aria-label="按${esc(label)}排序">${esc(label)} ${sortIndicator(store, key)}</button></th>`;
  }).join('');
  thead.querySelectorAll('[data-sort]').forEach(btn => {
    btn.addEventListener('click', () => store.toggleSort(btn.getAttribute('data-sort')));
  });
  store.subscribe(() => {
    thead.querySelectorAll('[data-sort]').forEach(btn => {
      const key = btn.getAttribute('data-sort');
      const label = btn.childNodes[0].textContent.trim();
      btn.innerHTML = `${esc(label)} ${sortIndicator(store, key)}`;
    });
  });
}

export function renderVideoRow(v) {
  const a = v.analysis || {};
  const topics = a.topics || [];
  const level = a.technical_level;
  return `
    <tr>
      <td class="col-channel" data-label="频道"><strong>${esc(v.channel_name)}</strong></td>
      <td class="col-title" data-label="视频标题">
        <a href="${esc(safeUrl(v.url))}" target="_blank" rel="noopener noreferrer" class="video-link">${esc(v.title)}</a>
        ${v.duration_string ? `<br><small class="duration">⏱ ${esc(v.duration_string)}</small>` : ''}
      </td>
      <td class="col-date" data-label="发布时间">${formatDate(v.published_at)}</td>
      <td class="col-views" data-label="播放量"><span class="views">${formatNumber(v.view_count)}</span></td>
      <td class="col-topics" data-label="主题标签"><div class="tags">${topics.map(t => `<span class="tag">${esc(t)}</span>`).join('')}</div></td>
      <td class="col-speaker" data-label="主讲人">${esc(a.speaker || '—')}</td>
      <td class="col-level" data-label="深度">${level && level !== 'N/A' ? `<span class="level-badge level-${esc(level)}">${esc(level)}</span>` : '—'}</td>
      <td class="col-summary" data-label="AI 摘要"><div class="summary-text">${esc(a.summary || '等待分析...')}</div></td>
    </tr>`;
}

export function renderTableBody(store) {
  const { rows } = store.getPageSlice(store.getFiltered());
  document.getElementById('table-body').innerHTML =
    rows.length
      ? rows.map(renderVideoRow).join('')
      : '<tr><td colspan="8" class="empty-state"><p>没有匹配的结果。试试调整筛选条件？</p></td></tr>';
}

export function renderPagination(store) {
  const list = store.getFiltered();
  const { totalPages, start, end } = store.getPageSlice(list);
  const el = document.getElementById('pagination');
  if (!el) return;

  let buttons = '';
  const current = store.state.page;
  const add = (p, label, disabled = false, active = false) => {
    buttons += `<button type="button" class="page-btn${active ? ' active' : ''}" data-page="${p}" ${disabled ? 'disabled' : ''}>${label}</button>`;
  };
  add(current - 1, '‹', current <= 1);
  const windowSize = 2;
  const from = Math.max(1, current - windowSize);
  const to = Math.min(totalPages, current + windowSize);
  if (from > 1) add(1, '1');
  if (from > 2) buttons += '<span class="page-ellipsis">…</span>';
  for (let p = from; p <= to; p++) add(p, String(p), false, p === current);
  if (to < totalPages - 1) buttons += '<span class="page-ellipsis">…</span>';
  if (to < totalPages) add(totalPages, String(totalPages));
  add(current + 1, '›', current >= totalPages);

  el.innerHTML = `
    <div class="page-info">显示 ${start}–${end}，共 ${list.length} 条 · 第 ${current}/${totalPages} 页</div>
    <div class="page-controls">${buttons}</div>`;
  el.querySelectorAll('[data-page]:not([disabled])').forEach(btn => {
    btn.addEventListener('click', () => {
      store.setPage(parseInt(btn.getAttribute('data-page'), 10));
      document.getElementById('video-table').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}

export function renderChannelFocus(data) {
  document.getElementById('channel-focus-grid').innerHTML = data.channels.map(ch => {
    const counts = {};
    data.videos.forEach(v => {
      if (v.channel_id === ch.channel_id) {
        (v.analysis?.topics || []).forEach(t => {
          if (t !== 'Other') counts[t] = (counts[t] || 0) + 1;
        });
      }
    });
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 5);
    return `
      <div class="focus-card">
        <h3>${esc(ch.name)}</h3>
        <p>${esc(ch.content_focus || '分析中...')}</p>
        <div class="channel-topics">${top.map(([t, c]) => `<span class="tag">${esc(t)} (${c})</span>`).join('')}</div>
      </div>`;
  }).join('');
}

function relationLabel(type) {
  return { complementary: '互补', contrasting: '对立', referencing: '引用' }[type] || type;
}

export function renderRelations(data) {
  const list = document.getElementById('relations-list');
  if (!data.relations.length) {
    list.innerHTML = '<p class="muted">暂无频道关联数据</p>';
    return;
  }
  list.innerHTML = data.relations.map(r => `
    <div class="relation-item">
      <span class="relation-type relation-${esc(r.relation_type)}">${relationLabel(r.relation_type)}</span>
      <div class="relation-text">
        <strong>${esc(r.channel_a_name)}</strong> ↔ <strong>${esc(r.channel_b_name)}</strong>
        <br>${esc(r.description)}
      </div>
      <span class="relation-overlap">${Math.round((r.topic_overlap || 0) * 100)}% 重叠</span>
    </div>`).join('');
}

export function renderAllForState(store) {
  renderTableBody(store);
  renderPagination(store);
  document.getElementById('result-count').textContent =
    `显示 ${store.getFiltered().length} / ${store.data.videos.length} 条视频`;
}

export { createStore };
