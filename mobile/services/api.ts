import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

// Your computer's IP address - change this to match your network
const API_BASE_URL = __DEV__
  ? 'http://192.168.8.152:8000'
  : 'https://your-render-app.onrender.com';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Log all requests for debugging
api.interceptors.request.use((config) => {
  console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error(`API Error: ${error.message}`);
    return Promise.reject(error);
  }
);

// Dashboard API - connects to /dashboard/* endpoints
export const dashboardApi = {
  getStatus: async () => {
    const { data } = await api.get('/dashboard/status');
    return data;
  },

  getSignals: async (limit: number = 20, grade?: string) => {
    const params: any = { limit };
    if (grade) params.grade = grade;
    const { data } = await api.get('/dashboard/signals', { params });
    return data;
  },

  getTrades: async (limit: number = 20, status?: string) => {
    const params: any = { limit };
    if (status) params.status_filter = status;
    const { data } = await api.get('/dashboard/trades', { params });
    return data;
  },

  getPositions: async () => {
    const { data } = await api.get('/dashboard/positions');
    return data;
  },

  closeAll: async () => {
    const { data } = await api.post('/dashboard/closeall');
    return data;
  },

  getSettings: async () => {
    const { data } = await api.get('/dashboard/settings');
    return data;
  },

  updateSettings: async (updates: any) => {
    const { data } = await api.post('/dashboard/settings/update', updates);
    return data;
  },

  switchMode: async (mode: string) => {
    const { data } = await api.post(`/dashboard/mode/${mode}`);
    return data;
  },

  activateEmergencyStop: async (reason: string, closePositions: boolean = false) => {
    const { data } = await api.post('/dashboard/emergency-stop', {
      reason,
      close_positions: closePositions,
    });
    return data;
  },

  deactivateEmergencyStop: async (authorizedBy: string) => {
    const { data } = await api.post('/dashboard/emergency-stop/deactivate', {
      authorized_by: authorizedBy,
    });
    return data;
  },

  getEmergencyStopStatus: async () => {
    const { data } = await api.get('/dashboard/emergency-stop/status');
    return data;
  },

  healthCheck: async () => {
    const { data } = await api.get('/dashboard/health');
    return data;
  },

  getWeeklyOverview: async () => {
    const { data } = await api.get('/dashboard/overview');
    return data;
  },

  getPaperTradeStats: async () => {
    const { data } = await api.get('/dashboard/paper-trades/stats');
    return data;
  },

  getPerformanceReport: async (days: number = 30) => {
    const { data } = await api.get('/dashboard/reports/performance', {
      params: { days },
    });
    return data;
  },

  getCurrentPrice: async (symbol: string = 'US30') => {
    const { data } = await api.get(`/mt5/price/${symbol}`);
    return data;
  },
};

// Legacy API exports for backward compatibility
export const botApi = {
  getStatus: dashboardApi.getStatus,
  setMode: async (mode: 'analyze' | 'trade' | 'swing') => {
    return dashboardApi.switchMode(mode);
  },
  setSafeMode: async (enabled: boolean) => {
    if (enabled) {
      return dashboardApi.activateEmergencyStop('User activated safe mode', false);
    } else {
      return dashboardApi.deactivateEmergencyStop('User');
    }
  },
};

export const signalsApi = {
  getSignals: () => dashboardApi.getSignals(20),
  getSignal: async (id: string) => {
    // Get all signals and filter by ID
    const signals = await dashboardApi.getSignals(100);
    return signals.find((s: any) => s.id === id);
  },
};

export const tradesApi = {
  getOpenTrades: () => dashboardApi.getTrades(20, 'open'),
  getTradeHistory: () => dashboardApi.getTrades(50),
  closeTrade: async (id: string) => {
    // Individual trade close not implemented in dashboard API
    // Would need to be added to backend
    throw new Error('Individual trade close not implemented');
  },
  closeAllTrades: dashboardApi.closeAll,
};

export const swingApi = {
  getPending: async () => {
    // Swing approvals would need to be added to dashboard API
    return [];
  },
  approve: async (id: string) => {
    throw new Error('Swing approval not implemented');
  },
  reject: async (id: string) => {
    throw new Error('Swing rejection not implemented');
  },
};

export const reportsApi = {
  getWeeklyOverview: dashboardApi.getWeeklyOverview,
};

