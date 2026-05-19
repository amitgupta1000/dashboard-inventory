import { useEffect, useState } from 'react';
import axios from 'axios';
import './styles/animations.css';
import DataTable from './components/DataTable';
import ProductSettings from './components/ProductSettings';
import InsightsDashboard from './components/InsightsDashboard';

interface InventoryItem {
  company_name: string;
  port_name: string;
  product_name: string;
  physical_stock: number;
  total_sold_qty: number;
  total_unsold_qty: number;
  incoming_vessel_qty: number | string;
  avg_import_price_usd: number;
  avg_price_inr: number;
  current_market_price: number | string;
  replacement_cost: number | string;
  stock_value: number;
}

interface Summary {
  total_products: number;
  total_physical_stock: number;
  total_stock_value: number;
  total_sold_qty: number;
  total_unsold_qty: number;
}

type TabType = 'inventory' | 'insights' | 'settings';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('insights');
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (activeTab === 'inventory') {
      fetchData();
    }
  }, [activeTab]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [inventoryRes, summaryRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/api/inventory`),
        axios.get(`${API_BASE_URL}/api/inventory/summary`)
      ]);

      if (inventoryRes.data.success) {
        setInventory(inventoryRes.data.data);
      }
      
      if (summaryRes.data.success) {
        setSummary(summaryRes.data.summary);
      }
      
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch data');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-100">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-slate-50 to-white border-b border-slate-200 sticky top-0 z-40 shadow-sm">
          <div className="px-6 md:px-10 py-8">
            <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-slate-800 via-blue-700 to-indigo-600 bg-clip-text text-transparent">
              📊 Sumairo Inventory Dashboard
            </h1>
            <p className="text-slate-600 mt-2 font-medium">Real-time inventory intelligence and management</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="sticky top-[105px] z-30 bg-white border-b border-slate-200 shadow-sm">
          <div className="px-6 md:px-10">
            <nav className="flex space-x-1">
              {[
                { id: 'insights' as const, label: '🧠 Intelligence & Insights' },
                { id: 'inventory' as const, label: '📊 Inventory Data' },
                { id: 'settings' as const, label: '⚙️ Product Settings' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-6 py-4 font-semibold text-sm transition-all duration-300 border-b-2 whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600 bg-gradient-to-b from-blue-50/50 to-transparent'
                      : 'border-transparent text-slate-600 hover:text-slate-800 hover:border-slate-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Content Area */}
        <div className="px-6 md:px-10 py-8 md:py-12">
          {activeTab === 'insights' && <InsightsDashboard />}

          {activeTab === 'inventory' && (
            <>
              {loading ? (
                <div className="flex items-center justify-center p-16">
                  <div className="text-center">
                    <div className="inline-block mb-4">
                      <div className="animate-spin">
                        <span className="text-5xl">⏳</span>
                      </div>
                    </div>
                    <p className="text-xl text-slate-600 font-semibold">Loading inventory data...</p>
                    <p className="text-slate-500 mt-2">Please wait while we fetch your data</p>
                  </div>
                </div>
              ) : error ? (
                <div className="bg-gradient-to-br from-white to-slate-50 rounded-2xl shadow-lg border border-slate-200 p-12 max-w-2xl mx-auto">
                  <div className="mb-8 bg-gradient-to-br from-rose-50 to-rose-100/50 border border-rose-200 rounded-2xl p-6">
                    <div className="flex items-start gap-4">
                      <div className="text-4xl">⚠️</div>
                      <div>
                        <h3 className="text-lg font-bold text-rose-900">Backend Connection Error</h3>
                        <p className="text-rose-800 mt-1 font-medium">{error}</p>
                        <p className="text-rose-700 text-sm mt-2">Check if the API is running on http://localhost:8000</p>
                      </div>
                    </div>
                  </div>
                  <div className="text-center">
                    <button
                      onClick={fetchData}
                      className="px-8 py-3 bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-bold rounded-xl hover:shadow-lg transition-all duration-300 hover:scale-105"
                    >
                      🔄 Retry Connection
                    </button>
                  </div>
                </div>
              ) : inventory.length === 0 ? (
                <div className="bg-gradient-to-br from-white to-slate-50 rounded-2xl shadow-lg border border-slate-200 p-16 text-center max-w-2xl mx-auto">
                  <p className="text-3xl mb-4">📦</p>
                  <p className="text-2xl font-bold text-slate-800 mb-2">No inventory records yet</p>
                  <p className="text-slate-600 font-medium">Upload a stock_report.xlsx file to populate inventory data</p>
                </div>
              ) : (
                <>
                  {summary && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-5 mb-10">
                      {[
                        { label: 'Total Products', value: summary.total_products.toString(), icon: '📦', color: 'from-blue-50 to-blue-100/50', textColor: 'text-blue-700', borderColor: 'border-blue-200' },
                        { label: 'Physical Stock', value: summary.total_physical_stock.toLocaleString('en-US', { maximumFractionDigits: 0 }), icon: '📊', color: 'from-purple-50 to-purple-100/50', textColor: 'text-purple-700', borderColor: 'border-purple-200' },
                        { label: 'Total Sold', value: summary.total_sold_qty.toLocaleString('en-US', { maximumFractionDigits: 0 }), icon: '📈', color: 'from-green-50 to-green-100/50', textColor: 'text-green-700', borderColor: 'border-green-200' },
                        { label: 'Unsold Qty', value: summary.total_unsold_qty.toLocaleString('en-US', { maximumFractionDigits: 0 }), icon: '📉', color: 'from-amber-50 to-amber-100/50', textColor: 'text-amber-700', borderColor: 'border-amber-200' },
                        { label: 'Stock Value', value: '₹' + summary.total_stock_value.toLocaleString('en-US', { maximumFractionDigits: 0 }), icon: '💰', color: 'from-emerald-50 to-emerald-100/50', textColor: 'text-emerald-700', borderColor: 'border-emerald-200' },
                      ].map((card, idx) => (
                        <div
                          key={idx}
                          className={`bg-gradient-to-br ${card.color} rounded-2xl border ${card.borderColor} shadow-md p-6 transition-all duration-300 hover:shadow-lg hover:scale-105 hover:-translate-y-1`}
                        >
                          <div className="text-3xl mb-2">{card.icon}</div>
                          <p className={`text-xs font-bold uppercase tracking-wider ${card.textColor}`}>{card.label}</p>
                          <p className={`text-2xl md:text-3xl font-extrabold mt-3 ${card.textColor}`}>{card.value}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  <DataTable data={inventory} />
                </>
              )}
            </>
          )}

          {activeTab === 'settings' && <ProductSettings />}
        </div>
      </div>
    </div>
  );
}

export default App;
