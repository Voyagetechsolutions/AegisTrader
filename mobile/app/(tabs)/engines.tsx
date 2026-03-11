import React, { useState, useEffect, useRef } from 'react';
import {
    View,
    Text,
    StyleSheet,
    ScrollView,
    RefreshControl,
    ActivityIndicator,
    Switch,
    Alert,
    TouchableOpacity,
} from 'react-native';
import { dualEngineApi, mt5Api, tradingLoopApi, createTradingLoopWebSocket } from '../../services/api';
import { DualEngineStatus, UnifiedSignal } from '../../types';
import { Colors } from '../../constants/theme';

export default function EnginesScreen() {
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [status, setStatus] = useState<DualEngineStatus | null>(null);
    const [activeSignals, setActiveSignals] = useState<UnifiedSignal[]>([]);
    const [error, setError] = useState<string | null>(null);

    // Engine control states
    const [coreEnabled, setCoreEnabled] = useState(true);
    const [scalpEnabled, setScalpEnabled] = useState(true);
    const [marketEnabled, setMarketEnabled] = useState({
        US30: true,
        NAS100: true,
        XAUUSD: true,
    });

    // MT5 connection state
    const [mt5Connected, setMt5Connected] = useState(false);
    const [mt5Status, setMt5Status] = useState<string>('disconnected');
    const [accountBalance, setAccountBalance] = useState<number>(0);

    // Trading loop state
    const [loopRunning, setLoopRunning] = useState(false);
    const [loopStats, setLoopStats] = useState({
        loop_count: 0,
        signals_generated: 0,
        trades_executed: 0,
        last_run: null as string | null,
    });
    const [wsConnected, setWsConnected] = useState(false);
    const [realtimeSignals, setRealtimeSignals] = useState<any[]>([]);
    const wsRef = useRef<WebSocket | null>(null);

    const fetchData = async () => {
        try {
            setError(null);
            const [statusData, signalsData, settingsData, mt5StatusData, accountData, loopStatusData] = await Promise.all([
                dualEngineApi.getStatus(),
                dualEngineApi.getActiveSignals(),
                dualEngineApi.getEngineSettings(),
                mt5Api.getStatus().catch(() => ({ connected: false, status: 'error' })),
                mt5Api.getAccountInfo().catch(() => ({ balance: 0 })),
                tradingLoopApi.getStatus().catch(() => ({ running: false, loop_count: 0, signals_generated: 0, trades_executed: 0, last_run: null })),
            ]);
            setStatus(statusData);
            setActiveSignals(signalsData);

            // Update control states from settings
            setCoreEnabled(settingsData.engines.core_strategy);
            setScalpEnabled(settingsData.engines.quick_scalp);
            setMarketEnabled({
                US30: settingsData.markets.US30,
                NAS100: settingsData.markets.NAS100,
                XAUUSD: settingsData.markets.XAUUSD,
            });

            // Update MT5 status
            setMt5Connected(mt5StatusData.connected);
            setMt5Status(mt5StatusData.status);
            setAccountBalance(accountData.balance);

            // Update trading loop status
            setLoopRunning(loopStatusData.running);
            setLoopStats({
                loop_count: loopStatusData.loop_count,
                signals_generated: loopStatusData.signals_generated,
                trades_executed: loopStatusData.trades_executed,
                last_run: loopStatusData.last_run,
            });
        } catch (err: any) {
            setError(err.message || 'Failed to fetch dual-engine data');
            console.error('Dual-engine fetch error:', err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const connectWebSocket = () => {
        if (wsRef.current) {
            wsRef.current.close();
        }

        wsRef.current = createTradingLoopWebSocket(
            (message) => {
                console.log('WebSocket message:', message);

                switch (message.type) {
                    case 'connected':
                        setWsConnected(true);
                        break;

                    case 'signal_generated':
                        setRealtimeSignals(prev => [message.signal, ...prev].slice(0, 10));
                        Alert.alert(
                            '✨ New Signal',
                            `${message.signal.engine} - ${message.signal.instrument} ${message.signal.direction}`,
                            [{ text: 'OK' }]
                        );
                        break;

                    case 'trade_executed':
                        Alert.alert(
                            '✅ Trade Executed',
                            `${message.instrument} ${message.direction} @ ${message.entry_price}`,
                            [{ text: 'OK' }]
                        );
                        break;

                    case 'trade_failed':
                        Alert.alert(
                            '❌ Trade Failed',
                            message.error,
                            [{ text: 'OK' }]
                        );
                        break;

                    case 'loop_completed':
                        setLoopStats({
                            loop_count: message.iteration,
                            signals_generated: message.signals_generated,
                            trades_executed: message.trades_executed,
                            last_run: message.timestamp,
                        });
                        break;

                    case 'news_blackout':
                        Alert.alert(
                            '⚠️ News Blackout',
                            `${message.reason}\nClears in ${message.minutes_until_clear} minutes`,
                            [{ text: 'OK' }]
                        );
                        break;
                }
            },
            (error) => {
                console.error('WebSocket error:', error);
                setWsConnected(false);
            },
            () => {
                setWsConnected(false);
                // Auto-reconnect after 5 seconds
                setTimeout(() => {
                    if (loopRunning) {
                        connectWebSocket();
                    }
                }, 5000);
            }
        );
    };

    const disconnectWebSocket = () => {
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        setWsConnected(false);
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 30000); // Refresh every 30s
        return () => {
            clearInterval(interval);
            disconnectWebSocket();
        };
    }, []);

    useEffect(() => {
        if (loopRunning && !wsConnected) {
            connectWebSocket();
        } else if (!loopRunning && wsConnected) {
            disconnectWebSocket();
        }
    }, [loopRunning]);

    const onRefresh = () => {
        setRefreshing(true);
        fetchData();
    };

    const handleToggleCoreStrategy = async (value: boolean) => {
        try {
            await dualEngineApi.toggleCoreStrategy(value);
            setCoreEnabled(value);
            Alert.alert(
                'Core Strategy',
                `Core Strategy ${value ? 'enabled' : 'disabled'}`
            );
        } catch (err: any) {
            Alert.alert('Error', `Failed to toggle Core Strategy: ${err.message}`);
            setCoreEnabled(!value); // Revert on error
        }
    };

    const handleToggleQuickScalp = async (value: boolean) => {
        try {
            await dualEngineApi.toggleQuickScalp(value);
            setScalpEnabled(value);
            Alert.alert(
                'Quick Scalp',
                `Quick Scalp ${value ? 'enabled' : 'disabled'}`
            );
        } catch (err: any) {
            Alert.alert('Error', `Failed to toggle Quick Scalp: ${err.message}`);
            setScalpEnabled(!value); // Revert on error
        }
    };

    const handleToggleMarket = async (market: string, value: boolean) => {
        try {
            await dualEngineApi.toggleMarket(market, value);
            setMarketEnabled(prev => ({ ...prev, [market]: value }));
            Alert.alert(
                market,
                `${market} ${value ? 'enabled' : 'disabled'}`
            );
        } catch (err: any) {
            Alert.alert('Error', `Failed to toggle ${market}: ${err.message}`);
            setMarketEnabled(prev => ({ ...prev, [market]: !value })); // Revert on error
        }
    };

    const handleStartTradingLoop = async () => {
        try {
            const result = await tradingLoopApi.start();
            if (result.ok) {
                setLoopRunning(true);
                Alert.alert('🚀 Trading Loop Started', 'Live market analysis and signal generation active');
            } else {
                Alert.alert('Error', result.message);
            }
        } catch (err: any) {
            Alert.alert('Error', `Failed to start trading loop: ${err.message}`);
        }
    };

    const handleStopTradingLoop = async () => {
        Alert.alert(
            'Stop Trading Loop?',
            'This will stop live market analysis and signal generation.',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Stop',
                    style: 'destructive',
                    onPress: async () => {
                        try {
                            const result = await tradingLoopApi.stop();
                            if (result.ok) {
                                setLoopRunning(false);
                                Alert.alert('Trading Loop Stopped', 'Market analysis paused');
                            } else {
                                Alert.alert('Error', result.message);
                            }
                        } catch (err: any) {
                            Alert.alert('Error', `Failed to stop trading loop: ${err.message}`);
                        }
                    },
                },
            ]
        );
    };

    const getVolatilityColor = (volatility: string) => {
        switch (volatility) {
            case 'LOW': return Colors.textSecondary;
            case 'NORMAL': return Colors.success;
            case 'HIGH': return Colors.warning;
            case 'EXTREME': return Colors.danger;
            default: return Colors.textSecondary;
        }
    };

    const getTrendColor = (trend: string) => {
        switch (trend) {
            case 'STRONG_TREND': return Colors.success;
            case 'WEAK_TREND': return Colors.info;
            case 'RANGING': return Colors.warning;
            case 'CHOPPY': return Colors.danger;
            default: return Colors.textSecondary;
        }
    };

    if (loading) {
        return (
            <View style={styles.centerContainer}>
                <ActivityIndicator size="large" color={Colors.info} />
                <Text style={styles.loadingText}>Loading dual-engine system...</Text>
            </View>
        );
    }

    if (error) {
        return (
            <View style={styles.centerContainer}>
                <Text style={styles.errorText}>Error: {error}</Text>
                <Text style={styles.retryText} onPress={fetchData}>
                    Tap to retry
                </Text>
            </View>
        );
    }

    if (!status) {
        return (
            <View style={styles.centerContainer}>
                <Text style={styles.errorText}>No data available</Text>
            </View>
        );
    }

    return (
        <ScrollView
            style={styles.container}
            refreshControl={
                <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
            }
        >
            {/* Header */}
            <View style={styles.header}>
                <Text style={styles.headerTitle}>Dual-Engine System</Text>
                <Text style={styles.headerSubtitle}>Core Strategy + Quick Scalp</Text>
            </View>

            {/* Trading Loop Control */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Trading Loop</Text>
                <View style={[styles.loopCard, loopRunning ? styles.loopRunning : styles.loopStopped]}>
                    <View style={styles.loopHeader}>
                        <View style={styles.loopStatusRow}>
                            <View style={[styles.statusDot, loopRunning ? styles.statusDotGreen : styles.statusDotRed]} />
                            <Text style={styles.loopStatusText}>
                                {loopRunning ? 'Running' : 'Stopped'}
                            </Text>
                            {wsConnected && (
                                <View style={styles.wsIndicator}>
                                    <Text style={styles.wsIndicatorText}>🔴 LIVE</Text>
                                </View>
                            )}
                        </View>
                        <TouchableOpacity
                            style={[styles.loopButton, loopRunning ? styles.stopButton : styles.startButton]}
                            onPress={loopRunning ? handleStopTradingLoop : handleStartTradingLoop}
                        >
                            <Text style={styles.loopButtonText}>
                                {loopRunning ? 'STOP' : 'START'}
                            </Text>
                        </TouchableOpacity>
                    </View>
                    <View style={styles.loopStats}>
                        <View style={styles.loopStat}>
                            <Text style={styles.loopStatLabel}>Iterations</Text>
                            <Text style={styles.loopStatValue}>{loopStats.loop_count}</Text>
                        </View>
                        <View style={styles.loopStat}>
                            <Text style={styles.loopStatLabel}>Signals</Text>
                            <Text style={styles.loopStatValue}>{loopStats.signals_generated}</Text>
                        </View>
                        <View style={styles.loopStat}>
                            <Text style={styles.loopStatLabel}>Trades</Text>
                            <Text style={styles.loopStatValue}>{loopStats.trades_executed}</Text>
                        </View>
                    </View>
                    {loopStats.last_run && (
                        <Text style={styles.loopLastRun}>
                            Last run: {new Date(loopStats.last_run).toLocaleTimeString()}
                        </Text>
                    )}
                </View>
            </View>

            {/* MT5 Connection Status */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>MT5 Connection</Text>
                <View style={[styles.mt5Card, mt5Connected ? styles.mt5Connected : styles.mt5Disconnected]}>
                    <View style={styles.mt5Header}>
                        <View style={styles.mt5StatusRow}>
                            <View style={[styles.statusDot, mt5Connected ? styles.statusDotGreen : styles.statusDotRed]} />
                            <Text style={styles.mt5StatusText}>
                                {mt5Connected ? 'Connected' : 'Disconnected'}
                            </Text>
                        </View>
                        {mt5Connected && (
                            <Text style={styles.mt5Balance}>
                                ${accountBalance.toFixed(2)}
                            </Text>
                        )}
                    </View>
                    <Text style={styles.mt5StatusDetail}>
                        Status: {mt5Status}
                    </Text>
                    {!mt5Connected && (
                        <Text style={styles.mt5Warning}>
                            Ensure MT5 terminal is running with AegisTradeBridge EA
                        </Text>
                    )}
                </View>
            </View>

            {/* Engine Controls */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Engine Controls</Text>

                <View style={styles.controlCard}>
                    <View style={styles.controlRow}>
                        <View style={styles.controlInfo}>
                            <Text style={styles.controlLabel}>🎯 Core Strategy</Text>
                            <Text style={styles.controlDescription}>
                                100-point confluence • 1-2 trades/day • 2:1 R:R
                            </Text>
                        </View>
                        <Switch
                            value={coreEnabled}
                            onValueChange={handleToggleCoreStrategy}
                            trackColor={{ false: '#444', true: Colors.info }}
                            thumbColor={coreEnabled ? '#FFFFFF' : '#888'}
                        />
                    </View>
                </View>

                <View style={styles.controlCard}>
                    <View style={styles.controlRow}>
                        <View style={styles.controlInfo}>
                            <Text style={styles.controlLabel}>⚡ Quick Scalp</Text>
                            <Text style={styles.controlDescription}>
                                M1 momentum • 5-15 trades/day • 1:1 R:R
                            </Text>
                        </View>
                        <Switch
                            value={scalpEnabled}
                            onValueChange={handleToggleQuickScalp}
                            trackColor={{ false: '#444', true: Colors.success }}
                            thumbColor={scalpEnabled ? '#FFFFFF' : '#888'}
                        />
                    </View>
                </View>
            </View>

            {/* Market Controls */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Active Markets</Text>

                {(['US30', 'NAS100', 'XAUUSD'] as const).map(market => (
                    <View key={market} style={styles.controlCard}>
                        <View style={styles.controlRow}>
                            <View style={styles.controlInfo}>
                                <Text style={styles.controlLabel}>{market}</Text>
                                <Text style={styles.controlDescription}>
                                    {market === 'US30' && 'Dow Jones Industrial Average'}
                                    {market === 'NAS100' && 'NASDAQ 100 Index'}
                                    {market === 'XAUUSD' && 'Gold vs US Dollar'}
                                </Text>
                            </View>
                            <Switch
                                value={marketEnabled[market]}
                                onValueChange={(val) => handleToggleMarket(market, val)}
                                trackColor={{ false: '#444', true: Colors.info }}
                                thumbColor={marketEnabled[market] ? '#FFFFFF' : '#888'}
                            />
                        </View>
                    </View>
                ))}
            </View>

            {/* Engine Status Cards */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Engine Status</Text>

                {/* Core Strategy */}
                <View style={[styles.engineCard, styles.coreCard]}>
                    <View style={styles.engineHeader}>
                        <Text style={styles.engineName}>🎯 Core Strategy</Text>
                        <View style={[
                            styles.statusBadge,
                            status.core_strategy.can_trade ? styles.statusActive : styles.statusBlocked
                        ]}>
                            <Text style={styles.statusBadgeText}>
                                {status.core_strategy.can_trade ? 'ACTIVE' : 'BLOCKED'}
                            </Text>
                        </View>
                    </View>
                    <View style={styles.engineStats}>
                        <Text style={styles.statText}>
                            Trades Today: {status.core_strategy.trades_today} / {status.core_strategy.daily_limit}
                        </Text>
                        {status.core_strategy.block_reason && (
                            <Text style={styles.blockReason}>{status.core_strategy.block_reason}</Text>
                        )}
                    </View>
                </View>

                {/* Quick Scalp */}
                <View style={[styles.engineCard, styles.scalpCard]}>
                    <View style={styles.engineHeader}>
                        <Text style={styles.engineName}>⚡ Quick Scalp</Text>
                        <View style={[
                            styles.statusBadge,
                            status.quick_scalp.can_trade ? styles.statusActive : styles.statusBlocked
                        ]}>
                            <Text style={styles.statusBadgeText}>
                                {status.quick_scalp.can_trade ? 'ACTIVE' : 'BLOCKED'}
                            </Text>
                        </View>
                    </View>
                    <View style={styles.engineStats}>
                        <Text style={styles.statText}>
                            Trades Today: {status.quick_scalp.trades_today} / {status.quick_scalp.daily_limit}
                        </Text>
                        {status.quick_scalp.block_reason && (
                            <Text style={styles.blockReason}>{status.quick_scalp.block_reason}</Text>
                        )}
                    </View>
                </View>
            </View>

            {/* Market Regimes */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Market Regimes</Text>
                {status.market_regimes.map((regime) => (
                    <View key={regime.instrument} style={styles.regimeCard}>
                        <Text style={styles.regimeInstrument}>{regime.instrument}</Text>
                        <View style={styles.regimeRow}>
                            <View style={styles.regimeItem}>
                                <Text style={styles.regimeLabel}>Volatility</Text>
                                <View style={[
                                    styles.regimeBadge,
                                    { backgroundColor: getVolatilityColor(regime.volatility) }
                                ]}>
                                    <Text style={styles.regimeBadgeText}>{regime.volatility}</Text>
                                </View>
                            </View>
                            <View style={styles.regimeItem}>
                                <Text style={styles.regimeLabel}>Trend</Text>
                                <View style={[
                                    styles.regimeBadge,
                                    { backgroundColor: getTrendColor(regime.trend) }
                                ]}>
                                    <Text style={styles.regimeBadgeText}>{regime.trend}</Text>
                                </View>
                            </View>
                        </View>
                        <View style={styles.regimeMetrics}>
                            <Text style={styles.regimeMetric}>
                                ATR: {regime.atr_current.toFixed(2)} (avg: {regime.atr_average.toFixed(2)})
                            </Text>
                            <Text style={styles.regimeMetric}>
                                Ratio: {regime.atr_ratio.toFixed(2)}x
                            </Text>
                        </View>
                    </View>
                ))}
            </View>

            {/* Real-time Signals */}
            {realtimeSignals.length > 0 && (
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>
                        🔴 Real-time Signals ({realtimeSignals.length})
                    </Text>
                    {realtimeSignals.map((signal, index) => (
                        <View key={index} style={[styles.signalCard, styles.realtimeSignalCard]}>
                            <View style={styles.signalHeader}>
                                <Text style={styles.signalEngine}>
                                    {signal.engine === 'CORE_STRATEGY' ? '🎯 Core' : '⚡ Scalp'}
                                </Text>
                                <Text style={styles.signalInstrument}>{signal.instrument}</Text>
                                <View style={[
                                    styles.directionBadge,
                                    signal.direction === 'LONG' ? styles.longBadge : styles.shortBadge
                                ]}>
                                    <Text style={styles.directionText}>{signal.direction}</Text>
                                </View>
                            </View>
                            <View style={styles.signalDetails}>
                                <Text style={styles.signalDetail}>Entry: {signal.entry_price?.toFixed(2)}</Text>
                                <Text style={styles.signalDetail}>SL: {signal.stop_loss?.toFixed(2)}</Text>
                                <Text style={styles.signalDetail}>TP1: {signal.tp1?.toFixed(2)}</Text>
                            </View>
                            <Text style={styles.signalRR}>
                                R:R {signal.risk_reward_ratio?.toFixed(2)}
                            </Text>
                        </View>
                    ))}
                </View>
            )}

            {/* Active Signals */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>
                    Active Signals ({activeSignals.length})
                </Text>
                {activeSignals.length === 0 ? (
                    <View style={styles.emptyState}>
                        <Text style={styles.emptyStateText}>No active signals</Text>
                    </View>
                ) : (
                    activeSignals.map((signal) => (
                        <View key={signal.signal_id} style={styles.signalCard}>
                            <View style={styles.signalHeader}>
                                <Text style={styles.signalEngine}>
                                    {signal.engine === 'CORE_STRATEGY' ? '🎯 Core' : '⚡ Scalp'}
                                </Text>
                                <Text style={styles.signalInstrument}>{signal.instrument}</Text>
                                <View style={[
                                    styles.directionBadge,
                                    signal.direction === 'LONG' ? styles.longBadge : styles.shortBadge
                                ]}>
                                    <Text style={styles.directionText}>{signal.direction}</Text>
                                </View>
                            </View>
                            <View style={styles.signalDetails}>
                                <Text style={styles.signalDetail}>Entry: {signal.entry_price.toFixed(2)}</Text>
                                <Text style={styles.signalDetail}>SL: {signal.stop_loss.toFixed(2)}</Text>
                                <Text style={styles.signalDetail}>TP1: {signal.tp1.toFixed(2)}</Text>
                                {signal.tp2 && (
                                    <Text style={styles.signalDetail}>TP2: {signal.tp2.toFixed(2)}</Text>
                                )}
                            </View>
                            <Text style={styles.signalRR}>
                                R:R {signal.risk_reward_ratio.toFixed(2)}
                            </Text>
                        </View>
                    ))
                )}
            </View>

            {/* Last Decision */}
            {status.last_decision && (
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Last Decision</Text>
                    <View style={styles.decisionCard}>
                        <Text style={styles.decisionText}>{status.last_decision}</Text>
                    </View>
                </View>
            )}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: Colors.background,
    },
    centerContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: Colors.background,
        padding: 20,
    },
    loadingText: {
        marginTop: 16,
        fontSize: 16,
        color: Colors.textSecondary,
    },
    errorText: {
        fontSize: 16,
        color: Colors.danger,
        textAlign: 'center',
        marginBottom: 16,
    },
    retryText: {
        fontSize: 16,
        color: Colors.info,
        textDecorationLine: 'underline',
    },
    header: {
        backgroundColor: Colors.card,
        padding: 20,
        borderBottomWidth: 1,
        borderBottomColor: Colors.border,
    },
    headerTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: Colors.text,
    },
    headerSubtitle: {
        fontSize: 14,
        color: Colors.textSecondary,
        marginTop: 4,
    },
    section: {
        marginTop: 16,
        paddingHorizontal: 16,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: Colors.text,
        marginBottom: 12,
    },
    engineCard: {
        backgroundColor: Colors.card,
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
        borderLeftWidth: 4,
    },
    coreCard: {
        borderLeftColor: Colors.info,
    },
    scalpCard: {
        borderLeftColor: Colors.success,
    },
    engineHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    engineName: {
        fontSize: 18,
        fontWeight: '600',
        color: Colors.text,
    },
    statusBadge: {
        paddingHorizontal: 12,
        paddingVertical: 4,
        borderRadius: 12,
    },
    statusActive: {
        backgroundColor: Colors.success + '30',
    },
    statusBlocked: {
        backgroundColor: Colors.danger + '30',
    },
    statusBadgeText: {
        fontSize: 12,
        fontWeight: '600',
        color: Colors.text,
    },
    engineStats: {
        gap: 8,
    },
    statText: {
        fontSize: 14,
        color: Colors.textSecondary,
    },
    blockReason: {
        fontSize: 12,
        color: Colors.danger,
        fontStyle: 'italic',
    },
    regimeCard: {
        backgroundColor: Colors.card,
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
    },
    regimeInstrument: {
        fontSize: 16,
        fontWeight: '600',
        color: Colors.text,
        marginBottom: 12,
    },
    regimeRow: {
        flexDirection: 'row',
        gap: 16,
        marginBottom: 12,
    },
    regimeItem: {
        flex: 1,
    },
    regimeLabel: {
        fontSize: 12,
        color: Colors.textSecondary,
        marginBottom: 4,
    },
    regimeBadge: {
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 8,
        alignItems: 'center',
    },
    regimeBadgeText: {
        fontSize: 12,
        fontWeight: '600',
        color: '#FFFFFF',
    },
    regimeMetrics: {
        flexDirection: 'row',
        justifyContent: 'space-between',
    },
    regimeMetric: {
        fontSize: 12,
        color: Colors.textSecondary,
    },
    emptyState: {
        backgroundColor: Colors.card,
        borderRadius: 12,
        padding: 32,
        alignItems: 'center',
    },
    emptyStateText: {
        fontSize: 14,
        color: Colors.textSecondary,
    },
    signalCard: {
        backgroundColor: Colors.card,
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
    },
    signalHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        marginBottom: 12,
    },
    signalEngine: {
        fontSize: 14,
        fontWeight: '600',
        color: Colors.textSecondary,
    },
    signalInstrument: {
        fontSize: 16,
        fontWeight: '600',
        color: Colors.text,
    },
    directionBadge: {
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 6,
    },
    longBadge: {
        backgroundColor: Colors.success + '30',
    },
    shortBadge: {
        backgroundColor: Colors.danger + '30',
    },
    directionText: {
        fontSize: 12,
        fontWeight: '600',
        color: Colors.text,
    },
    signalDetails: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 12,
        marginBottom: 8,
    },
    signalDetail: {
        fontSize: 14,
        color: Colors.textSecondary,
    },
    signalRR: {
        fontSize: 14,
        fontWeight: '600',
        color: Colors.info,
    },
    decisionCard: {
        backgroundColor: Colors.card,
        borderRadius: 12,
        padding: 16,
    },
    decisionText: {
        fontSize: 14,
        color: Colors.text,
        lineHeight: 20,
    },
    controlCard: {
        backgroundColor: Colors.card,
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
    },
    controlRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    controlInfo: {
        flex: 1,
        marginRight: 16,
    },
    controlLabel: {
        fontSize: 16,
        fontWeight: '600',
        color: Colors.text,
        marginBottom: 4,
    },
    controlDescription: {
        fontSize: 12,
        color: Colors.textSecondary,
        lineHeight: 16,
    },
    mt5Card: {
        backgroundColor: Colors.card,
        borderRadius: 12,
        padding: 16,
        borderLeftWidth: 4,
    },
    mt5Connected: {
        borderLeftColor: Colors.success,
    },
    mt5Disconnected: {
        borderLeftColor: Colors.danger,
    },
    mt5Header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
    },
    mt5StatusRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    statusDot: {
        width: 10,
        height: 10,
        borderRadius: 5,
    },
    statusDotGreen: {
        backgroundColor: Colors.success,
    },
    statusDotRed: {
        backgroundColor: Colors.danger,
    },
    mt5StatusText: {
        fontSize: 16,
        fontWeight: '600',
        color: Colors.text,
    },
    mt5Balance: {
        fontSize: 18,
        fontWeight: 'bold',
        color: Colors.success,
    },
    mt5StatusDetail: {
        fontSize: 12,
        color: Colors.textSecondary,
        marginBottom: 4,
    },
    mt5Warning: {
        fontSize: 12,
        color: Colors.warning,
        fontStyle: 'italic',
        marginTop: 8,
    },
    loopCard: {
        backgroundColor: Colors.card,
        borderRadius: 12,
        padding: 16,
        borderLeftWidth: 4,
    },
    loopRunning: {
        borderLeftColor: Colors.success,
    },
    loopStopped: {
        borderLeftColor: Colors.textSecondary,
    },
    loopHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16,
    },
    loopStatusRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    loopStatusText: {
        fontSize: 16,
        fontWeight: '600',
        color: Colors.text,
    },
    wsIndicator: {
        backgroundColor: Colors.danger + '30',
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 8,
        marginLeft: 8,
    },
    wsIndicatorText: {
        fontSize: 10,
        fontWeight: 'bold',
        color: Colors.danger,
    },
    loopButton: {
        paddingHorizontal: 20,
        paddingVertical: 10,
        borderRadius: 8,
        minWidth: 80,
        alignItems: 'center',
    },
    startButton: {
        backgroundColor: Colors.success,
    },
    stopButton: {
        backgroundColor: Colors.danger,
    },
    loopButtonText: {
        fontSize: 14,
        fontWeight: 'bold',
        color: '#FFFFFF',
    },
    loopStats: {
        flexDirection: 'row',
        justifyContent: 'space-around',
        marginBottom: 12,
    },
    loopStat: {
        alignItems: 'center',
    },
    loopStatLabel: {
        fontSize: 12,
        color: Colors.textSecondary,
        marginBottom: 4,
    },
    loopStatValue: {
        fontSize: 20,
        fontWeight: 'bold',
        color: Colors.text,
    },
    loopLastRun: {
        fontSize: 12,
        color: Colors.textSecondary,
        textAlign: 'center',
    },
    realtimeSignalCard: {
        borderLeftWidth: 3,
        borderLeftColor: Colors.danger,
    },
});
