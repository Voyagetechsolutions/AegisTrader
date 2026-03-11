import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, RefreshControl, StatusBar } from 'react-native';
import axios from 'axios';

const API_URL = 'http://localhost:8000'; // Change to your backend URL

export default function App() {
  const [status, setStatus] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  const loadStatus = async () => {
    try {
      const response = await axios.get(`${API_URL}/dashboard/status`);
      setStatus(response.data);
    } catch (error) {
      console.error('Failed to load status:', error);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadStatus();
    setRefreshing(false);
  };

  const toggleAutoTrade = async () => {
    try {
      await axios.post(`${API_URL}/dashboard/auto-trade`, {
        enabled: !status?.auto_trade_enabled
      });
      await loadStatus();
    } catch (error) {
      console.error('Failed to toggle auto trade:', error);
    }
  };

  const setMode = async (mode) => {
    try {
      await axios.post(`${API_URL}/dashboard/mode`, { mode });
      await loadStatus();
    } catch (error) {
      console.error('Failed to set mode:', error);
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a0a" />
      
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>⚡ Aegis Trader</Text>
        <Text style={styles.headerSubtitle}>US30</Text>
      </View>

      {/* Status Bar */}
      <View style={styles.statusBar}>
        <View style={styles.statusItem}>
          <Text style={styles.statusLabel}>Mode</Text>
          <Text style={styles.statusValue}>{status?.mode?.toUpperCase() || '—'}</Text>
        </View>
        <View style={styles.statusItem}>
          <Text style={styles.statusLabel}>Session</Text>
          <Text style={styles.statusValue}>{status?.session || '—'}</Text>
        </View>
        <View style={styles.statusItem}>
          <Text style={styles.statusLabel}>Trades</Text>
          <Text style={styles.statusValue}>{status?.trades_today || 0}/2</Text>
        </View>
      </View>

      {/* Content */}
      <ScrollView
        style={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>
        
        {/* Quick Controls */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Quick Controls</Text>
          
          <View style={styles.modeGrid}>
            <TouchableOpacity
              style={[styles.modeBtn, status?.mode === 'analyze' && styles.modeBtnActive]}
              onPress={() => setMode('analyze')}>
              <Text style={styles.modeBtnText}>🔍</Text>
              <Text style={styles.modeBtnLabel}>Analyze</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={[styles.modeBtn, status?.mode === 'trade' && styles.modeBtnActive]}
              onPress={() => setMode('trade')}>
              <Text style={styles.modeBtnText}>⚡</Text>
              <Text style={styles.modeBtnLabel}>Trade</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={[styles.modeBtn, status?.mode === 'swing' && styles.modeBtnActive]}
              onPress={() => setMode('swing')}>
              <Text style={styles.modeBtnText}>📈</Text>
              <Text style={styles.modeBtnLabel}>Swing</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.toggleRow}>
            <Text style={styles.toggleLabel}>Auto Trading</Text>
            <TouchableOpacity
              style={[styles.toggle, status?.auto_trade_enabled && styles.toggleActive]}
              onPress={toggleAutoTrade}>
              <View style={[styles.toggleSlider, status?.auto_trade_enabled && styles.toggleSliderActive]} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Risk Status */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Risk Status</Text>
          <View style={styles.riskGrid}>
            <View style={styles.riskItem}>
              <Text style={styles.riskValue}>{status?.trades_today || 0}/2</Text>
              <Text style={styles.riskLabel}>Trades Today</Text>
            </View>
            <View style={styles.riskItem}>
              <Text style={styles.riskValue}>{status?.losses_today || 0}/2</Text>
              <Text style={styles.riskLabel}>Losses Today</Text>
            </View>
            <View style={styles.riskItem}>
              <Text style={styles.riskValue}>{status?.drawdown_pct?.toFixed(2) || '0.00'}%</Text>
              <Text style={styles.riskLabel}>Drawdown</Text>
            </View>
          </View>
        </View>

        {/* Balance */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Account</Text>
          <Text style={styles.balanceText}>${status?.balance?.toFixed(2) || '0.00'}</Text>
        </View>
      </ScrollView>

      {/* Tab Bar */}
      <View style={styles.tabBar}>
        <TouchableOpacity style={styles.tab} onPress={() => setActiveTab('overview')}>
          <Text style={[styles.tabIcon, activeTab === 'overview' && styles.tabActive]}>📊</Text>
          <Text style={[styles.tabLabel, activeTab === 'overview' && styles.tabActive]}>Overview</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.tab} onPress={() => setActiveTab('signals')}>
          <Text style={[styles.tabIcon, activeTab === 'signals' && styles.tabActive]}>📈</Text>
          <Text style={[styles.tabLabel, activeTab === 'signals' && styles.tabActive]}>Signals</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.tab} onPress={() => setActiveTab('trades')}>
          <Text style={[styles.tabIcon, activeTab === 'trades' && styles.tabActive]}>💰</Text>
          <Text style={[styles.tabLabel, activeTab === 'trades' && styles.tabActive]}>Trades</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.tab} onPress={() => setActiveTab('settings')}>
          <Text style={[styles.tabIcon, activeTab === 'settings' && styles.tabActive]}>⚙️</Text>
          <Text style={[styles.tabLabel, activeTab === 'settings' && styles.tabActive]}>Settings</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
  header: {
    backgroundColor: '#1a1a1a',
    padding: 16,
    paddingTop: 40,
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  headerTitle: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
  },
  headerSubtitle: {
    color: '#00d4aa',
    fontSize: 14,
    marginTop: 4,
  },
  statusBar: {
    flexDirection: 'row',
    backgroundColor: '#1a1a1a',
    padding: 16,
    justifyContent: 'space-around',
  },
  statusItem: {
    alignItems: 'center',
  },
  statusLabel: {
    color: '#666',
    fontSize: 12,
  },
  statusValue: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: 4,
  },
  content: {
    flex: 1,
  },
  card: {
    backgroundColor: '#1a1a1a',
    margin: 16,
    padding: 16,
    borderRadius: 12,
  },
  cardTitle: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  modeGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  modeBtn: {
    backgroundColor: '#333',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    flex: 1,
    marginHorizontal: 4,
  },
  modeBtnActive: {
    backgroundColor: '#00d4aa',
  },
  modeBtnText: {
    fontSize: 24,
  },
  modeBtnLabel: {
    color: '#fff',
    fontSize: 12,
    marginTop: 4,
  },
  toggleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  toggleLabel: {
    color: '#fff',
    fontSize: 16,
  },
  toggle: {
    width: 50,
    height: 30,
    backgroundColor: '#333',
    borderRadius: 15,
    padding: 2,
  },
  toggleActive: {
    backgroundColor: '#00d4aa',
  },
  toggleSlider: {
    width: 26,
    height: 26,
    backgroundColor: '#fff',
    borderRadius: 13,
  },
  toggleSliderActive: {
    marginLeft: 22,
  },
  riskGrid: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  riskItem: {
    alignItems: 'center',
  },
  riskValue: {
    color: '#00d4aa',
    fontSize: 20,
    fontWeight: 'bold',
  },
  riskLabel: {
    color: '#666',
    fontSize: 12,
    marginTop: 4,
  },
  balanceText: {
    color: '#00d4aa',
    fontSize: 32,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: '#1a1a1a',
    borderTopWidth: 1,
    borderTopColor: '#333',
    paddingBottom: 20,
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 8,
  },
  tabIcon: {
    fontSize: 24,
    color: '#666',
  },
  tabLabel: {
    fontSize: 10,
    color: '#666',
    marginTop: 4,
  },
  tabActive: {
    color: '#00d4aa',
  },
});