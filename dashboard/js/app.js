/**
 * app.js – Aegis Trader Dashboard Application Logic
 */

'use strict';

// ── State ──────────────────────────────────────────────────────────────────

const state = {
    mode: 'analyze',
    autoTrade: false,
    connected: false,
    refreshInterval: null,
};

// ── DOM Helpers ────────────────────────────────────────────────────────────

const $ = (id) => document.getElementById(id);
const el = (tag, cls, html = '') => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    e.innerHTML = html;
    return e;
};

function showToast(msg, duration = 2500) {
    const t = $('toast');
    t.textContent = msg;
    t.classList.remove('hidden');
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.add('hidden'), duration);
}

function setConnectionState(ok) {
    state.connected = ok;
    const dot = $('connDot');
    dot.className = 'connection-dot ' + (ok ? 'connected' : 'error');
    $('backendUrl').textContent = ok ? AegisAPI.base : 'Disconnected';
}

// ── Tabs ───────────────────────────────────────────────────────────────────

function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
            btn.classList.add('active');
            $(`tab-${btn.dataset.tab}`).classList.add('active');
            if (btn.dataset.tab === 'signals') loadSignals();
            if (btn.dataset.tab === 'trades') loadTrades();
        });
    });
}

// ── Mode Buttons ───────────────────────────────────────────────────────────

function setActiveModeBtn(mode) {
    document.querySelectorAll('.mode-btn[data-mode]').forEach(b => {
        b.classList.toggle('active', b.dataset.mode === mode);
    });
}

function initModeButtons() {
    document.querySelectorAll('.mode-btn[data-mode]').forEach(btn => {
        btn.addEventListener('click', async () => {
            try {
                await AegisAPI.switchMode(btn.dataset.mode);
                state.mode = btn.dataset.mode;
                setActiveModeBtn(btn.dataset.mode);
                $('modeVal').textContent = btn.dataset.mode.toUpperCase();
                showToast(`✅ Mode: ${btn.dataset.mode}`);
            } catch (e) {
                showToast('❌ Mode switch failed');
            }
        });
    });

    $('btnCloseAll').addEventListener('click', async () => {
        if (!confirm('Close ALL open positions?')) return;
        try {
            const res = await AegisAPI.closeAll();
            showToast(`🔒 Closed ${res.closed} position(s)`);
            loadStatus();
        } catch (e) {
            showToast('❌ Close all failed');
        }
    });
}

// ── Auto Trade Toggle ──────────────────────────────────────────────────────

function initAutoTradeToggle() {
    $('autoTradeToggle').addEventListener('change', async (e) => {
        try {
            await AegisAPI.updateSettings({ auto_trade_enabled: e.target.checked });
            showToast(e.target.checked ? '✅ Auto trading ON' : '⛔ Auto trading OFF');
        } catch (err) {
            e.target.checked = !e.target.checked; // revert
            showToast('❌ Failed to update setting');
        }
    });
}

// ── Status ─────────────────────────────────────────────────────────────────

async function loadStatus() {
    try {
        const s = await AegisAPI.getStatus();
        setConnectionState(true);

        // Status bar
        $('modeVal').textContent = s.mode.toUpperCase();
        $('sessionVal').textContent = s.active_session
            ? s.active_session.replace('_', ' ').toUpperCase()
            : 'CLOSED';
        $('tradesVal').textContent = `${s.trades_today}/2`;
        $('ddVal').textContent = `${s.drawdown_today_pct.toFixed(2)}%`;

        // Mode button highlight
        state.mode = s.mode;
        setActiveModeBtn(s.mode);

        // Auto trade toggle
        $('autoTradeToggle').checked = s.auto_trade_enabled;

        // Risk grid
        $('riskTrades').textContent = `${s.trades_today}/2`;
        $('riskLosses').textContent = `${s.losses_today}/2`;
        $('riskDD').textContent = `${s.drawdown_today_pct.toFixed(2)}%`;
        $('riskPos').textContent = s.open_positions;

        // Colour-code risk values
        const riskPct = s.drawdown_today_pct;
        $('riskDD').className = 'risk-value' + (riskPct >= 2 ? ' danger' : riskPct >= 1.5 ? ' warn' : '');

        // Risk bar
        const fill = Math.min((riskPct / 2) * 100, 100);
        $('riskBarFill').style.width = fill + '%';

        // Alerts
        const banner = $('alertBanner');
        if (s.risk_limit_hit) {
            banner.textContent = '🚨 Risk limit reached. Auto trading disabled.';
            banner.className = 'alert-banner';
        } else if (s.news_blackout_active) {
            banner.textContent = '📰 News blackout active. Auto trading paused.';
            banner.className = 'alert-banner warn';
        } else if (!s.active_session) {
            banner.textContent = '⏰ Outside session hours. Monitoring only.';
            banner.className = 'alert-banner warn';
        } else {
            banner.classList.add('hidden');
        }
        if (!banner.classList.contains('hidden')) banner.classList.remove('hidden');

        // Live positions
        await loadPositions();

    } catch (e) {
        setConnectionState(false);
    }
}

// ── Positions ──────────────────────────────────────────────────────────────

