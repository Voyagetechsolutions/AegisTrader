import { View, Text, StyleSheet, FlatList, TouchableOpacity } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '../../services/api';
import { Colors, Spacing, FontSizes } from '../../constants/theme';
import { Signal } from '../../types';

export default function Signals() {
  const { data: signals, isLoading } = useQuery<Signal[]>({
    queryKey: ['signals'],
    queryFn: () => dashboardApi.getSignals(20),
    refetchInterval: 10000,
  });

  const getGradeColor = (grade: string | null) => {
    switch (grade) {
      case 'A+': return Colors.gradeAPlus;
      case 'A': return Colors.gradeA;
      case 'B': return Colors.gradeB;
      default: return Colors.textSecondary;
    }
  };

  const renderSignal = ({ item }: { item: Signal }) => (
    <TouchableOpacity style={styles.signalCard}>
      <View style={styles.signalHeader}>
        <View style={[styles.directionBadge, { backgroundColor: item.direction === 'long' ? Colors.long : Colors.short }]}>
          <Text style={styles.directionText}>{item.direction?.toUpperCase() || 'N/A'}</Text>
        </View>
        <View style={[styles.gradeBadge, { backgroundColor: getGradeColor(item.grade) }]}>
          <Text style={styles.gradeText}>{item.grade || 'N/A'}</Text>
        </View>
        <Text style={styles.scoreText}>{item.score}/100</Text>
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
          <Text style={styles.priceLabel}>TP1</Text>
          <Text style={styles.priceValue}>{item.tp1.toFixed(1)}</Text>
        </View>
      </View>

      <Text style={styles.sessionText}>{item.session_name || 'No session'}</Text>
      <Text style={styles.timeText}>
        {item.created_at ? new Date(item.created_at).toLocaleString() : 'N/A'}
      </Text>

      {item.news_blocked && (
        <Text style={styles.blockedText}>⚠️ Blocked by news filter</Text>
      )}
      {!item.eligible_for_auto_trade && (
        <Text style={styles.blockedText}>⚠️ Not eligible for auto-trade</Text>
      )}
    </TouchableOpacity>
  );

  if (isLoading) {
    return (
      <View style={styles.container}>
        <Text style={styles.loadingText}>Loading signals...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={signals}
        renderItem={renderSignal}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <Text style={styles.emptyText}>No signals yet. System is analyzing...</Text>
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
  signalCard: {
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: Spacing.lg,
    marginBottom: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  signalHeader: {
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
  gradeBadge: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: 6,
    marginRight: Spacing.sm,
  },
  gradeText: {
    color: Colors.text,
    fontWeight: 'bold',
    fontSize: FontSizes.sm,
  },
  scoreText: {
    color: Colors.text,
    fontSize: FontSizes.lg,
    fontWeight: 'bold',
    marginLeft: 'auto',
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
  sessionText: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    marginBottom: Spacing.xs,
  },
  timeText: {
    fontSize: FontSizes.xs,
    color: Colors.textSecondary,
  },
  blockedText: {
    fontSize: FontSizes.sm,
    color: Colors.danger,
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
