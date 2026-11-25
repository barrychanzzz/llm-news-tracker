/**
 * Entry point — wires data, store, theme and components.
 * APP_DATA is injected by generate_site.py into index.html.
 */
import { initTheme } from './theme.js';
import { createStore } from './store.js';
import {
  renderStats, renderUpdateTime, renderChannelOptions, renderTopicChips,
  renderTableHeader, renderChannelFocus, renderRelations, renderAllForState,
} from './components.js';

(function () {
  'use strict';

  function debounce(fn, wait) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  function init() {
    initTheme();

    const data = window.APP_DATA;
    if (!data || !data.videos || !data.videos.length) {
      document.getElementById('table-body').innerHTML =
        '<tr><td colspan="8" class="empty-state"><p>暂无数据。系统正在初始运行中，请稍后再来查看。</p></td></tr>';
      return;
    }

    const store = createStore(data);

    renderStats(data);
    renderUpdateTime(data);
    renderChannelOptions(data, store);
    renderTopicChips(data, store);
    renderTableHeader(store);
    renderChannelFocus(data);
    renderRelations(data);

    // Wire search with debounce
    const search = document.getElementById('search-input');
    search.addEventListener('input', debounce(e => {
      store.state.search = e.target.value;
      store.state.page = 1;
      store.set({});
    }, 180));

    // Active filter chip counters
    const counter = document.getElementById('filter-count');
    if (counter) {
      store.subscribe(() => {
        const n = store.state.topics.size + (store.state.channel ? 1 : 0) + (store.state.search ? 1 : 0);
        counter.textContent = n ? `${n} 项筛选` : '';
        counter.classList.toggle('visible', n > 0);
      });
    }

    // Clear filters button
    const clear = document.getElementById('clear-filters');
    if (clear) {
      clear.addEventListener('click', () => {
        search.value = '';
        document.getElementById('channel-filter').value = '';
        store.clearFilters();
      });
      store.subscribe(() => {
        clear.classList.toggle('visible',
          store.state.topics.size > 0 || !!store.state.channel || !!store.state.search);
      });
    }

    // Page size selector
    const pageSize = document.getElementById('page-size');
    if (pageSize) {
      pageSize.addEventListener('change', e => store.setPageSize(parseInt(e.target.value, 10)));
    }

    // Subscribe rendering last so initial state is consistent
    store.subscribe(() => renderAllForState(store));
    renderAllForState(store);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
