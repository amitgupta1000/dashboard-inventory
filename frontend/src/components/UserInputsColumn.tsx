import { useEffect, useState } from 'react';
import axios from 'axios';
import { crystalColors } from '../styles/crystalColors';

interface CommodityInput {
  product_name: string;
  market_price: number;
  replacement_cost: number;
  duty_tariff_percent: number;
  safety_stock_qty: number;
  reorder_point_qty: number;
  desired_inventory_days: number;
  target_monthly_sales_volume: number;
  id?: string;
}

const API_BASE_URL = 'http://localhost:8000';

const UserInputsColumn: React.FC = () => {
  const [commodities, setCommodities] = useState<CommodityInput[]>([]);
  const [selectedCommodity, setSelectedCommodity] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [formData, setFormData] = useState<CommodityInput | null>(null);

  useEffect(() => {
    fetchCommodities();
  }, []);

  const fetchCommodities = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API_BASE_URL}/api/inventory`);
      if (res.data.success) {
        // Get unique products with initial values
        const uniqueProducts = Array.from(
          new Map(res.data.data.map((item: any) => [item.product_name, item])).values()
        );
        
        const commodityData = uniqueProducts.map((product: any) => ({
          product_name: product.product_name,
          market_price: product.current_market_price || 0,
          replacement_cost: product.replacement_cost || 0,
          duty_tariff_percent: 0,
          safety_stock_qty: 0,
          reorder_point_qty: 0,
          desired_inventory_days: 30,
          target_monthly_sales_volume: 0,
        }));

        setCommodities(commodityData);
        if (commodityData.length > 0) {
          setSelectedCommodity(0);
          setFormData(commodityData[0]);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch commodities');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field: keyof CommodityInput, value: any) => {
    if (formData) {
      const updated = {
        ...formData,
        [field]: field === 'product_name' ? value : Number(value) || 0,
      };
      setFormData(updated);
      
      // Update the commodities array
      if (selectedCommodity !== null) {
        const newCommodities = [...commodities];
        newCommodities[selectedCommodity] = updated;
        setCommodities(newCommodities);
      }
    }
  };

  const handleSave = async () => {
    if (!formData) return;
    
    try {
      setSaving(true);
      setError(null);
      
      // In a real app, you would send this to the backend
      // For now, we'll just show a success message
      await axios.post(`${API_BASE_URL}/api/product-settings`, formData);
      
      setSuccessMessage('Settings saved successfully!');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="text-4xl mb-3">⚙️</div>
          <p className="text-slate-600 font-semibold">Loading commodities...</p>
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
          background: `linear-gradient(135deg, ${crystalColors.primary.purple} 0%, ${crystalColors.primary.cyan} 100%)`,
        }}
      >
        <h2 className="text-2xl font-bold mb-2">⚙️ Configuration</h2>
        <p className="opacity-90 text-sm">Set commodity-wise parameters and pricing</p>
      </div>

      {/* Commodity Selector */}
      <div>
        <label className="block text-sm font-bold text-slate-900 mb-3">SELECT COMMODITY</label>
        <div className="grid grid-cols-1 gap-2 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
          {commodities.map((commodity, idx) => (
            <button
              key={idx}
              onClick={() => {
                setSelectedCommodity(idx);
                setFormData(commodity);
              }}
              className={`p-3 rounded-lg text-left transition-all duration-300 font-semibold text-sm ${
                selectedCommodity === idx
                  ? 'text-white shadow-md transform scale-105'
                  : 'text-slate-700 hover:bg-slate-100 border border-slate-200'
              }`}
              style={{
                background:
                  selectedCommodity === idx
                    ? `linear-gradient(135deg, ${crystalColors.primary.purple} 0%, ${crystalColors.primary.cyan} 100%)`
                    : crystalColors.backgrounds.white,
              }}
            >
              {commodity.product_name}
            </button>
          ))}
        </div>
      </div>

      {/* Form */}
      {formData && (
        <div className="space-y-4 flex-1 overflow-y-auto pr-2 custom-scrollbar">
          {/* Messages */}
          {error && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm font-medium">
              {error}
            </div>
          )}
          {successMessage && (
            <div className="p-3 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm font-medium">
              ✓ {successMessage}
            </div>
          )}

          {/* Product Name */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-2">PRODUCT</label>
            <input
              type="text"
              value={formData.product_name}
              disabled
              className="w-full px-3 py-2 rounded-lg border bg-slate-50 text-slate-700 font-semibold text-sm"
              style={{ borderColor: crystalColors.borders.light }}
            />
          </div>

          {/* Market Price */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-2">💰 MARKET PRICE (₹)</label>
            <input
              type="number"
              value={formData.market_price}
              onChange={(e) => handleInputChange('market_price', e.target.value)}
              className="w-full px-3 py-2 rounded-lg border focus:outline-none focus:ring-2 transition-all text-sm"
              style={{
                borderColor: crystalColors.borders.light,
                focusRing: `2px solid ${crystalColors.primary.teal}`,
              }}
              placeholder="Enter market price"
            />
          </div>

          {/* Replacement Cost */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-2">🔄 REPLACEMENT COST (₹)</label>
            <input
              type="number"
              value={formData.replacement_cost}
              onChange={(e) => handleInputChange('replacement_cost', e.target.value)}
              className="w-full px-3 py-2 rounded-lg border focus:outline-none focus:ring-2 transition-all text-sm"
              style={{ borderColor: crystalColors.borders.light }}
              placeholder="Enter replacement cost"
            />
          </div>

          {/* Duty/Tariff */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-2">📋 DUTY/TARIFF (%)</label>
            <input
              type="number"
              value={formData.duty_tariff_percent}
              onChange={(e) => handleInputChange('duty_tariff_percent', e.target.value)}
              className="w-full px-3 py-2 rounded-lg border focus:outline-none focus:ring-2 transition-all text-sm"
              style={{ borderColor: crystalColors.borders.light }}
              placeholder="Enter duty/tariff percentage"
              min="0"
              max="100"
            />
          </div>

          {/* Safety Stock */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-2">🛡️ SAFETY STOCK (units)</label>
            <input
              type="number"
              value={formData.safety_stock_qty}
              onChange={(e) => handleInputChange('safety_stock_qty', e.target.value)}
              className="w-full px-3 py-2 rounded-lg border focus:outline-none focus:ring-2 transition-all text-sm"
              style={{ borderColor: crystalColors.borders.light }}
              placeholder="Enter minimum safety stock"
            />
          </div>

          {/* Reorder Point */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-2">📍 REORDER POINT (units)</label>
            <input
              type="number"
              value={formData.reorder_point_qty}
              onChange={(e) => handleInputChange('reorder_point_qty', e.target.value)}
              className="w-full px-3 py-2 rounded-lg border focus:outline-none focus:ring-2 transition-all text-sm"
              style={{ borderColor: crystalColors.borders.light }}
              placeholder="Enter reorder point"
            />
          </div>

          {/* Desired Inventory Days */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-2">📅 DESIRED INVENTORY DAYS</label>
            <input
              type="number"
              value={formData.desired_inventory_days}
              onChange={(e) => handleInputChange('desired_inventory_days', e.target.value)}
              className="w-full px-3 py-2 rounded-lg border focus:outline-none focus:ring-2 transition-all text-sm"
              style={{ borderColor: crystalColors.borders.light }}
              placeholder="Enter desired inventory days"
            />
          </div>

          {/* Target Monthly Sales */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-2">📊 TARGET MONTHLY SALES (units)</label>
            <input
              type="number"
              value={formData.target_monthly_sales_volume}
              onChange={(e) => handleInputChange('target_monthly_sales_volume', e.target.value)}
              className="w-full px-3 py-2 rounded-lg border focus:outline-none focus:ring-2 transition-all text-sm"
              style={{ borderColor: crystalColors.borders.light }}
              placeholder="Enter target monthly sales volume"
            />
          </div>
        </div>
      )}

      {/* Save Button */}
      <button
        onClick={handleSave}
        disabled={saving}
        className="w-full py-3 rounded-xl font-bold text-white transition-all duration-300 hover:shadow-lg transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
        style={{
          background: `linear-gradient(135deg, ${crystalColors.primary.purple} 0%, ${crystalColors.primary.teal} 100%)`,
        }}
      >
        {saving ? '💾 Saving...' : '💾 Save Settings'}
      </button>
    </div>
  );
};

export default UserInputsColumn;
