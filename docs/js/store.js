/**
 * Store — central state, filtering, sorting and pagination logic
 */
export function createStore(data) {
  const state = {
    search: '',
    channel: '',
    topics: new Set(),
    sortKey: 'published_at',
    sortDir: 'desc',
    page: 1,
    pageSize: 30,
  };

  const listeners = new Set();
  const emit = () => listeners.forEach(fn => fn());

  function subscribe(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  }

  function set(patch) {
    Object.assign(state, patch);
    emit();
  }

  function toggleTopic(topic) {
    if (state.topics.has(topic)) state.topics.delete(topic);
    else state.topics.add(topic);
    state.page = 1;
    emit();
  }

  function toggleSort(key) {
    if (state.sortKey === key) {
      state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      state.sortKey = key;
      state.sortDir = key === 'title' ? 'asc' : 'desc';
    }
    state.page = 1;
    emit();
  }

  function getFiltered() {
    const q = state.search.toLowerCase().trim();
    let list = data.videos.filter(v => {
      if (state.channel && v.channel_id !== state.channel) return false;
      if (state.topics.size) {
        const topics = v.analysis?.topics || [];
        if (!topics.some(t => state.topics.has(t))) return false;
      }
      if (q) {
        const fields = [
          v.title || '', v.channel_name || '',
          v.analysis?.summary || '', v.analysis?.speaker || '',
          (v.analysis?.topics || []).join(' '),
        ];
        if (!fields.some(f => f.toLowerCase().includes(q))) return false;
      }
      return true;
    });

    const dir = state.sortDir === 'asc' ? 1 : -1;
    const key = state.sortKey;
    list.sort((a, b) => {
      let av, bv;
      if (key === 'published_at') {
        av = a.published_at || ''; bv = b.published_at || '';
      } else if (key === 'view_count') {
        av = a.view_count || 0; bv = b.view_count || 0;
      } else if (key === 'title') {
        av = (a.title || '').toLowerCase(); bv = (b.title || '').toLowerCase();
      } else if (key === 'channel') {
        av = (a.channel_name || '').toLowerCase(); bv = (b.channel_name || '').toLowerCase();
      } else {
        av = a[key] ?? ''; bv = b[key] ?? '';
      }
      if (av < bv) return -1 * dir;
      if (av > bv) return 1 * dir;
      return 0;
    });

    return list;
  }

  function getPageSlice(list) {
    const start = (state.page - 1) * state.pageSize;
    return {
      rows: list.slice(start, start + state.pageSize),
      totalPages: Math.max(1, Math.ceil(list.length / state.pageSize)),
      start: list.length ? start + 1 : 0,
      end: Math.min(start + state.pageSize, list.length),
    };
  }

  function clearFilters() {
    state.search = '';
    state.channel = '';
    state.topics.clear();
    state.page = 1;
    emit();
  }

  return {
    state, data, subscribe, set, toggleTopic, toggleSort,
    getFiltered, getPageSlice, clearFilters,
    setPage: (p) => set({ page: p }),
    setPageSize: (n) => set({ pageSize: n, page: 1 }),
  };
}
