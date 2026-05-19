import { useEffect, useState } from 'react';
import axios from 'axios';

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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'CRITICAL': return 'bg-red-100 text-red-800 border-red-300';
      case 'WARNING': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'EXCESS': return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'NORMAL': return 'bg-green-100 text-green-800 border-green-300';
      default: return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'CRITICAL': return 'text-red-600';
      case 'NEEDS_ATTENTION': return 'text-yellow-600';
      case 'OVERSTOCKED': return 'text-blue-600';
      case 'HEALTHY': return 'text-green-600';
      default: return 'text-gray-600';
    }
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
      <div className="bg-white rounded-lg shadow p-8">
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <span className="text-red-600 font-bold text-lg">⚠️</span>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Backend Connection Error</h3>
              <p className="mt-1 text-sm text-red-700">
                {error}. Check if the API is running on http://localhost:8000
              </p>
            </div>
          </div>
        </div>
        <div className="text-center">
          <p className="text-lg text-gray-600 mb-4">📊 No intelligence data available</p>
          <p className="text-sm text-gray-500 mb-6">
            Ensure the backend is running and the database is connected
          </p>
          <button
            onClick={fetchData}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
          >
            🔄 Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Executive Summary Card */}
      {narrative && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-semibold text-gray-800">
              📊 Executive Summary
            </h2>
            <span className={`text-xl font-bold ${getHealthColor(narrative.overall_health)}`}>
              {narrative.overall_health}
            </span>
          </div>
          
          <p className="text-gray-700 text-lg mb-4 leading-relaxed">
            {narrative.executive_summary}
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="bg-red-50 p-3 rounded border border-red-200">
              <div className="text-sm text-red-600 font-medium">Critical</div>
              <div className="text-2xl font-bold text-red-700">{narrative.critical_count}</div>
            </div>
            <div className="bg-yellow-50 p-3 rounded border border-yellow-200">
              <div className="text-sm text-yellow-600 font-medium">Warning</div>
              <div className="text-2xl font-bold text-yellow-700">{narrative.warning_count}</div>
            </div>
            <div className="bg-blue-50 p-3 rounded border border-blue-200">
              <div className="text-sm text-blue-600 font-medium">Excess</div>
              <div className="text-2xl font-bold text-blue-700">{narrative.excess_count}</div>
            </div>
            <div className="bg-green-50 p-3 rounded border border-green-200">
              <div className="text-sm text-green-600 font-medium">Normal</div>
              <div className="text-2xl font-bold text-green-700">{narrative.normal_count}</div>
            </div>
          </div>

          {narrative.recommended_actions && narrative.recommended_actions.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-300 rounded p-4">
              <h3 className="text-lg font-semibold text-yellow-800 mb-2">🎯 Recommended Actions:</h3>
              <ul className="list-disc list-inside space-y-1">
                {narrative.recommended_actions.map((action, idx) => (
                  <li key={idx} className="text-yellow-900">{action}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Critical Alerts */}
      {alerts.length > 0 && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">
            🚨 Critical Alerts
          </h2>
          <div className="space-y-2">
            {alerts.slice(0, 10).map((alert, idx) => (
              <div
                key={idx}
                className={`p-3 rounded border-l-4 ${
                  alert.priority === 1 ? 'bg-red-50 border-red-500' :
                  alert.priority === 2 ? 'bg-orange-50 border-orange-500' :
                  alert.priority === 3 ? 'bg-yellow-50 border-yellow-500' :
                  'bg-blue-50 border-blue-500'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="font-semibold text-gray-800">
                      {alert.alert_type}
                    </div>
                    <div className="text-sm text-gray-600 mt-1">
                      {alert.item} @ {alert.company} - {alert.port}
                    </div>
                    <div className="text-sm text-gray-700 mt-1">
                      {alert.alert_message}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Product Intelligence Summary Table */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-semibold text-gray-800 mb-4">
          📈 Product Intelligence Summary
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-blue-500">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold text-white">Product</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-white">Status</th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-white">Current Stock</th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-white">Days Coverage</th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-white">Safety Stock</th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-white">Reorder Point</th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-white">Shortage/Excess</th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-white">Margin %</th>
                <th className="px-4 py-3 text-center text-sm font-semibold text-white">Actions</th>
              </tr>
            </thead>
            <tbody>
              {summary.map((item, index) => (
                <tr
                  key={item.item}
                  className={`${
                    index % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                  } hover:bg-blue-50 transition-colors`}
                >
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 border-b">
                    {item.item}
                  </td>
                  <td className="px-4 py-3 text-sm border-b">
                    <span className={`px-2 py-1 rounded text-xs font-semibold border ${getStatusColor(item.stock_status)}`}>
                      {item.stock_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-gray-700 border-b">
                    {item.total_stock_all_locations?.toLocaleString('en-US', { maximumFractionDigits: 2 }) || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-gray-700 border-b">
                    <span className={
                      item.days_of_stock_remaining < 10 ? 'text-red-600 font-bold' :
                      item.days_of_stock_remaining < 20 ? 'text-yellow-600 font-semibold' :
                      'text-gray-700'
                    }>
                      {item.days_of_stock_remaining?.toFixed(1) || '-'} days
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-gray-600 border-b">
                    {item.safety_stock?.toLocaleString('en-US', { maximumFractionDigits: 0 }) || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-gray-600 border-b">
                    {item.reorder_point?.toLocaleString('en-US', { maximumFractionDigits: 0 }) || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-right border-b">
                    {item.shortage_qty > 0 ? (
                      <span className="text-red-600 font-semibold">
                        -{item.shortage_qty.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                      </span>
                    ) : item.excess_qty > 0 ? (
                      <span className="text-blue-600 font-semibold">
                        +{item.excess_qty.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                      </span>
                    ) : (
                      <span className="text-gray-500">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-right border-b">
                    <span className={
                      item.profit_margin_percent > 20 ? 'text-green-600 font-semibold' :
                      item.profit_margin_percent > 10 ? 'text-green-600' :
                      item.profit_margin_percent > 0 ? 'text-gray-700' :
                      'text-red-600 font-semibold'
                    }>
                      {item.profit_margin_percent?.toFixed(2) || '-'}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-center border-b">
                    <button
                      onClick={() => fetchProductNarrative(item.item)}
                      className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-xs"
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

      {/* Product Narrative Modal */}
      {selectedProduct && productNarrative && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-xl font-semibold text-gray-800">
                Product Analysis: {selectedProduct}
              </h3>
              <button
                onClick={() => {
                  setSelectedProduct(null);
                  setProductNarrative(null);
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
            
            <div className={`p-4 rounded mb-4 ${getStatusColor(productNarrative.status)}`}>
              <div className="font-semibold text-lg mb-2">Status: {productNarrative.status}</div>
            </div>

            <p className="text-gray-700 leading-relaxed mb-4">
              {productNarrative.narrative}
            </p>

            {productNarrative.actions && productNarrative.actions.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-300 rounded p-4">
                <h4 className="font-semibold text-yellow-800 mb-2">Recommended Actions:</h4>
                <ul className="list-disc list-inside space-y-1">
                  {productNarrative.actions.map((action: string, idx: number) => (
                    <li key={idx} className="text-yellow-900">{action}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-4 flex justify-end">
              <button
                onClick={() => {
                  setSelectedProduct(null);
                  setProductNarrative(null);
                }}
                className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
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
