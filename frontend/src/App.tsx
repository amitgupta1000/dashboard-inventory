import { useEffect, useState } from 'react';
import axios from 'axios';
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
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-semibold text-gray-800 border-b-2 border-blue-500 pb-3">
            Sumairo Inventory Management Dashboard
          </h1>
        </div>

        {/* Tab Navigation */}
        <div className="mb-6">
          <div className="border-b border-gray-300">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('insights')}
                className={`${
                  activeTab === 'insights'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
              >
                🧠 Intelligence & Insights
              </button>
              <button
                onClick={() => setActiveTab('inventory')}
                className={`${
                  activeTab === 'inventory'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
              >
                📊 Sumairo Inventory Dashboard
              </button>
              <button
                onClick={() => setActiveTab('settings')}
                className={`${
                  activeTab === 'settings'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
              >
                ⚙️ Product Settings
              </button>
            </nav>
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === 'insights' && <InsightsDashboard />}

        {activeTab === 'inventory' && (
          <>
            {loading ? (
              <div className="flex items-center justify-center p-8">
                <div className="text-xl text-gray-600">Loading inventory data...</div>
              </div>
            ) : error ? (
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
                  <p className="text-lg text-gray-600 mb-4">📦 No inventory data available</p>
                  <button
                    onClick={fetchData}
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
                  >
                    🔄 Retry Connection
                  </button>
                </div>
              </div>
            ) : inventory.length === 0 ? (
              <div className="bg-white rounded-lg shadow p-8">
                <div className="text-center">
                  <p className="text-lg text-gray-600 mb-2">📊 No inventory records yet</p>
                  <p className="text-sm text-gray-500">
                    Upload a stock_report.xlsx file to populate inventory data
                  </p>
                </div>
              </div>
            ) : (
              <>
                {summary && (
                  <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
                    <div className="bg-white p-4 rounded-lg shadow">
                      <div className="text-sm text-gray-600">Total Products</div>
                      <div className="text-2xl font-bold text-gray-800">{summary.total_products}</div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                      <div className="text-sm text-gray-600">Physical Stock</div>
                      <div className="text-2xl font-bold text-gray-800">
                        {summary.total_physical_stock.toLocaleString('en-US', { maximumFractionDigits: 2 })}
                      </div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                      <div className="text-sm text-gray-600">Total Sold Qty</div>
                      <div className="text-2xl font-bold text-gray-800">
                        {summary.total_sold_qty.toLocaleString('en-US', { maximumFractionDigits: 2 })}
                      </div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                      <div className="text-sm text-gray-600">Total Unsold Qty</div>
                      <div className="text-2xl font-bold text-gray-800">
                        {summary.total_unsold_qty.toLocaleString('en-US', { maximumFractionDigits: 2 })}
                      </div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                      <div className="text-sm text-gray-600">Stock Value</div>
                      <div className="text-2xl font-bold text-green-600">
                        ₹{summary.total_stock_value.toLocaleString('en-US', { maximumFractionDigits: 2 })}
                      </div>
                    </div>
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
  );
}

export default App;
