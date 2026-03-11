import { View, Text, StyleSheet, FlatList, TouchableOpacity, Alert } from 'react-native';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dashboardApi } from '../../services/api';
import { Colors, Spacing, FontSizes } from '../../constants/theme';
import { Trade } from '../../types';

export default function Trades() {
  const queryClient = useQueryClient();

  const { data: trades, isLoading } = useQuery<Trade[]>({
    queryKey: ['trades'],
    queryFn: () => dashboardApi.getTrades(50),
    refetchInterval: 5000,
  });

  const closeAllMutation = useMutation({
    mutationFn: dashboardApi.closeAll,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardStatus'] });
    },
  });

  const handleCloseAll = () => {
    Alert.alert(
      'Close All Trades',
      'Are you sure you want to close ALL open positions?',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Close All', style: 'destructive', onPress: () => closeAllMutation.mutate() },
      ]
    );
  };

  const renderTrade = ({ item }: { item: Trade }) => {
    const isOpen = item.status === 'open' || item.status === 'partial';

    return (
      <View style={styles.tradeCard}>
        <View style={styles.tradeHeader}>
          <View style={[styles.directionBadge, { backgroundColor: item.direction === 'long' ? Colors.long : Colors.short }]}>
            <Text style={styles.directionText}>{item.direction?.toUpperCase() || 'N/A'}</Text>
          </View>
          <Text style={styles.symbolText}>{item.symbol}</Text>
          <View style={[styles.statusBadge, { backgroundColor: isOpen ? Colors.success : Colors.textSecondary }]}>
            <Text style={styles.statusText}>{item.status?.toUpperCase()}</Text>
          </View>
        </View>

        <View style={styles.priceRow}>
          <View style={styles.priceItem}>
            <Text style={styles.priceLabel}>Entry</Text>
            <Text style={styles.priceValue}>{item.entry_price.toFixed(1)}</Text>
          </View>
          <View style={styles.priceItem}>
            <Text style={styles.priceLabel}>SL</Text>
            <Text style={styles.priceValue}>{item.stop_loss.toFixed(1)}</Text>
          </View>
          <View style={styles.priceItem}>
            <Text style={styles.priceLabel}>Lots</Text>
            <Text style={styles.priceValue}>{item.lot_size.toFixed(2)}</Text>
          </View>
        </View>

        {item.pnl !== null && (
          <Text style={[styles.pnlText, { color: item.pnl >= 0 ? Colors.success : Colors.danger }]}>
            P&L: ${item.pnl.toFixed(2)}
          </Text>
        )}

        {item.tp1_hit && <Text style={styles.badgeText}>✓ TP1 Hit</Text>}
        {item.breakeven_active && <Text style={styles.badgeText}>✓ BE Active</Text>}
        {item.runner_active && <Text style={styles.badgeText}>🏃 Runner Active</Text>}

        <Text style={styles.timeText}>
          {item.opened_at ? new Date(item.opened_at).toLocaleString() : 'N/A'}
        </Text>
      </View>
    );
  };

  if (isLoading) {
    return (
      <View style={styles.container}>
        <Text style={styles.loadingText}>Loading trades...</Text>
      </View>
    );
  }

  const openTrades = trades?.filter(t => t.status === 'open' || t.status === 'partial') || [];

  return (
    <View style={styles.container}>
      {openTrades.length > 0 && (
        <TouchableOpacity style={styles.closeAllButton} onPress={handleCloseAll}>
          <Text style={styles.closeAllText}>Close All Positions ({openTrades.length})</Text>
        </TouchableOpacity>
      )}

      <FlatList
        data={trades}
        renderItem={renderTrade}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <Text style={styles.emptyText}>No trades recorded</Text>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  list: {
    padding: Spacing.md,
  },
  closeAllButton: {
    backgroundColor: Colors.danger,
    margin: Spacing.md,
    padding: Spacing.md,
    borderRadius: 8,
    alignItems: 'center',
  },
  closeAllText: {
    color: Colors.text,
    fontWeight: 'bold',
    fontSize: FontSizes.md,
  },
  tradeCard: {
    backgroundColor: Colors.card,
    borderRadius: 8,
    padding: Spacing.lg,
    marginBottom: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  tradeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: Spacing.md,
  },
  directionBadge: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: 6,
    marginRight: Spacing.sm,
  },
  directionText: {
    color: Colors.text,
    fontWeight: 'bold',
    fontSize: FontSizes.sm,
  },
  symbolText: {
    color: Colors.text,
    fontSize: FontSizes.md,
    fontWeight: '600',
    flex: 1,
  },
  statusBadge: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 4,
    borderRadius: 4,
  },
  statusText: {
    color: Colors.text,
    fontSize: FontSizes.xs,
    fontWeight: '600',
  },
  pnlText: {
    fontSize: FontSizes.lg,
    fontWeight: 'bold',
    marginBottom: Spacing.sm,
  },
  priceRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: Spacing.md,
  },
  priceItem: {
    alignItems: 'center',
  },
  priceLabel: {
    fontSize: FontSizes.xs,
    color: Colors.textSecondary,
    marginBottom: Spacing.xs,
  },
  priceValue: {
    fontSize: FontSizes.md,
    color: Colors.text,
    fontWeight: '600',
  },
  badgeText: {
    color: Colors.success,
    fontSize: FontSizes.sm,
    marginBottom: 4,
  },
  timeText: {
    fontSize: FontSizes.xs,
    color: Colors.textSecondary,
    marginTop: Spacing.sm,
  },
  loadingText: {
    color: Colors.text,
    fontSize: FontSizes.lg,
    textAlign: 'center',
    marginTop: Spacing.xl,
  },
  emptyText: {
    color: Colors.textSecondary,
    fontSize: FontSizes.md,
    textAlign: 'center',
    marginTop: Spacing.xl,
  },
});
