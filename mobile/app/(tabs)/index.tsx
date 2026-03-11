import { View, Text, StyleSheet, ScrollView, TouchableOpacity, RefreshControl, Alert } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '../../services/api';
import { Colors, Spacing, FontSizes } from '../../constants/theme';
import { DashboardStatus } from '../../types';
import { useState } from 'react';

export default function Dashboard() {
  const [refreshing, setRefreshing] = useState(false);
  const [selectedPair, setSelectedPair] = useState('US30');

  const { data: status, isLoading, refetch } = useQuery<DashboardStatus>({
    queryKey: ['dashboardStatus'],
    queryFn: dashboardApi.getStatus,
    refetchInterval: 3000, // Update every 3 seconds
    retry: 1,
  });

  const { data: priceData } = useQuery({
    queryKey: ['currentPrice', selectedPair],
    queryFn: () => dashboardApi.getCurrentPrice(selectedPair),
    refetchInterval: 2000, // Update price every 2 seconds
    retry: 1,
    enabled: !!selectedPair,
  });

  const getCurrentPrice = () => {
    if (!priceData) return '—';
    // Format price with commas
    return priceData.bid.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  const handleModeSwitch = async (mode: string) => {
    try {
      await dashboardApi.switchMode(mode);
      await refetch();
      Alert.alert('Success', `Switched to ${mode} mode`);
    } catch (error) {
      Alert.alert('Error', 'Failed to switch mode');
    }
  };

  const handleToggleAutoTrade = async () => {
    try {
      await dashboardApi.updateSettings({
        auto_trade_enabled: !status?.auto_trade_enabled,
      });
      await refetch();
    } catch (error) {
      Alert.alert('Error', 'Failed to toggle auto trading');
    }
  };

  const handleCloseAll = () => {
    Alert.alert(
      'Close All Positions',
      'Are you sure you want to close all open positions?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Close All',
          style: 'destructive',
          onPress: async () => {
            try {
              await dashboardApi.closeAll();
              await refetch();
              Alert.alert('Success', 'All positions closed');
            } catch (error) {
              Alert.alert('Error', 'Failed to close positions');
            }
          },
        },
      ]
    );
  };

  const handleEmergencyStop = () => {
    Alert.alert(
      '🚨 Emergency Stop',
      'This will immediately halt all trading. Continue?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'STOP',
          style: 'destructive',
          onPress: async () => {
            try {
              await dashboardApi.activateEmergencyStop('User activated from mobile', false);
              await refetch();
              Alert.alert('Emergency Stop Activated', 'All trading has been halted');
            } catch (error) {
              Alert.alert('Error', 'Failed to activate emergency stop');
            }
          },
        },
      ]
    );
  };

  if (isLoading) {
    return (
      <View style={styles.container}>
        <Text style={styles.loadingText}>Connecting to backend...</Text>
        <Text style={styles.infoText}>Make sure backend is running on port 8000</Text>
      </View>
    );
  }

  if (!status) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>Backend Offline</Text>
        <Text style={styles.infoText}>Start the backend server first</Text>
        <TouchableOpacity style={styles.retryButton} onPress={() => refetch()}>
          <Text style={styles.retryText}>Retry Connection</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const isConnected = status.connection_health.database && status.connection_health.mt5_node;

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.success} />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.title}>⚡ Aegis Trader</Text>
        </View>
        <View style={[styles.connectionDot, { backgroundColor: isConnected ? Colors.success : Colors.danger }]} />
      </View>

      {/* Pair Selector */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Trading Pair</Text>
        <View style={styles.pairGrid}>
          <TouchableOpacity
            style={[styles.pairBtn, selectedPair === 'US30' && styles.pairBtnActive]}
            onPress={() => setSelectedPair('US30')}
          >
            <Text style={[styles.pairText, selectedPair === 'US30' && styles.pairTextActive]}>US30</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.pairBtn, styles.pairBtnDisabled]} disabled>
            <Text style={styles.pairTextDisabled}>GOLD</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.pairBtn, styles.pairBtnDisabled]} disabled>
            <Text style={styles.pairTextDisabled}>NASDAQ</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Account Info */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Account Info</Text>
        <View style={styles.accountGrid}>
          <View style={styles.accountItem}>
            <Text style={styles.accountLabel}>Balance</Text>
            <Text style={styles.accountValue}>${status?.account_balance.toFixed(2) || '0.00'}</Text>
          </View>
          <View style={styles.accountItem}>
            <Text style={styles.accountLabel}>Current Price</Text>
            <Text style={styles.accountValue}>{getCurrentPrice()}</Text>
          </View>
        </View>
      </View>

      {/* Status Bar */}
      <View style={styles.statusBar}>
        <View style={styles.statusItem}>
          <Text style={styles.statusLabel}>Mode</Text>
          <Text style={styles.statusValue}>{status.mode || '—'}</Text>
        </View>
        <View style={styles.statusItem}>
          <Text style={styles.statusLabel}>Session</Text>
          <Text style={styles.statusValue}>{status.active_session || '—'}</Text>
        </View>
        <View style={styles.statusItem}>
          <Text style={styles.statusLabel}>Trades</Text>
          <Text style={styles.statusValue}>{status.trades_today}/2</Text>
        </View>
        <View style={styles.statusItem}>
          <Text style={styles.statusLabel}>DD</Text>
          <Text style={styles.statusValue}>{status.drawdown_today_pct.toFixed(2)}%</Text>
        </View>
      </View>

      {/* Quick Controls */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Quick Controls</Text>
        <View style={styles.modeGrid}>
          <TouchableOpacity style={styles.modeBtn} onPress={() => handleModeSwitch('analyze')}>
            <Text style={styles.modeIcon}>🔍</Text>
            <Text style={styles.modeText}>Analyze</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.modeBtn} onPress={() => handleModeSwitch('trade')}>
            <Text style={styles.modeIcon}>⚡</Text>
            <Text style={styles.modeText}>Trade</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.modeBtn} onPress={() => handleModeSwitch('swing')}>
            <Text style={styles.modeIcon}>📈</Text>
            <Text style={styles.modeText}>Swing</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.modeBtn, styles.modeBtnDanger]} onPress={handleCloseAll}>
            <Text style={styles.modeIcon}>🔒</Text>
            <Text style={styles.modeText}>Close All</Text>
          </TouchableOpacity>
        </View>
        <View style={styles.autoTradeRow}>
          <Text style={styles.autoLabel}>Auto Trading</Text>
          <TouchableOpacity
            style={[styles.toggle, status.auto_trade_enabled && styles.toggleActive]}
            onPress={handleToggleAutoTrade}
          >
            <View style={[styles.toggleThumb, status.auto_trade_enabled && styles.toggleThumbActive]} />
          </TouchableOpacity>
        </View>
      </View>

      {/* Risk Status */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Risk Status</Text>
        <View style={styles.riskGrid}>
          <View style={styles.riskItem}>
            <Text style={styles.riskValue}>{status.trades_today}/2</Text>
            <Text style={styles.riskLabel}>Trades Today</Text>
          </View>
          <View style={styles.riskItem}>
            <Text style={styles.riskValue}>{status.losses_today}/2</Text>
            <Text style={styles.riskLabel}>Losses Today</Text>
          </View>
          <View style={styles.riskItem}>
            <Text style={styles.riskValue}>{status.drawdown_today_pct.toFixed(2)}%</Text>
            <Text style={styles.riskLabel}>Drawdown</Text>
          </View>
          <View style={styles.riskItem}>
            <Text style={styles.riskValue}>{status.open_positions}</Text>
            <Text style={styles.riskLabel}>Open Positions</Text>
          </View>
        </View>
        <View style={styles.riskBarWrap}>
          <View style={styles.riskBarTrack}>
            <View
              style={[
                styles.riskBarFill,
                { width: `${Math.min((status.drawdown_today_pct / 2) * 100, 100)}%` },
              ]}
            />
          </View>
          <Text style={styles.riskBarLabel}>Drawdown Limit: 2%</Text>
        </View>
      </View>

      {/* System Health */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>System Health</Text>
        <View style={styles.healthRow}>
          <Text style={styles.healthLabel}>Database</Text>
          <View style={[styles.healthDot, { backgroundColor: status.connection_health.database ? Colors.success : Colors.danger }]} />
        </View>
        <View style={styles.healthRow}>
          <Text style={styles.healthLabel}>MT5 Node</Text>
          <View style={[styles.healthDot, { backgroundColor: status.connection_health.mt5_node ? Colors.success : Colors.danger }]} />
        </View>
        <View style={styles.healthRow}>
          <Text style={styles.healthLabel}>Telegram</Text>
          <View style={[styles.healthDot, { backgroundColor: status.connection_health.telegram ? Colors.success : Colors.danger }]} />
        </View>
      </View>

      {/* Emergency Stop */}
      <TouchableOpacity style={styles.emergencyButton} onPress={handleEmergencyStop}>
        <Text style={styles.emergencyText}>🚨 EMERGENCY STOP</Text>
      </TouchableOpacity>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
    padding: Spacing.md,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.md,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  title: {
    fontSize: FontSizes.xl,
    fontWeight: '700',
    color: Colors.text,
  },
  connectionDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  pairGrid: {
    flexDirection: 'row',
    gap: 12,
  },
  pairBtn: {
    flex: 1,
    backgroundColor: '#1e2433',
    paddingVertical: 16,
    paddingHorizontal: 12,
    borderRadius: 8,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#2a3142',
  },
  pairBtnActive: {
    backgroundColor: '#1a3a2a',
    borderColor: Colors.success,
  },
  pairBtnDisabled: {
    backgroundColor: '#1a1d26',
    borderColor: '#252830',
    opacity: 0.5,
  },
  pairText: {
    color: Colors.text,
    fontSize: FontSizes.md,
    fontWeight: '600',
  },
  pairTextActive: {
    color: Colors.success,
  },
  pairTextDisabled: {
    color: '#555',
    fontSize: FontSizes.md,
    fontWeight: '600',
  },
  accountGrid: {
    flexDirection: 'row',
    gap: 12,
  },
  accountItem: {
    flex: 1,
    backgroundColor: '#1e2433',
    padding: Spacing.md,
    borderRadius: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#2a3142',
  },
  accountLabel: {
    fontSize: FontSizes.xs,
    color: Colors.textSecondary,
    marginBottom: 8,
  },
  accountValue: {
    fontSize: FontSizes.xl,
    fontWeight: '700',
    color: Colors.success,
  },
  statusBar: {
    flexDirection: 'row',
    backgroundColor: Colors.card,
    paddingVertical: 12,
    paddingHorizontal: Spacing.md,
    borderRadius: 8,
    marginBottom: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  statusItem: {
    flex: 1,
    alignItems: 'center',
  },
  statusLabel: {
    fontSize: FontSizes.xs,
    color: Colors.textSecondary,
    marginBottom: 4,
  },
  statusValue: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
  },
  card: {
    backgroundColor: Colors.card,
    borderRadius: 8,
    padding: Spacing.lg,
    marginBottom: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  cardTitle: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
    marginBottom: Spacing.md,
  },
  modeGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: Spacing.md,
  },
  modeBtn: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: '#1e2433',
    padding: Spacing.md,
    borderRadius: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#2a3142',
  },
  modeBtnDanger: {
    backgroundColor: '#2a1a1a',
    borderColor: Colors.danger,
  },
  modeIcon: {
    fontSize: 24,
    marginBottom: 8,
  },
  modeText: {
    color: Colors.text,
    fontSize: FontSizes.sm,
    fontWeight: '500',
  },
  autoTradeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: Spacing.md,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  autoLabel: {
    color: Colors.text,
    fontSize: FontSizes.md,
    fontWeight: '500',
  },
  toggle: {
    width: 50,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#444',
    padding: 2,
    justifyContent: 'center',
  },
  toggleActive: {
    backgroundColor: Colors.success,
  },
  toggleThumb: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#fff',
  },
  toggleThumbActive: {
    alignSelf: 'flex-end',
  },
  riskGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: Spacing.md,
  },
  riskItem: {
    flex: 1,
    minWidth: '45%',
    alignItems: 'center',
  },
  riskValue: {
    fontSize: FontSizes.xl,
    fontWeight: '700',
    color: Colors.success,
    marginBottom: 4,
  },
  riskLabel: {
    fontSize: FontSizes.xs,
    color: Colors.textSecondary,
  },
  riskBarWrap: {
    marginTop: 8,
  },
  riskBarTrack: {
    height: 8,
    backgroundColor: '#1e2433',
    borderRadius: 4,
    overflow: 'hidden',
  },
  riskBarFill: {
    height: '100%',
    backgroundColor: Colors.success,
  },
  riskBarLabel: {
    fontSize: FontSizes.xs,
    color: Colors.textSecondary,
    marginTop: 8,
    textAlign: 'center',
  },
  healthRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  healthLabel: {
    fontSize: FontSizes.md,
    color: Colors.text,
  },
  healthDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  healthValue: {
    fontSize: FontSizes.md,
    color: Colors.text,
    fontWeight: '600',
  },
  emergencyButton: {
    backgroundColor: Colors.danger,
    padding: Spacing.lg,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: Spacing.md,
  },
  emergencyText: {
    color: Colors.text,
    fontSize: FontSizes.lg,
    fontWeight: 'bold',
  },
  loadingText: {
    color: Colors.text,
    fontSize: FontSizes.lg,
    textAlign: 'center',
    marginTop: Spacing.xl,
  },
  errorText: {
    color: Colors.danger,
    fontSize: FontSizes.xl,
    fontWeight: 'bold',
    textAlign: 'center',
    marginTop: Spacing.xl,
  },
  infoText: {
    color: Colors.textSecondary,
    fontSize: FontSizes.md,
    textAlign: 'center',
    marginTop: Spacing.md,
  },
  retryButton: {
    backgroundColor: Colors.success,
    padding: Spacing.lg,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: Spacing.xl,
    marginHorizontal: Spacing.xl,
  },
  retryText: {
    color: Colors.text,
    fontSize: FontSizes.lg,
    fontWeight: 'bold',
  },
});
