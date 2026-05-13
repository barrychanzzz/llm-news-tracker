/**
 * LLM News Tracker — Frontend Application
 * Renders video table, search/filter, channel relations from injected data.
 */

(function () {
  'use strict';

  // APP_DATA is injected by generate_site.py
  const data = window.APP_DATA || { videos: [], channels: [], relations: [], generated_at: null, total_videos: 0, total_channels: 0 };

  // State
  let activeTopicFilters = new Set();
  let activeChannelFilter = '';
  let searchQuery = '';

  // ─── Initialization ───────────────────────────────────────

  function init() {
    if (!data.videos.length) {
      document.getElementById('table-body').innerHTML =
        '<tr><td colspan="8" class="empty-state"><p>暂无数据。系统正在初始运行中，请稍后再来查看。</p></td></tr>';
      return;
    }

    renderStats();
    renderUpdateTime();
    populateChannelFilter();
    populateTopicFilters();
    renderTable();
    renderChannelFocus();
    renderRelations();
  }

  // ─── Stats ────────────────────────────────────────────────

  function renderStats() {
    document.getElementById('stat-channels').textContent = data.channels.length;
    document.getElementById('stat-videos').textContent = data.videos.length;
    document.getElementById('stat-relations').textContent = data.relations.length;
  }

  function renderUpdateTime() {
    if (data.generated_at) {
      const d = new Date(data.generated_at);
      const local = d.toLocaleString('zh-CN', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', timeZoneName: 'short'
      });
      document.getElementById('update-time').textContent = '🕐 数据更新：' + local;
    }
  }

  // ─── Filters ──────────────────────────────────────────────

  function populateChannelFilter() {
    const select = document.getElementById('channel-filter');
    data.channels.forEach(ch => {
      const opt = document.createElement('option');
      opt.value = ch.channel_id;
      opt.textContent = ch.name;
      select.appendChild(opt);
    });

    select.addEventListener('change', function () {
      activeChannelFilter = this.value;
      renderTable();
    });
  }

  function populateTopicFilters() {
    // Collect all unique topics
    const topicCounts = {};
    data.videos.forEach(v => {
      const topics = (v.analysis && v.analysis.topics) ? v.analysis.topics : [];
      topics.forEach(t => {
        if (t !== 'Other') {
          topicCounts[t] = (topicCounts[t] || 0) + 1;
        }
      });
    });

    const container = document.getElementById('topic-filters');
    // Sort by frequency
    Object.entries(topicCounts)
      .sort((a, b) => b[1] - a[1])
      .forEach(([topic, count]) => {
        const chip = document.createElement('span');
        chip.className = 'topic-chip';
        chip.textContent = topic + ' (' + count + ')';
        chip.addEventListener('click', function () {
          if (activeTopicFilters.has(topic)) {
            activeTopicFilters.delete(topic);
            chip.classList.remove('active');
          } else {
            activeTopicFilters.add(topic);
            chip.classList.add('active');
          }
          renderTable();
        });
        container.appendChild(chip);
      });
  }

  // ─── Search ───────────────────────────────────────────────

  document.getElementById('search-input').addEventListener('input', function () {
    searchQuery = this.value.toLowerCase().trim();
    renderTable();
  });

  // ─── Table Rendering ──────────────────────────────────────

  function getFilteredVideos() {
    return data.videos.filter(v => {
      // Channel filter
      if (activeChannelFilter && v.channel_id !== activeChannelFilter) {
        return false;
      }

      // Topic filter
      if (activeTopicFilters.size > 0) {
        const vTopics = (v.analysis && v.analysis.topics) ? v.analysis.topics : [];
        if (!vTopics.some(t => activeTopicFilters.has(t))) {
          return false;
        }
      }

      // Search query
      if (searchQuery) {
        const searchFields = [
          v.title || '',
          v.channel_name || '',
          v.analysis ? v.analysis.summary || '' : '',
          v.analysis ? v.analysis.speaker || '' : '',
          (v.analysis && v.analysis.topics) ? v.analysis.topics.join(' ') : '',
        ];
        if (!searchFields.some(f => f.toLowerCase().includes(searchQuery))) {
          return false;
        }
      }

      return true;
    });
  }

  function renderTable() {
    const filtered = getFilteredVideos();
    const tbody = document.getElementById('table-body');

    if (filtered.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="8" class="empty-state"><p>没有匹配的结果。试试调整筛选条件？</p></td></tr>';
    } else {
      tbody.innerHTML = filtered.map(v => renderVideoRow(v)).join('');
    }

    document.getElementById('result-count').textContent =
      '显示 ' + filtered.length + ' / ' + data.videos.length + ' 条视频';
  }

  function renderVideoRow(v) {
    const analysis = v.analysis || {};
    const topics = analysis.topics || [];

    return `
      <tr>
        <td class="col-channel"><strong>${esc(v.channel_name)}</strong></td>
        <td class="col-title">
          <a href="${esc(v.url)}" target="_blank" rel="noopener" class="video-link">
            ${esc(v.title)}
          </a>
          ${v.duration_string ? '<br><small style="color:var(--text-secondary)">⏱ ' + esc(v.duration_string) + '</small>' : ''}
        </td>
        <td class="col-date">${formatDate(v.published_at)}</td>
        <td class="col-views"><span class="views">${formatNumber(v.view_count)}</span></td>
        <td class="col-topics">
          <div class="tags">
            ${topics.map(t => '<span class="tag">' + esc(t) + '</span>').join('')}
            ${topics.length === 0 ? '<span class="tag" style="opacity:0.5">分析中</span>' : ''}
          </div>
        </td>
        <td class="col-speaker">${esc(analysis.speaker || '—')}</td>
        <td class="col-level">
          ${analysis.technical_level && analysis.technical_level !== 'N/A'
            ? '<span class="level-badge level-' + esc(analysis.technical_level) + '">' + esc(analysis.technical_level) + '</span>'
            : '—'}
        </td>
        <td class="col-summary">
          <div class="summary-text">${esc(analysis.summary || '等待分析...')}</div>
        </td>
      </tr>`;
  }

  // ─── Channel Focus Grid ───────────────────────────────────

  function renderChannelFocus() {
    const grid = document.getElementById('channel-focus-grid');
    grid.innerHTML = data.channels.map(ch => {
      // Get this channel's topic distribution
      const topicCounts = {};
      data.videos.forEach(v => {
        if (v.channel_id === ch.channel_id && v.analysis && v.analysis.topics) {
          v.analysis.topics.forEach(t => {
            if (t !== 'Other') topicCounts[t] = (topicCounts[t] || 0) + 1;
          });
        }
      });

      const topTopics = Object.entries(topicCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);

      return `
        <div class="focus-card">
          <h3>${esc(ch.name)}</h3>
          <p>${esc(ch.content_focus || '分析中...')}</p>
          <div class="channel-topics">
            ${topTopics.map(([t, c]) => '<span class="tag">' + esc(t) + ' (' + c + ')</span>').join('')}
          </div>
        </div>`;
    }).join('');
  }

  // ─── Relations List ───────────────────────────────────────

  function renderRelations() {
    const list = document.getElementById('relations-list');
    if (!data.relations.length) {
      list.innerHTML = '<p style="color:var(--text-secondary)">暂无频道关联数据</p>';
      return;
    }

    list.innerHTML = data.relations.map(r => `
      <div class="relation-item">
        <span class="relation-type relation-${esc(r.relation_type)}">${relationLabel(r.relation_type)}</span>
        <div class="relation-text">
          <strong>${esc(r.channel_a_name)}</strong> ↔ <strong>${esc(r.channel_b_name)}</strong>
          <br>${esc(r.description)}
        </div>
        <span class="relation-overlap">${Math.round(r.topic_overlap * 100)}% 重叠</span>
      </div>
    `).join('');
  }

  // ─── Utilities ────────────────────────────────────────────

  function esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function formatDate(isoStr) {
    if (!isoStr) return '—';
    const d = new Date(isoStr);
    const now = new Date();
    const diffMs = now - d;
    const diffH = Math.floor(diffMs / 3600000);
    const diffD = Math.floor(diffMs / 86400000);

    if (diffH < 1) return '刚刚';
    if (diffH < 24) return diffH + '小时前';
    if (diffD < 7) return diffD + '天前';

    return d.toLocaleDateString('zh-CN', {
      month: '2-digit', day: '2-digit',
    });
  }

  function formatNumber(n) {
    if (!n || n === 0) return '—';
    if (n >= 10000) {
      return (n / 10000).toFixed(1) + '万';
    }
    return n.toLocaleString();
  }

  function relationLabel(type) {
    const labels = {
      complementary: '互补',
      contrasting: '对立',
      referencing: '引用',
    };
    return labels[type] || type;
  }

  // ─── Start ────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', init);
})();
