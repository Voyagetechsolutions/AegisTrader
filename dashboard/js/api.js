/**
 * api.js – Backend API client for Aegis Trader dashboard
 * Sets the backend URL and wraps all fetch calls.
 */

// Set this to your Render backend URL (or http://localhost:8000 for dev)
const API_BASE = window.AEGIS_API_URL || 'http://localhost:8000';

window.AegisAPI = (() => {
  async function request(method, path, body = null) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);
    const resp = await fetch(`${API_BASE}${path}`, opts);
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
    return resp.json();
  }

  return {
    base: API_BASE,

    // Status
    getStatus:        ()           => request('GET',   '/dashboard/status'),

    // Signals
    getSignals:       (limit = 20) => request('GET',   `/dashboard/signals?limit=${limit}`),

    // Trades
    getTrades:        (limit = 20) => request('GET',   `/dashboard/trades?limit=${limit}`),
    getPositions:     ()           => request('GET',   '/dashboard/positions'),
    closeAll:         ()           => request('POST',  '/dashboard/closeall'),

    // Settings
    getSettings:      ()           => request('GET',   '/dashboard/settings'),
    updateSettings:   (data)       => request('PATCH', '/dashboard/settings', data),
    switchMode:       (mode)       => request('POST',  `/dashboard/mode/${mode}`),

    // Overview
    getOverview:      ()           => request('GET',   '/dashboard/overview'),

    // Paper trade stats (analyze mode performance)
    getPaperTradeStats: (days = 30) => request('GET', `/dashboard/paper-trades/stats?days=${days}`),

    // Performance reports
    getPerformance:   (days = 30)  => request('GET',   `/dashboard/reports/performance?days=${days}`),

    // Health
    health:           ()           => request('GET',   '/health'),
  };
})();