// Dual-Engine API - connects to /dual-engine/* endpoints
export const dualEngineApi = {
  getStatus: async () => {
    const { data } = await api.get('/dual-engine/status');
    return data;
  },

  getMarketRegime: async (instrument: string) => {
    const { data } = await api.get(`/dual-engine/regime/${instrument}`);
    return data;
  },

  getEnginePerformance: async (engine: string) => {
    const { data } = await api.get(`/dual-engine/performance/${engine}`);
    return data;
  },

  compareEnginePerformance: async (instrument?: string) => {
    const params = instrument ? { instrument } : {};
    const { data } = await api.get('/dual-engine/performance/compare', { params });
    return data;
  },

  getActiveSignals: async () => {
    const { data } = await api.get('/dual-engine/signals/active');
    return data;
  },

  getSignalHistory: async (engine?: string, instrument?: string, limit: number = 50) => {
    const params: any = { limit };
    if (engine) params.engine = engine;
    if (instrument) params.instrument = instrument;
    const { data } = await api.get('/dual-engine/signals/history', { params });
    return data;
  },

  getRecentDecisions: async (limit: number = 20) => {
    const { data } = await api.get('/dual-engine/decisions/recent', {
      params: { limit },
    });
    return data;
  },

  getConfig: async () => {
    const { data } = await api.get('/dual-engine/config');
    return data;
  },

  updateConfig: async (configUpdates: any) => {
    const { data } = await api.post('/dual-engine/config/update', configUpdates);
    return data;
  },

  healthCheck: async () => {
    const { data } = await api.get('/dual-engine/health');
    return data;
  },

  // Engine control methods
  toggleCoreStrategy: async (enabled: boolean) => {
    const { data } = await api.post(`/dual-engine/engines/core/toggle?enabled=${enabled}`);
    return data;
  },

  toggleQuickScalp: async (enabled: boolean) => {
    const { data } = await api.post(`/dual-engine/engines/scalp/toggle?enabled=${enabled}`);
    return data;
  },

  getEngineSettings: async () => {
    const { data } = await api.get('/dual-engine/engines/settings');
    return data;
  },

  // Market control methods
  toggleMarket: async (instrument: string, enabled: boolean) => {
    const { data } = await api.post(`/dual-engine/markets/${instrument}/toggle?enabled=${enabled}`);
    return data;
  },

  getAllMarketsStatus: async () => {
    const { data } = await api.get('/dual-engine/markets/status');
    return data;
  },
};

// MT5 Connection API - connects to /mt5/* endpoints
export const mt5Api = {
  getStatus: async () => {
    const { data } = await api.get('/mt5/status');
    return data;
  },

  connect: async () => {
    const { data } = await api.post('/mt5/connect');
    return data;
  },

  disconnect: async () => {
    const { data } = await api.post('/mt5/disconnect');
    return data;
  },

  testConnection: async (testConfig?: any) => {
    const { data } = await api.post('/mt5/test', testConfig || {
      test_account_info: true,
      test_market_data: true,
      test_positions: true,
    });
    return data;
  },

  getAccountInfo: async () => {
    const { data } = await api.get('/mt5/account');
    return data;
  },

  getCurrentPrice: async (instrument: string) => {
    const { data } = await api.get(`/mt5/price/${instrument}`);
    return data;
  },

  getCurrentSpread: async (instrument: string) => {
    const { data } = await api.get(`/mt5/spread/${instrument}`);
    return data;
  },

  getPositions: async () => {
    const { data } = await api.get('/mt5/positions');
    return data;
  },

  healthCheck: async () => {
    const { data } = await api.get('/mt5/health');
    return data;
  },
};

// Trading Loop API - connects to /trading-loop/* endpoints
export const tradingLoopApi = {
  getStatus: async () => {
    const { data } = await api.get('/trading-loop/status');
    return data;
  },

  start: async () => {
    const { data } = await api.post('/trading-loop/start');
    return data;
  },

  stop: async () => {
    const { data } = await api.post('/trading-loop/stop');
    return data;
  },

  updateSettings: async (settings: {
    core_strategy_enabled?: boolean;
    quick_scalp_enabled?: boolean;
    us30_enabled?: boolean;
    nas100_enabled?: boolean;
    xauusd_enabled?: boolean;
  }) => {
    const { data } = await api.post('/trading-loop/settings', settings);
    return data;
  },

  healthCheck: async () => {
    const { data } = await api.get('/trading-loop/health');
    return data;
  },
};

// WebSocket connection for trading loop updates
export const createTradingLoopWebSocket = (
  onMessage: (message: any) => void,
  onError?: (error: any) => void,
  onClose?: () => void
) => {
  const wsUrl = API_BASE_URL.replace('http', 'ws') + '/trading-loop/ws';
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('Trading Loop WebSocket connected');
  };

  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      console.log('Trading Loop WebSocket message:', message.type);
      onMessage(message);
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  };

  ws.onerror = (error) => {
    console.error('Trading Loop WebSocket error:', error);
    if (onError) onError(error);
  };

  ws.onclose = () => {
    console.log('Trading Loop WebSocket disconnected');
    if (onClose) onClose();
  };

  return ws;
};

export default api;