async function loadPositions() {
    try {
        const positions = await AegisAPI.getPositions();
        const list = $('positionsList');
        $('posCount').textContent = positions.length;

        if (!positions.length) {
            list.innerHTML = '<div class="empty-state">No open positions</div>';
            return;
        }

        list.innerHTML = '';
        positions.forEach(p => {
            const pnlSign = p.pnl >= 0 ? '+' : '';
            const card = el('div', 'position-card', `
        <div class="pos-header">
          <div>
            <span class="pos-dir-badge ${p.direction}">${p.direction.toUpperCase()}</span>
            <span style="font-weight:600;margin-left:8px;font-size:14px">${p.symbol}</span>
            <span style="color:var(--text-muted);font-size:12px;margin-left:4px">#${p.ticket}</span>
          </div>
          <div class="pos-pnl ${p.pnl >= 0 ? 'positive' : 'negative'}">${pnlSign}$${p.pnl.toFixed(2)}</div>
        </div>
        <div class="pos-details">
          <div class="pos-detail">
            <span class="pos-detail-label">Entry</span>
            <div class="pos-detail-val">${p.open_price.toLocaleString()}</div>
          </div>
          <div class="pos-detail">
            <span class="pos-detail-label">Current</span>
            <div class="pos-detail-val">${p.current_price.toLocaleString()}</div>
          </div>
          <div class="pos-detail">
            <span class="pos-detail-label">Lots</span>
            <div class="pos-detail-val">${p.lot_size}</div>
          </div>
        </div>
      `);
            list.appendChild(card);
        });
    } catch (_) { }
}

// ── Signals ────────────────────────────────────────────────────────────────

function gradeClass(grade) {
    if (grade === 'A+') return 'aplus';
    if (grade === 'A') return 'a';
    return 'b';
}

