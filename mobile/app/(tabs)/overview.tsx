import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '../../services/api';
import { Colors, Spacing, FontSizes } from '../../constants/theme';
import { WeeklyOverview } from '../../types';

export default function Overview() {
  const { data: overview, isLoading } = useQuery<WeeklyOverview>({
    queryKey: ['weeklyOverview'],
    queryFn: dashboardApi.getWeeklyOverview,
  });

  if (isLoading) {
    return (
      <View style={styles.container}>
        <Text style={styles.loadingText}>Loading overview...</Text>
      </View>
    );
  }

  if (!overview) {
    return (
      <View style={styles.container}>
        <Text style={styles.emptyText}>No weekly overview available yet.</Text>
        <Text style={styles.infoText}>Run /overview command in Telegram to generate.</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      {/* Bias Ladder */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Bias Ladder</Text>
        <View style={styles.biasRow}>
          <Text style={styles.biasLabel}>Weekly</Text>
          <Text style={styles.biasValue}>{overview.weekly_bias}</Text>
        </View>
        <View style={styles.biasRow}>
          <Text style={styles.biasLabel}>Daily</Text>
          <Text style={styles.biasValue}>{overview.daily_bias}</Text>
        </View>
        <View style={styles.biasRow}>
          <Text style={styles.biasLabel}>4H</Text>
          <Text style={styles.biasValue}>{overview.h4_bias}</Text>
        </View>
        <View style={styles.biasRow}>
          <Text style={styles.biasLabel}>1H</Text>
          <Text style={styles.biasValue}>{overview.h1_bias}</Text>
        </View>
        <View style={styles.biasRow}>
          <Text style={styles.biasLabel}>15M</Text>
          <Text style={styles.biasValue}>{overview.m15_bias}</Text>
        </View>
        <View style={styles.biasRow}>
          <Text style={styles.biasLabel}>5M</Text>
          <Text style={styles.biasValue}>{overview.m5_bias}</Text>
        </View>
        <View style={styles.biasRow}>
          <Text style={styles.biasLabel}>1M</Text>
          <Text style={styles.biasValue}>{overview.m1_bias}</Text>
        </View>
      </View>

      {/* Scenarios */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Bullish Scenario</Text>
        <Text style={styles.scenarioText}>{overview.bullish_scenario}</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Bearish Scenario</Text>
        <Text style={styles.scenarioText}>{overview.bearish_scenario}</Text>
      </View>

      {/* Key Levels */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Key Levels</Text>
        {overview.key_levels.map((level, index) => (
          <Text key={index} style={styles.levelText}>{level.toFixed(1)}</Text>
        ))}
      </View>

      {/* Major News */}
      {overview.major_news && overview.major_news.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Major News This Week</Text>
          {overview.major_news.map((news, index) => (
            <View key={index} style={styles.newsItem}>
              <Text style={styles.newsDate}>{news.date}</Text>
              <Text style={styles.newsEvent}>{news.event}</Text>
              <Text style={[styles.newsImpact, { color: news.impact === 'high' ? Colors.danger : Colors.warning }]}>
                {news.impact.toUpperCase()}
              </Text>
            </View>
          ))}
        </View>
      )}

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
  card: {
    backgroundColor: Colors.card,
    borderRadius: 8,
    padding: Spacing.lg,
    marginBottom: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  cardTitle: {
    fontSize: FontSizes.lg,
    fontWeight: 'bold',
    color: Colors.text,
    marginBottom: Spacing.md,
  },
  biasRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: Spacing.sm,
  },
  biasLabel: {
    fontSize: FontSizes.md,
    color: Colors.textSecondary,
  },
  biasValue: {
    fontSize: FontSizes.md,
    color: Colors.text,
    fontWeight: '600',
  },
  scenarioText: {
    fontSize: FontSizes.md,
    color: Colors.text,
    lineHeight: 22,
  },
  levelText: {
    fontSize: FontSizes.lg,
    color: Colors.text,
    fontWeight: '600',
    marginBottom: Spacing.xs,
  },
  newsItem: {
    marginBottom: Spacing.md,
  },
  newsDate: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    marginBottom: Spacing.xs,
  },
  newsEvent: {
    fontSize: FontSizes.md,
    color: Colors.text,
    marginBottom: Spacing.xs,
  },
  newsImpact: {
    fontSize: FontSizes.sm,
    fontWeight: 'bold',
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
  infoText: {
    color: Colors.textSecondary,
    fontSize: FontSizes.sm,
    textAlign: 'center',
    marginTop: Spacing.md,
  },
});
