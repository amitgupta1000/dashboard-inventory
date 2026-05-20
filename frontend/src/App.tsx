import { useState, useEffect } from 'react';
import {
  Activity, RefreshCw, CheckCircle2, AlertCircle, Clock, Users,
  DollarSign, Award, FileText, ChevronRight, Search, Settings,
  Sparkles, Package, TrendingUp, BarChart3, Database, Zap
} from 'lucide-react';
import './styles/animations.css';

function App() {
  const [inventory, setInventory] = useState([]);
  const [summary, setSummary] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [narrative, setNarrative] = useState(null);
  const [loadingInventory, setLoadingInventory] = useState(false);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [toast, setToast] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [formData, setFormData] = useState(null);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const API_BASE_URL = 'http://localhost:8000';

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const fetchInventoryData = async () => {
    setLoadingInventory(true);
    try {
      const [invRes, sumRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/inventory`),
        fetch(`${API_BASE_URL}/api/inventory/summary`)
      ]);
      
      const invData = await invRes.json();
      const sumData = await sumRes.json();
      
      if (invData.success) {
        setInventory(invData.data.slice(0, 8)); // Top 8 items
        if (invData.data.length > 0 && !selectedProduct) {
          setSelectedProduct(invData.data[0]);
          initializeForm(invData.data[0]);
        }
      }
      
      if (sumData.success) {
        setSummary(sumData.summary);
      }
    } catch (e) {
      console.error(e);
      showToast('Failed to load inventory', 'error');
    } finally {
      setLoadingInventory(false);
    }
  };

  const fetchAnalyticsData = async () => {
    setLoadingAnalytics(true);
    try {
      const [alertsRes, narrativeRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/intelligence/alerts`),
        fetch(`${API_BASE_URL}/api/intelligence/narrative`)
      ]);
      
      const alertsData = await alertsRes.json();
      const narrativeData = await narrativeRes.json();
      
      if (alertsData.success) {
        setAlerts(alertsData.data.slice(0, 6)); // Top 6 alerts
      }
      
      if (narrativeData.success) {
        setNarrative(narrativeData.data);
      }
    } catch (e) {
      console.error(e);
      showToast('Failed to load analytics', 'error');
    } finally {
      setLoadingAnalytics(false);
    }
  };

  useEffect(() => {
    fetchInventoryData();
    fetchAnalyticsData();
  }, []);

  const initializeForm = (product) => {
    setFormData({
      product_name: product.product_name,
      market_price: product.current_market_price || 0,
      replacement_cost: product.replacement_cost || 0,
      duty_tariff_percent: 0,
      safety_stock_qty: 0,
      reorder_point_qty: 0,
      desired_inventory_days: 30,
      target_monthly_sales_volume: 0,
    });
  };

  const handleSaveSettings = async () => {
    if (!formData) return;
    setSaving(true);
    try {
      await fetch(`${API_BASE_URL}/api/product-settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      showToast('Settings saved successfully!');
    } catch (e) {
      console.error(e);
      showToast('Failed to save settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([fetchInventoryData(), fetchAnalyticsData()]);
    showToast('Dashboard synced');
    setRefreshing(false);
  };

  const filteredInventory = inventory.filter(item =>
    item.product_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.company_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getAlertColor = (type) => {
    switch (type?.toLowerCase()) {
      case 'critical':
      case 'shortage':
        return { bg: 'bg-rose-50', border: 'border-rose-200', text: 'text-rose-700', icon: AlertCircle };
      case 'warning':
      case 'aging':
        return { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', icon: Clock };
      case 'excess':
        return { bg: 'bg-sky-50', border: 'border-sky-200', text: 'text-sky-700', icon: TrendingUp };
      default:
        return { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', icon: CheckCircle2 };
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-slate-50 select-none overflow-hidden text-slate-800">
      
      {/* Toast Alert */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 animate-fade-in flex items-center gap-3 px-4 py-3 rounded-xl border bg-white shadow-xl border-slate-200">
          <span className={`w-2 h-2 rounded-full ${toast.type === 'success' ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
          <span className="text-xs font-semibold text-slate-700">{toast.message}</span>
        </div>
      )}

      {/* Compact Header */}
      <header className="h-16 bg-white border-b border-slate-200/80 px-6 flex justify-between items-center shrink-0 shadow-sm z-20">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center border border-purple-200">
            <Package className="w-4 h-4 text-purple-600" strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="text-base font-extrabold text-slate-900 tracking-tight">Sumairo Inventory Dashboard</h1>
            <p className="text-[10px] text-slate-500 font-medium">Real-time inventory intelligence and management</p>
          </div>
        </div>

        {/* Global Stats */}
        <div className="hidden md:flex items-center gap-6 text-xs border-l border-slate-200 pl-6 h-8">
          {summary && (
            <>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Products:</span>
                <span className="px-2 py-0.5 rounded-full bg-purple-50 border border-purple-200 text-purple-700 font-bold text-[10px]">
                  {summary.total_products}
                </span>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Stock Value:</span>
                <span className="px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 font-bold text-[10px]">
                  ₹{(summary.total_stock_value / 1000000).toFixed(1)}M
                </span>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Alerts:</span>
                <span className={`px-2 py-0.5 rounded-full ${alerts.length > 0 ? 'bg-rose-50 border border-rose-200 text-rose-700' : 'bg-emerald-50 border border-emerald-200 text-emerald-700'} font-bold text-[10px]`}>
                  {alerts.length}
                </span>
              </div>
            </>
          )}

          <button 
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-500 shrink-0 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </header>

      {/* Main 3-Column Layout */}
      <main className="flex-1 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 p-5 min-h-0 overflow-hidden">
        
        {/* ==========================================
            COLUMN 1: INVENTORY CONFIGURATOR
            ========================================== */}
        <section className="flex flex-col h-full bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm min-h-0 overflow-hidden">
          {/* Header */}
          <div className="shrink-0 mb-3 border-b border-slate-100 pb-2">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-purple-500"></span>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">1. Inventory Configurator</h2>
            </div>
            <p className="text-[10px] text-slate-500 mt-0.5">Set commodity-wise parameters and pricing.</p>
          </div>

          <div className="flex-1 flex flex-col justify-between min-h-0 space-y-4">
            
            {/* Search Inventory */}
            <div className="shrink-0 space-y-2">
              <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">Select Product</span>
              <div className="relative">
                <Search className="w-3 h-3 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input 
                  type="text"
                  placeholder="Search by product or company..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-2 text-[10px] text-slate-700 focus:outline-none focus:ring-1 focus:ring-purple-400 w-full"
                />
              </div>
            </div>

            {/* Inventory List */}
            <div className="flex-1 flex flex-col min-h-0 space-y-2">
              <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">Inventory Items ({filteredInventory.length})</span>
              
              <div className="flex-1 overflow-y-auto border border-slate-100 rounded-xl p-1.5 space-y-1.5 bg-slate-50/50 custom-scrollbar">
                {loadingInventory ? (
                  <div className="text-center py-8 text-[11px] text-slate-400">Loading...</div>
                ) : filteredInventory.map((item, idx) => (
                  <div 
                    key={idx}
                    onClick={() => {
                      setSelectedProduct(item);
                      initializeForm(item);
                    }}
                    className={`p-2.5 rounded-lg border cursor-pointer transition-all duration-200 ${
                      selectedProduct?.product_name === item.product_name
                        ? 'bg-purple-50/80 border-purple-300'
                        : 'bg-white border-slate-100/80 hover:border-slate-250'
                    }`}
                  >
                    <div className="flex justify-between items-start gap-2">
                      <div className="min-w-0 flex-1">
                        <span className="font-bold text-[10px] text-slate-900 block truncate">{item.product_name}</span>
                        <p className="text-[8px] text-slate-500 truncate">{item.company_name} • {item.port_name}</p>
                      </div>
                      <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded shrink-0 ${
                        item.physical_stock > 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                      }`}>
                        {item.physical_stock.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Configuration Form */}
            {selectedProduct && formData && (
              <div className="shrink-0 space-y-3 border-t border-slate-100 pt-3">
                <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">Edit Settings</span>
                
                <div className="grid grid-cols-2 gap-2">
                  <input 
                    type="number"
                    placeholder="Market Price"
                    value={formData.market_price}
                    onChange={(e) => setFormData({...formData, market_price: Number(e.target.value)})}
                    className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px] text-slate-800 focus:outline-none focus:ring-1 focus:ring-purple-400"
                  />
                  <input 
                    type="number"
                    placeholder="Replacement Cost"
                    value={formData.replacement_cost}
                    onChange={(e) => setFormData({...formData, replacement_cost: Number(e.target.value)})}
                    className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px] text-slate-800 focus:outline-none focus:ring-1 focus:ring-purple-400"
                  />
                  <input 
                    type="number"
                    placeholder="Duty/Tariff %"
                    value={formData.duty_tariff_percent}
                    onChange={(e) => setFormData({...formData, duty_tariff_percent: Number(e.target.value)})}
                    className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px] text-slate-800 focus:outline-none focus:ring-1 focus:ring-purple-400"
                  />
                  <input 
                    type="number"
                    placeholder="Safety Stock"
                    value={formData.safety_stock_qty}
                    onChange={(e) => setFormData({...formData, safety_stock_qty: Number(e.target.value)})}
                    className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px] text-slate-800 focus:outline-none focus:ring-1 focus:ring-purple-400"
                  />
                </div>
              </div>
            )}

            {/* Save Button */}
            <button 
              onClick={handleSaveSettings}
              disabled={saving || !formData}
              className="shrink-0 w-full py-2.5 bg-purple-600 hover:bg-purple-750 text-white rounded-xl font-bold text-xs shadow-md shadow-purple-600/10 cursor-pointer flex items-center justify-center gap-2 active:scale-[0.98] transition-transform disabled:opacity-50"
            >
              {saving ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Settings className="w-3.5 h-3.5" />
                  Save Settings
                </>
              )}
            </button>
          </div>
        </section>

        {/* ==========================================
            COLUMN 2: INVENTORY MONITOR & ANALYTICS
            ========================================== */}
        <section className="flex flex-col h-full bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm min-h-0 overflow-hidden">
          {/* Header */}
          <div className="shrink-0 mb-3 border-b border-slate-100 pb-2">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-500"></span>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">2. Analytics & Monitor</h2>
            </div>
            <p className="text-[10px] text-slate-500 mt-0.5">Summary metrics and real-time health status.</p>
          </div>

          <div className="flex-1 flex flex-col justify-between min-h-0 space-y-4">
            
            {/* Summary Stats Grid */}
            {summary && (
              <div className="shrink-0 grid grid-cols-2 gap-2">
                <div className="bg-slate-50 border border-slate-100 p-2.5 rounded-lg">
                  <span className="text-[8px] font-bold text-slate-400 uppercase block">Products</span>
                  <span className="text-base font-extrabold text-slate-900">{summary.total_products}</span>
                </div>
                <div className="bg-slate-50 border border-slate-100 p-2.5 rounded-lg">
                  <span className="text-[8px] font-bold text-slate-400 uppercase block">Physical Stock</span>
                  <span className="text-base font-extrabold text-slate-900">{(summary.total_physical_stock / 1000).toFixed(0)}K</span>
                </div>
                <div className="bg-slate-50 border border-slate-100 p-2.5 rounded-lg">
                  <span className="text-[8px] font-bold text-slate-400 uppercase block">Sold Qty</span>
                  <span className="text-base font-extrabold text-emerald-600">{(summary.total_sold_qty / 1000).toFixed(0)}K</span>
                </div>
                <div className="bg-slate-50 border border-slate-100 p-2.5 rounded-lg">
                  <span className="text-[8px] font-bold text-slate-400 uppercase block">Stock Value</span>
                  <span className="text-sm font-extrabold text-purple-600">₹{(summary.total_stock_value / 10000000).toFixed(1)}Cr</span>
                </div>
              </div>
            )}

            {/* Health Status */}
            {narrative && (
              <div className="shrink-0 bg-slate-50/60 border border-slate-100 p-3 rounded-xl space-y-2">
                <span className="block text-[9px] font-bold text-slate-400 uppercase tracking-widest">Overall Health</span>
                <div className="flex items-center justify-between">
                  <span className={`text-xs font-extrabold ${
                    narrative.overall_health === 'HEALTHY' ? 'text-emerald-600' :
                    narrative.overall_health === 'CRITICAL' ? 'text-rose-600' : 'text-amber-600'
                  }`}>
                    {narrative.overall_health}
                  </span>
                  <div className="flex gap-2 text-[8px]">
                    <span className="px-1.5 py-0.5 rounded bg-rose-100 text-rose-700 font-bold">Critical: {narrative.critical_count}</span>
                    <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-bold">Warning: {narrative.warning_count}</span>
                    <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 font-bold">Normal: {narrative.normal_count}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Alerts List */}
            <div className="flex-1 flex flex-col min-h-0 space-y-2">
              <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">⚠️ Top Alerts ({alerts.length})</span>
              
              <div className="flex-1 overflow-y-auto border border-slate-100 rounded-xl p-2 space-y-1.5 bg-slate-50/50 custom-scrollbar">
                {loadingAnalytics ? (
                  <div className="text-center py-8 text-[11px] text-slate-400">Loading...</div>
                ) : alerts.length === 0 ? (
                  <div className="text-center py-4 text-[10px] text-emerald-600 font-semibold">✓ No critical alerts</div>
                ) : alerts.map((alert, idx) => {
                  const colors = getAlertColor(alert.alert_type);
                  const IconComponent = colors.icon;
                  return (
                    <div 
                      key={idx}
                      className={`p-2 rounded-lg border ${colors.bg} ${colors.border} flex gap-2`}
                    >
                      <IconComponent className={`w-3.5 h-3.5 ${colors.text} flex-shrink-0 mt-0.5`} />
                      <div className="min-w-0 flex-1">
                        <p className={`font-bold text-[9px] ${colors.text} truncate`}>{alert.item}</p>
                        <p className={`text-[8px] ${colors.text} opacity-80 line-clamp-2`}>{alert.alert_message}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        {/* ==========================================
            COLUMN 3: INTELLIGENCE INSIGHTS
            ========================================== */}
        <section className="flex flex-col h-full bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm min-h-0 overflow-hidden">
          {/* Header */}
          <div className="shrink-0 mb-3 border-b border-slate-100 pb-2">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">3. Intelligence Insights</h2>
            </div>
            <p className="text-[10px] text-slate-500 mt-0.5">Key metrics and operational recommendations.</p>
          </div>

          <div className="flex-1 flex flex-col justify-between min-h-0 space-y-4">
            
            {/* Selected Product Details */}
            {selectedProduct && (
              <div className="shrink-0 space-y-2">
                <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">Active Product</span>
                <div className="bg-slate-50 border border-slate-100 p-3 rounded-lg space-y-1.5">
                  <div>
                    <p className="text-[8px] font-bold text-slate-400 uppercase">Product</p>
                    <p className="text-[10px] font-bold text-slate-900">{selectedProduct.product_name}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="text-[8px] font-bold text-slate-400 uppercase">Physical Stock</p>
                      <p className="text-xs font-bold text-slate-900">{selectedProduct.physical_stock.toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                    </div>
                    <div>
                      <p className="text-[8px] font-bold text-slate-400 uppercase">Stock Value</p>
                      <p className="text-xs font-bold text-emerald-600">₹{selectedProduct.stock_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="text-[8px] font-bold text-slate-400 uppercase">Market Price</p>
                      <p className="text-xs font-bold text-slate-900">₹{Number(selectedProduct.current_market_price).toLocaleString('en-US', { maximumFractionDigits: 2 })}</p>
                    </div>
                    <div>
                      <p className="text-[8px] font-bold text-slate-400 uppercase">Incoming</p>
                      <p className="text-xs font-bold text-purple-600">{Number(selectedProduct.incoming_vessel_qty || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Key Insights */}
            {narrative && (
              <div className="flex-1 flex flex-col min-h-0 space-y-2">
                <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">Executive Summary</span>
                
                <div className="flex-1 overflow-y-auto border border-slate-100 rounded-xl p-2.5 bg-slate-50/50 custom-scrollbar">
                  <p className="text-[9px] leading-relaxed text-slate-700">{narrative.executive_summary}</p>
                  
                  {narrative.recommended_actions && narrative.recommended_actions.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-100 space-y-1.5">
                      <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Recommendations</p>
                      {narrative.recommended_actions.slice(0, 4).map((action, idx) => (
                        <div key={idx} className="flex gap-2 text-[8px]">
                          <Zap className="w-2.5 h-2.5 text-amber-500 flex-shrink-0 mt-0.5" />
                          <span className="text-slate-700">{action}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Refresh Insights */}
            <button 
              onClick={fetchAnalyticsData}
              className="shrink-0 w-full py-2.5 bg-emerald-600 hover:bg-emerald-750 text-white rounded-xl font-bold text-xs shadow-md shadow-emerald-600/10 cursor-pointer flex items-center justify-center gap-2 active:scale-[0.98] transition-transform"
            >
              <Zap className="w-3.5 h-3.5" />
              Regenerate Insights
            </button>
          </div>
        </section>

      </main>
    </div>
  );
}

export default App;
