import { useEffect, useState } from 'react';
import axios from 'axios';
import { crystalColors } from '../styles/crystalColors';

interface Summary {
  total_products: number;
  total_physical_stock: number;
  total_stock_value: number;
  total_sold_qty: number;
  total_unsold_qty: number;
}

interface Alert {
  priority: number;
  alert_type: string;
  item: string;
  company: string;
  port: string;
  physical_stock: number;
  safety_stock: number;
  reorder_point: number;
  days_old: number;
  max_storage_days: number;
  alert_message: string;
}

interface Narrative {
  overall_health: string;
  executive_summary: string;
  total_products: number;
  critical_count: number;
  warning_count: number;
  excess_count: number;
  normal_count: number;
}

const API_BASE_URL = 'http://localhost:8000';

const AnalyticsInsightsColumn: React.FC = () => {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [narrative, setNarrative] = useState<Narrative | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [summaryRes, alertsRes, narrativeRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/api/inventory/summary`),
        axios.get(`${API_BASE_URL}/api/intelligence/alerts`),
        axios.get(`${API_BASE_URL}/api/intelligence/narrative`),
      ]);

      if (summaryRes.data.success) {
        setSummary(summaryRes.data.summary);
      }
      if (alertsRes.data.success) {
        setAlerts(alertsRes.data.data.slice(0, 5)); // Top 5 alerts
      }
      if (narrativeRes.data.success) {
        setNarrative(narrativeRes.data.data);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch analytics');
    } finally {
      setLoading(false);
    }
  };

  const getAlertColor = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'critical':
      case 'shortage':
        return { bg: '#FEE2E2', text: '#991B1B', border: '#FCA5A5', icon: '🔴' };
      case 'warning':
      case 'aging':
        return { bg: '#FEF3C7', text: '#92400E', border: '#FCD34D', icon: '🟠' };
      case 'excess':
        return { bg: '#CFFAFE', text: '#164E63', border: '#A5F3FC', icon: '🔵' };
      default:
        return { bg: '#D1FAE5', text: '#065F46', border: '#6EE7B7', icon: '🟢' };
    }
  };

  const getHealthColor = (health: string) => {
    switch (health?.toLowerCase()) {
      case 'critical':
        return crystalColors.status.warning;
      case 'needs attention':
        return crystalColors.status.pending;
      case 'healthy':
        return crystalColors.status.active;
      default:
        return crystalColors.primary.teal;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="text-4xl mb-3">📊</div>
          <p className="text-slate-600 font-semibold">Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div
        className="p-6 rounded-2xl text-white shadow-lg"
        style={{
          background: `linear-gradient(135deg, ${crystalColors.primary.teal} 0%, ${crystalColors.primary.cyan} 100%)`,
        }}
      >
        <h2 className="text-2xl font-bold mb-2">📊 Analytics & Insights</h2>
        <p className="opacity-90 text-sm">Summary and key performance metrics</p>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 gap-3">
          {[
            {
              label: 'Total Products',
              value: summary.total_products,
              icon: '📦',
              color: crystalColors.primary.purple,
            },
            {
              label: 'Physical Stock',
              value: summary.total_physical_stock.toLocaleString('en-US', { maximumFractionDigits: 0 }),
              icon: '📈',
              color: crystalColors.primary.teal,
            },
            {
              label: 'Total Sold',
              value: summary.total_sold_qty.toLocaleString('en-US', { maximumFractionDigits: 0 }),
              icon: '✅',
              color: crystalColors.status.active,
            },
            {
              label: 'Stock Value',
              value: `₹${summary.total_stock_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
              icon: '💰',
              color: crystalColors.primary.cyan,
            },
          ].map((card, idx) => (
            <div
              key={idx}
              className="p-4 rounded-xl border transition-all duration-300 hover:shadow-md"
              style={{
                background: crystalColors.backgrounds.white,
                borderColor: crystalColors.borders.light,
              }}
            >
              <div className="text-2xl mb-2">{card.icon}</div>
              <p className="text-xs text-slate-500 font-semibold mb-1">{card.label}</p>
              <p className="text-lg font-bold" style={{ color: card.color }}>
                {card.value}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Health Status */}
      {narrative && (
        <div
          className="p-5 rounded-xl border-l-4"
          style={{
            background: crystalColors.backgrounds.light,
            borderColor: getHealthColor(narrative.overall_health),
          }}
        >
          <div className="flex items-start gap-3">
            <div className="text-2xl">🏥</div>
            <div className="flex-1">
              <p className="font-bold text-slate-900 text-sm">Overall Health</p>
              <p
                className="text-lg font-bold mt-1"
                style={{ color: getHealthColor(narrative.overall_health) }}
              >
                {narrative.overall_health.toUpperCase()}
              </p>
              <div className="grid grid-cols-4 gap-2 mt-3 text-xs">
                <div>
                  <p className="text-slate-500">Critical</p>
                  <p className="font-bold text-red-600">{narrative.critical_count}</p>
                </div>
                <div>
                  <p className="text-slate-500">Warning</p>
                  <p className="font-bold text-amber-600">{narrative.warning_count}</p>
                </div>
                <div>
                  <p className="text-slate-500">Excess</p>
                  <p className="font-bold text-blue-600">{narrative.excess_count}</p>
                </div>
                <div>
                  <p className="text-slate-500">Normal</p>
                  <p className="font-bold text-green-600">{narrative.normal_count}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Alerts */}
      <div>
        <h3 className="font-bold text-slate-900 mb-3 text-sm">⚠️ TOP ALERTS</h3>
        <div className="space-y-2 max-h-72 overflow-y-auto pr-2 custom-scrollbar">
          {error ? (
            <div className="p-3 rounded-lg text-red-700 text-xs font-medium bg-red-50 border border-red-200">
              {error}
            </div>
          ) : alerts.length === 0 ? (
            <div className="p-3 rounded-lg text-green-700 text-xs font-medium bg-green-50 border border-green-200">
              ✓ No critical alerts
            </div>
          ) : (
            alerts.map((alert, idx) => {
              const colors = getAlertColor(alert.alert_type);
              return (
                <div
                  key={idx}
                  className="p-3 rounded-lg border"
                  style={{
                    background: colors.bg,
                    borderColor: colors.border,
                    color: colors.text,
                  }}
                >
                  <div className="flex items-start gap-2">
                    <div className="text-lg">{colors.icon}</div>
                    <div className="flex-1">
                      <p className="font-bold text-xs">{alert.item}</p>
                      <p className="text-xs opacity-80 mt-1">{alert.alert_message}</p>
                      <p className="text-xs opacity-60 mt-1">
                        {alert.company} • {alert.port}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Refresh Button */}
      <button
        onClick={fetchData}
        className="w-full py-3 rounded-xl font-semibold text-white transition-all duration-300 hover:shadow-lg transform hover:scale-105 flex items-center justify-center gap-2"
        style={{
          background: `linear-gradient(135deg, ${crystalColors.primary.teal} 0%, ${crystalColors.primary.cyan} 100%)`,
        }}
      >
        🔄 Refresh
      </button>
    </div>
  );
};

export default AnalyticsInsightsColumn;