async function loadSignals() {
    try {
        const signals = await AegisAPI.getSignals(20);
        const list = $('signalsList');
        $('signalCount').textContent = signals.length;

        if (!signals.length) {
            list.innerHTML = '<div class="empty-state">No signals yet</div>';
            return;
        }

        list.innerHTML = '';
        signals.forEach(s => {
            const dir = s.direction;
            const gc = gradeClass(s.grade);
            const fill = Math.min(s.score, 100);
            const time = new Date(s.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const setupLabel = s.setup_type ? s.setup_type.replace(/_/g, ' ') : '';
            const paperResult = s.paper_result ? ` | ${s.paper_result.toUpperCase()}` : '';
            const card = el('div', `signal-card ${dir} ${gc === 'aplus' ? 'grade-aplus' : ''}`, `
        <div class="signal-header">
          <span class="signal-dir ${dir}">${dir.toUpperCase()} ${dir === 'long' ? '▲' : '▼'}</span>
          <span class="signal-grade ${gc}">${s.grade}${paperResult}</span>
        </div>
        <div class="signal-prices">
          <div class="signal-price-item"><span>Entry</span><span>${parseFloat(s.entry_price).toLocaleString()}</span></div>
          <div class="signal-price-item"><span>SL</span><span>${parseFloat(s.stop_loss).toLocaleString()}</span></div>
          <div class="signal-price-item"><span>TP1</span><span>${parseFloat(s.tp1).toLocaleString()}</span></div>
          <div class="signal-price-item"><span>TP2</span><span>${parseFloat(s.tp2).toLocaleString()}</span></div>
        </div>
        <div class="signal-score-bar">
          <div class="signal-score-fill" style="width:${fill}%"></div>
        </div>
        <div class="signal-meta">
          <span>Score: <b>${s.score}/100</b></span>
          <span>${s.session_name ? s.session_name.replace('_', ' ') : '—'}</span>
          <span>${!s.news_blocked ? '✅ News clear' : '⛔ News'}</span>
          <span style="margin-left:auto;opacity:0.6">${time}</span>
        </div>
        ${setupLabel ? `<div class="signal-setup">${setupLabel}</div>` : ''}
      `);
            list.appendChild(card);
        });
    } catch (_) { }
}

// ── Trades ─────────────────────────────────────────────────────────────────

async function loadTrades() {
    try {
        const trades = await AegisAPI.getTrades(20);
        const list = $('tradesList');
        $('tradeCount').textContent = trades.length;

        if (!trades.length) {
            list.innerHTML = '<div class="empty-state">No trades recorded</div>';
            return;
        }

        list.innerHTML = '';
        trades.forEach(t => {
            const pnl = t.pnl || 0;
            const pnlStr = `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`;
            const time = new Date(t.opened_at).toLocaleDateString([], { month: 'short', day: 'numeric' });
            const card = el('div', 'trade-card', `
        <div class="trade-info">
          <div class="trade-symbol">${t.symbol} <span style="font-size:12px;color:${t.direction === 'long' ? 'var(--bull)' : 'var(--bear)'}">${t.direction.toUpperCase()}</span></div>
          <div class="trade-meta">${time} · ${t.lot_size} lots ${t.mt5_ticket ? `· #${t.mt5_ticket}` : ''}</div>
          <span class="trade-status-badge ${t.status}">${t.status.toUpperCase()}</span>
        </div>
        <div>
          <div class="trade-pnl" style="color:${pnl >= 0 ? 'var(--bull)' : 'var(--bear)'}">${t.status !== 'open' ? pnlStr : '—'}</div>
        </div>
      `);
            list.appendChild(card);
        });
    } catch (_) { }
}

// ── Settings Form ──────────────────────────────────────────────────────────

async function loadSettings() {
    try {
        const s = await AegisAPI.getSettings();

        // Lot mode handling - display based on mode
        const lotModeSelect = $('setLotMode');
        if (lotModeSelect) lotModeSelect.value = s.lot_mode || 'minimum_lot';

        $('setFixedLot').value = s.fixed_lot || 0.01;
        $('setRiskPct').value = s.risk_percent || 1.0;
        $('setMaxTrades').value = s.max_trades_per_day;
        $('setMaxLosses').value = s.max_losses_per_day;
        $('setMaxDD').value = s.max_daily_drawdown_pct;
        $('setMaxSpread').value = s.spread_max_points;

        // Toggle visibility of lot size fields based on mode
        updateLotModeFields();
    } catch (_) { }
}

function updateLotModeFields() {
    const mode = $('setLotMode')?.value || 'minimum_lot';
    const fixedGroup = $('fixedLotGroup');
    const riskGroup = $('riskPctGroup');

    if (fixedGroup && riskGroup) {
        fixedGroup.style.display = mode === 'fixed_lot' ? 'block' : 'none';
        riskGroup.style.display = mode === 'risk_percent' ? 'block' : 'none';
    }
}

function initSettingsForm() {
    // Lot mode change handler
    const lotModeSelect = $('setLotMode');
    if (lotModeSelect) {
        lotModeSelect.addEventListener('change', updateLotModeFields);
    }

    $('riskForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const lotMode = $('setLotMode')?.value || 'minimum_lot';
        const data = {
            lot_mode: lotMode,
            max_trades_per_day: parseInt($('setMaxTrades').value),
            max_losses_per_day: parseInt($('setMaxLosses').value),
            max_daily_drawdown_pct: parseFloat($('setMaxDD').value),
            spread_max_points: parseFloat($('setMaxSpread').value),
        };

        // Add lot-specific fields based on mode
        if (lotMode === 'fixed_lot') {
            data.fixed_lot = parseFloat($('setFixedLot').value);
        } else if (lotMode === 'risk_percent') {
            data.risk_percent = parseFloat($('setRiskPct').value);
        }

        try {
            await AegisAPI.updateSettings(data);
            showToast('✅ Settings saved');
        } catch (_) {
            showToast('❌ Save failed');
        }
    });
}

// ── Paper Trade Stats ──────────────────────────────────────────────────────

async function loadPaperTradeStats() {
    try {
        const stats = await AegisAPI.getPaperTradeStats(30);
        const container = $('paperTradeStats');
        if (!container) return;

        if (stats.total === 0) {
            container.innerHTML = '<div class="empty-state">No paper trades yet</div>';
            return;
        }

        const winRate = stats.win_rate.toFixed(1);
        const winRateClass = stats.win_rate >= 50 ? 'positive' : 'negative';

        container.innerHTML = `
            <div class="paper-stats-grid">
                <div class="stat-item">
                    <div class="stat-value">${stats.total}</div>
                    <div class="stat-label">Total Signals</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value positive">${stats.wins}</div>
                    <div class="stat-label">Winners</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value negative">${stats.losses}</div>
                    <div class="stat-label">Losers</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value ${winRateClass}">${winRate}%</div>
                    <div class="stat-label">Win Rate</div>
                </div>
            </div>
            ${renderGradeBreakdown(stats.by_grade)}
        `;
    } catch (_) { }
}

function renderGradeBreakdown(byGrade) {
    if (!byGrade || Object.keys(byGrade).length === 0) return '';

    let html = '<div class="grade-breakdown"><div class="breakdown-title">By Grade</div><div class="breakdown-grid">';
    for (const [grade, data] of Object.entries(byGrade)) {
        const wr = data.win_rate ? data.win_rate.toFixed(0) : 0;
        const gradeClass = grade === 'A+' ? 'aplus' : grade.toLowerCase();
        html += `
            <div class="breakdown-item">
                <span class="grade-badge ${gradeClass}">${grade}</span>
                <span>${data.count} trades · ${wr}% WR</span>
            </div>
        `;
    }
    html += '</div></div>';
    return html;
}

// ── Refresh ────────────────────────────────────────────────────────────────

$('refreshBtn').addEventListener('click', () => {
    loadStatus();
    showToast('🔄 Refreshed');
});

// Auto-refresh every 10 seconds
function startAutoRefresh() {
    state.refreshInterval = setInterval(loadStatus, 10_000);
}

// ── Boot ───────────────────────────────────────────────────────────────────

async function init() {
    initTabs();
    initModeButtons();
    initAutoTradeToggle();
    initSettingsForm();
    await loadStatus();
    await loadSettings();
    await loadPaperTradeStats();
    startAutoRefresh();
}

document.addEventListener('DOMContentLoaded', init);
