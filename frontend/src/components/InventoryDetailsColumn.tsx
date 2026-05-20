import { useEffect, useState } from 'react';
import axios from 'axios';
import { crystalColors } from '../styles/crystalColors';

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

const API_BASE_URL = 'http://localhost:8000';

const InventoryDetailsColumn: React.FC = () => {
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchInventory();
  }, []);

  const fetchInventory = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API_BASE_URL}/api/inventory`);
      if (res.data.success) {
        setInventory(res.data.data.slice(0, 10)); // Show latest 10
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch inventory');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="text-4xl mb-3">⏳</div>
          <p className="text-slate-600 font-semibold">Loading inventory...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Header */}
      <div
        className="p-4 md:p-6 rounded-2xl text-white shadow-xl hover:shadow-2xl transition-shadow duration-300"
        style={{
          background: `linear-gradient(135deg, ${crystalColors.primary.purple} 0%, ${crystalColors.primary.teal} 100%)`,
        }}
      >
        <h2 className="text-xl md:text-2xl font-black mb-1">📦 Latest Inventory</h2>
        <p className="opacity-95 text-xs md:text-sm font-semibold">Real-time stock levels across all locations</p>
      </div>

      {/* Inventory Items */}
      <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
        {error ? (
          <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm font-medium">
            {error}
          </div>
        ) : inventory.length === 0 ? (
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-slate-600 text-sm font-medium">
            No inventory data available
          </div>
        ) : (
          inventory.map((item, idx) => (
            <div
              key={idx}
              className="p-4 rounded-xl border transition-all duration-300 hover:shadow-md hover:border-violet-300 cursor-pointer"
              style={{
                background: crystalColors.backgrounds.white,
                borderColor: crystalColors.borders.light,
              }}
            >
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="font-bold text-slate-900">{item.product_name}</h3>
                  <p className="text-xs text-slate-500">{item.company_name} • {item.port_name}</p>
                </div>
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold"
                  style={{ backgroundColor: crystalColors.primary.teal }}
                >
                  {item.physical_stock > 0 ? '✓' : '!'}
                </div>
              </div>

              {/* Key Metrics Grid */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <p className="text-slate-500">Physical Stock</p>
                  <p className="font-bold text-slate-900">
                    {item.physical_stock.toLocaleString('en-US', { maximumFractionDigits: 1 })}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500">Stock Value</p>
                  <p className="font-bold" style={{ color: crystalColors.primary.teal }}>
                    ₹{item.stock_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500">Market Price</p>
                  <p className="font-bold text-slate-900">
                    {item.current_market_price
                      ? `₹${Number(item.current_market_price).toLocaleString('en-US', { maximumFractionDigits: 2 })}`
                      : '-'}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500">Incoming</p>
                  <p className="font-bold text-slate-900">
                    {item.incoming_vessel_qty
                      ? Number(item.incoming_vessel_qty).toLocaleString('en-US', { maximumFractionDigits: 1 })
                      : '0'}
                  </p>
                </div>
              </div>

              {/* Status Bar */}
              <div className="mt-3 pt-3 border-t border-slate-100 flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full"
                    style={{
                      width: `${Math.min((item.physical_stock / (item.physical_stock + item.incoming_vessel_qty as number + 100)) * 100, 100)}%`,
                      background: `linear-gradient(90deg, ${crystalColors.primary.teal}, ${crystalColors.primary.cyan})`,
                    }}
                  />
                </div>
                <span className="text-xs font-semibold" style={{ color: crystalColors.primary.teal }}>
                  {item.total_sold_qty > 0
                    ? `${((item.total_sold_qty / (item.total_sold_qty + item.total_unsold_qty)) * 100).toFixed(0)}% Sold`
                    : 'New'}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Refresh Button */}
      <button
        onClick={fetchInventory}
        className="w-full py-3 rounded-xl font-semibold text-white transition-all duration-300 hover:shadow-lg transform hover:scale-105 flex items-center justify-center gap-2"
        style={{
          background: `linear-gradient(135deg, ${crystalColors.primary.purple} 0%, ${crystalColors.primary.cyan} 100%)`,
        }}
      >
        🔄 Refresh Data
      </button>
    </div>
  );
};

export default InventoryDetailsColumn;
