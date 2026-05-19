import { useEffect, useState } from 'react';
import axios from 'axios';
import { colors, getStatusColor, getHealthColor, getHealthBgColor } from '../styles/colors';

interface IntelligenceSummary {
  item: string;
  total_stock_all_locations: number;
  total_unsold_all_locations: number;
  total_incoming_all_locations: number;
  overall_avg_market_price: number;
  overall_avg_selling_price: number;
  overall_avg_purchase_price: number;
  safety_stock: number;
  reorder_point: number;
  max_storage_days: number;
  max_inventory_days: number;
  monthly_target_volume: number;
  days_of_stock_remaining: number;
  stock_status: string;
  shortage_qty: number;
  excess_qty: number;
  profit_margin_percent: number;
  target_fulfillment_percent: number;
  company_count: number;
  port_count: number;
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
  avg_days_stock: number;
  total_shortage: number;
  total_excess: number;
  avg_profit_margin: number;
  aged_count: number;
  aging_soon_count: number;
  recommended_actions: string[];
}

const API_BASE_URL = 'http://localhost:8000';

const InsightsDashboard: React.FC = () => {
  const [summary, setSummary] = useState<IntelligenceSummary[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [narrative, setNarrative] = useState<Narrative | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<string | null>(null);
  const [productNarrative, setProductNarrative] = useState<any>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [summaryRes, alertsRes, narrativeRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/api/intelligence/summary`),
        axios.get(`${API_BASE_URL}/api/intelligence/alerts`),
        axios.get(`${API_BASE_URL}/api/intelligence/narrative`)
      ]);

      if (summaryRes.data.success) {
        setSummary(summaryRes.data.data);
      }
      if (alertsRes.data.success) {
        setAlerts(alertsRes.data.data);
      }
      if (narrativeRes.data.success) {
        setNarrative(narrativeRes.data.data);
      }
      
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch intelligence data');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchProductNarrative = async (productName: string) => {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/intelligence/product/${encodeURIComponent(productName)}`
      );
      if (response.data.success) {
        setProductNarrative(response.data.data);
        setSelectedProduct(productName);
      }
    } catch (err: any) {
      console.error('Error fetching product narrative:', err);
    }
  };

  const getStatusColorForBadge = (status: string) => {
    const colorObj = getStatusColor(status);
    return colorObj.badge;
  };

  const getHealthColorClass = (health: string) => {
    return getHealthColor(health);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-xl text-gray-600">Loading insights...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-100 p-8 flex items-center justify-center">
        <div className="max-w-2xl w-full">
          <div className="bg-gradient-to-br from-white to-slate-50 rounded-2xl shadow-xl border border-slate-200 p-12">
            <div className="mb-8 bg-gradient-to-br from-rose-50 to-rose-100/50 border border-rose-200 rounded-2xl p-6 shadow-md">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 text-4xl">⚠️</div>
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-rose-900 mb-2">Backend Connection Error</h3>
                  <p className="text-rose-800 font-medium">
                    {error}. Check if the API is running on http://localhost:8000
                  </p>
                </div>
              </div>
            </div>
            
            <div className="text-center">
              <p className="text-2xl mb-3">📊</p>
              <p className="text-xl font-bold text-slate-800 mb-2">No Intelligence Data Available</p>
              <p className="text-slate-600 mb-8">
                Ensure the backend is running and the database is connected
              </p>
              <button
                onClick={fetchData}
                className="px-6 py-3 bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-semibold rounded-xl hover:shadow-lg transition-all duration-300 hover:scale-105"
              >
                🔄 Retry Connection
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-100 p-6 md:p-10">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 md:gap-8 max-w-7xl mx-auto">
        {/* Main Central Panel */}
        <div className="lg:col-span-2 space-y-6 md:space-y-8">
          {/* Executive Summary Card */}
          {narrative && (
            <div className={`${colors.cards.primary} rounded-2xl ${colors.shadows.lg} border border-slate-200 p-8 md:p-10 transition-all duration-300 hover:shadow-xl`}>
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-8 gap-4">
                <h2 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent">
                  📊 Executive Summary
                </h2>
                <div className={`px-6 py-3 rounded-full font-bold text-sm tracking-wider uppercase whitespace-nowrap shadow-md border ${getHealthBgColor(narrative.overall_health)} ${getHealthColorClass(narrative.overall_health)}`}>
                  {narrative.overall_health}
                </div>
              </div>
              
              <p className="text-slate-700 text-lg mb-10 leading-relaxed font-medium">
                {narrative.executive_summary}
              </p>

              {/* Status Cards Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                {[
                  { label: 'Critical', count: narrative.critical_count, statusKey: 'critical' },
                  { label: 'Warning', count: narrative.warning_count, statusKey: 'warning' },
                  { label: 'Excess', count: narrative.excess_count, statusKey: 'excess' },
                  { label: 'Normal', count: narrative.normal_count, statusKey: 'normal' },
                ].map(({ label, count, statusKey }: any) => {
                  const statusColor = colors.status[statusKey as keyof typeof colors.status];
                  return (
                    <div
                      key={statusKey}
                      className={`bg-gradient-to-br ${statusColor.bg} rounded-2xl border ${statusColor.border} ${colors.shadows.md} p-6 flex flex-col items-center justify-center text-center hover:shadow-lg transition-all duration-300 hover:scale-105`}
                    >
                      <div className={`text-sm font-bold tracking-wider uppercase flex items-center gap-2 ${statusColor.text}`}>
                        <span className="text-2xl">{statusColor.icon}</span>
                        {label}
                      </div>
                      <div className={`text-5xl font-extrabold mt-3 ${statusColor.text}`}>{count}</div>
                    </div>
                  );
                })}
              </div>

              {/* Recommended Actions */}
              {narrative.recommended_actions && narrative.recommended_actions.length > 0 && (
                <div className="bg-gradient-to-br from-amber-50 to-yellow-50/30 border border-amber-200 rounded-2xl p-6 mt-8 shadow-md">
                  <h3 className="text-sm font-bold text-amber-900 mb-4 uppercase tracking-wider flex items-center gap-2">
                    <span className="text-xl">🎯</span> Recommended Actions
                  </h3>
                  <ul className="space-y-3">
                    {narrative.recommended_actions.map((action, idx) => (
                      <li key={idx} className="text-amber-900 font-medium flex items-start gap-3">
                        <span className="text-amber-500 font-bold mt-1">•</span>
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Product Intelligence Table */}
          <div className={`${colors.cards.primary} rounded-2xl ${colors.shadows.lg} border border-slate-200 p-8 md:p-10 overflow-hidden transition-all duration-300 hover:shadow-xl`}>
            <h2 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent mb-8">
              📈 Product Intelligence
            </h2>
            <div className="overflow-x-auto rounded-xl">
              <table className="w-full text-left border-collapse">
                <thead className="bg-gradient-to-r from-slate-100 to-slate-50 border-b-2 border-slate-200">
                  <tr>
                    <th className="px-6 py-4 text-xs font-bold text-slate-600 uppercase tracking-wider rounded-tl-lg">Product</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-600 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-600 uppercase tracking-wider text-right">Stock</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-600 uppercase tracking-wider text-right">Coverage</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-600 uppercase tracking-wider text-right">Gap</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-600 uppercase tracking-wider text-right">Margin %</th>
                    <th className="px-6 py-4 text-center text-xs font-bold text-slate-600 uppercase tracking-wider rounded-tr-lg">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {summary.map((item) => (
                    <tr
                      key={item.item}
                      className="hover:bg-gradient-to-r hover:from-slate-50 hover:to-blue-50/30 transition-all duration-200 hover:shadow-sm"
                    >
                      <td className="px-6 py-5 text-sm font-semibold text-slate-800">
                        {item.item}
                      </td>
                      <td className="px-6 py-5 text-sm">
                        <span className={`px-3 py-1.5 rounded-full text-xs font-bold border inline-block ${getStatusColorForBadge(item.stock_status)}`}>
                          {item.stock_status}
                        </span>
                      </td>
                      <td className="px-6 py-5 text-sm text-right text-slate-700 font-semibold">
                        {item.total_stock_all_locations?.toLocaleString('en-US', { maximumFractionDigits: 0 }) || '-'}
                      </td>
                      <td className="px-6 py-5 text-sm text-right font-bold">
                        <span className={
                          item.days_of_stock_remaining < 10 ? 'text-rose-600' :
                          item.days_of_stock_remaining < 20 ? 'text-amber-600' :
                          'text-emerald-600'
                        }>
                          {item.days_of_stock_remaining?.toFixed(1) || '-'} d
                        </span>
                      </td>
                      <td className="px-6 py-5 text-sm text-right font-bold">
                        {item.shortage_qty > 0 ? (
                          <span className="text-rose-600 bg-rose-50 px-3 py-1.5 rounded-lg inline-block border border-rose-200">
                            -{item.shortage_qty.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                          </span>
                        ) : item.excess_qty > 0 ? (
                          <span className="text-sky-600 bg-sky-50 px-3 py-1.5 rounded-lg inline-block border border-sky-200">
                            +{item.excess_qty.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                          </span>
                        ) : (
                          <span className="text-slate-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-5 text-sm text-right font-bold">
                        <span className={
                          item.profit_margin_percent > 20 ? 'text-emerald-600' :
                          item.profit_margin_percent > 10 ? 'text-emerald-500' :
                          item.profit_margin_percent > 0 ? 'text-slate-700' :
                          'text-rose-600'
                        }>
                          {item.profit_margin_percent?.toFixed(2) || '-'}%
                        </span>
                      </td>
                      <td className="px-6 py-5 text-sm text-center">
                        <button
                          onClick={() => fetchProductNarrative(item.item)}
                          className="px-4 py-2 bg-gradient-to-r from-indigo-50 to-blue-50 text-indigo-700 font-bold rounded-lg hover:from-indigo-100 hover:to-blue-100 transition-all duration-300 text-xs shadow-sm border border-indigo-200 hover:shadow-md hover:scale-105"
                        >
                          Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Sidebar - Critical Alerts */}
        <div className="lg:col-span-1">
          {alerts.length > 0 && (
            <div className={`${colors.cards.primary} rounded-2xl ${colors.shadows.lg} border border-slate-200 p-6 md:p-8 lg:sticky lg:top-6 transition-all duration-300 hover:shadow-xl h-fit`}>
              <h2 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent mb-6">
                🚨 Active Alerts
              </h2>
              <div className="space-y-4 max-h-[800px] overflow-y-auto pr-2 custom-scrollbar">
                {alerts.slice(0, 10).map((alert, idx) => {
                  const statusColor = getStatusColor(alert.priority === 1 ? 'CRITICAL' : alert.priority === 2 ? 'WARNING' : alert.priority === 3 ? 'EXCESS' : 'NORMAL');
                  return (
                    <div
                      key={idx}
                      className={`bg-gradient-to-br ${statusColor.bg} rounded-xl border ${statusColor.border} ${colors.shadows.md} p-4 transition-all duration-300 hover:shadow-lg hover:scale-105 hover:-translate-y-1 cursor-pointer`}
                    >
                      <div className="flex flex-col gap-3">
                        <div className={`font-bold text-sm ${statusColor.text} uppercase tracking-wide`}>
                          {statusColor.icon} {alert.alert_type}
                        </div>
                        <div className="text-xs font-semibold text-slate-600">
                          {alert.item} • {alert.company} • {alert.port}
                        </div>
                        <div className="text-sm text-slate-700 bg-white/80 backdrop-blur-sm p-3 rounded-lg border border-white/50 mt-1">
                          {alert.alert_message}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Product Narrative Modal */}
      {selectedProduct && productNarrative && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-300">
          <div className="bg-gradient-to-br from-white to-slate-50 rounded-2xl shadow-2xl max-w-3xl w-full p-10 border border-slate-200 animate-in scale-95 duration-300 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-8">
              <h3 className="text-3xl font-bold bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent">
                {selectedProduct} Analysis
              </h3>
              <button
                onClick={() => {
                  setSelectedProduct(null);
                  setProductNarrative(null);
                }}
                className="text-slate-400 hover:text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-full w-10 h-10 flex items-center justify-center transition-all duration-300 hover:scale-110 font-bold text-lg"
              >
                ✕
              </button>
            </div>
            
            <div className={`px-6 py-4 rounded-xl mb-8 inline-flex border ${colors.shadows.md} font-bold text-sm uppercase tracking-wider ${getStatusColorForBadge(productNarrative.status)}`}>
              STATUS: {productNarrative.status}
            </div>

            <p className="text-slate-700 text-lg leading-relaxed mb-10 font-medium">
              {productNarrative.narrative}
            </p>

            {productNarrative.actions && productNarrative.actions.length > 0 && (
              <div className="bg-gradient-to-br from-indigo-50 to-blue-50 border border-indigo-200 rounded-2xl p-8 mb-8 shadow-md">
                <h4 className="font-bold text-indigo-900 mb-4 uppercase text-sm tracking-wider flex items-center gap-2">
                  <span className="text-xl">💡</span> Recommended Actions
                </h4>
                <ul className="space-y-3">
                  {productNarrative.actions.map((action: string, idx: number) => (
                    <li key={idx} className="text-indigo-900 font-medium flex items-start gap-3">
                      <span className="text-indigo-500 font-bold mt-1">→</span>
                      {action}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-10 flex justify-end gap-4">
              <button
                onClick={() => {
                  setSelectedProduct(null);
                  setProductNarrative(null);
                }}
                className="px-8 py-3 bg-gradient-to-r from-slate-100 to-slate-50 text-slate-700 font-bold rounded-xl hover:from-slate-200 hover:to-slate-100 transition-all duration-300 border border-slate-200 hover:shadow-lg hover:scale-105"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InsightsDashboard;
