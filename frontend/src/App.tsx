import { useState, useEffect } from 'react';
import {
  Activity, RefreshCw, CheckCircle2, AlertCircle, Clock, Users,
  DollarSign, Award, FileText, ChevronRight, Search, Settings,
  Sparkles, Package, TrendingUp, BarChart3, Database, Zap, Lock, X, ChevronLeft, Upload
} from 'lucide-react';
import './styles/animations.css';
import UploadPanel from './components/UploadPanel';

function App() {
  const [inventory, setInventory] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [narrative, setNarrative] = useState<any>(null);
  const [loadingInventory, setLoadingInventory] = useState(false);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<any>(null);
  const [toast, setToast] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [formData, setFormData] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [uploadPanelOpen, setUploadPanelOpen] = useState(false);
  const [asOfDate, setAsOfDate] = useState('');
  const [backdate, setBackdate] = useState('');
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [drilldownRows, setDrilldownRows] = useState<any[]>([]);
  const [loadingDrilldown, setLoadingDrilldown] = useState(false);

  const API_BASE_URL = 'http://localhost:8000';

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const buildDateQuery = () => {
    const params = new URLSearchParams();
    if (asOfDate) params.set('as_of', asOfDate);
    if (backdate) params.set('backdate', backdate);
    return params.toString();
  };

  const fetchDrilldown = async (product: any = selectedProduct, asOfParam = asOfDate, backdateParam = backdate) => {
    if (!product?.product_name || !product?.port_name || !product?.company_name) {
      setDrilldownRows([]);
      return;
    }

    setLoadingDrilldown(true);
    try {
      const params = new URLSearchParams({
        product_name: product.product_name,
        port_name: product.port_name,
        company_name: product.company_name,
      });
      if (asOfParam) params.set('as_of', asOfParam);
      if (backdateParam) params.set('backdate', backdateParam);

      const response = await fetch(`${API_BASE_URL}/api/stock-analytics/drilldown?${params.toString()}`);
      const data = await response.json();
      if (data.success) {
        setDrilldownRows(data.data || []);
      }
    } catch (e) {
      console.error(e);
      setDrilldownRows([]);
    } finally {
      setLoadingDrilldown(false);
    }
  };

  const fetchInventoryData = async () => {
    setLoadingInventory(true);
    try {
      const query = buildDateQuery();
      const endpoint = query
        ? `${API_BASE_URL}/api/stock-analytics/summary?${query}`
        : `${API_BASE_URL}/api/stock-analytics/summary`;

      const invRes = await fetch(endpoint);
      const invData = await invRes.json();
      
      if (invData.success) {
        const rows = invData.data || [];
        setInventory(rows);
        setSummary(invData.summary || null);
        setAvailableDates(invData.available_dates || []);

        if (invData.as_of_date && !asOfDate) setAsOfDate(invData.as_of_date);
        if (invData.backdate && !backdate) setBackdate(invData.backdate);

        if (rows.length > 0) {
          const nextSelected = selectedProduct
            ? rows.find((r: any) =>
                r.product_name === selectedProduct.product_name
                && r.port_name === selectedProduct.port_name
                && r.company_name === selectedProduct.company_name
              ) || rows[0]
            : rows[0];

          setSelectedProduct(nextSelected);
          initializeForm(nextSelected);
          await fetchDrilldown(nextSelected, invData.as_of_date || asOfDate, invData.backdate || backdate);
        }
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
      const query = buildDateQuery();
      const alertsUrl = query
        ? `${API_BASE_URL}/api/intelligence/alerts?${query}`
        : `${API_BASE_URL}/api/intelligence/alerts`;
      const narrativeUrl = query
        ? `${API_BASE_URL}/api/intelligence/narrative?${query}`
        : `${API_BASE_URL}/api/intelligence/narrative`;

      const [alertsRes, narrativeRes] = await Promise.all([
        fetch(alertsUrl),
        fetch(narrativeUrl)
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

  const initializeForm = (product: any) => {
    setFormData({
      product_name: product.product_name,
      market_price: product.average_selling_price_inr || 0,
      replacement_cost: product.cost_price_inr || 0,
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

  const filteredInventory = inventory.filter((item: any) =>
    (item.product_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (item.port_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (item.company_name || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getAlertColor = (type: string) => {
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
    <div className="h-screen w-screen flex flex-col bg-gradient-to-b from-slate-50 via-purple-50/30 to-slate-50 select-none overflow-hidden text-slate-800">
      
      
      {/* Toast Alert */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 animate-fade-in flex items-center gap-3 px-4 py-3 rounded-xl border bg-white shadow-lg border-slate-200">
          <span className={`w-2 h-2 rounded-full ${toast.type === 'success' ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
          <span className="text-xs font-semibold text-slate-700">{toast.message}</span>
        </div>
      )}

      {/* Premium Header */}
      <header className="h-16 bg-white/80 backdrop-blur-sm border-b border-slate-200/40 px-6 flex justify-between items-center shrink-0 shadow-sm z-20">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-gradient-to-br from-purple-300 to-purple-400 rounded-xl flex items-center justify-center border border-purple-200/60 shadow-md">
            <Package className="w-5 h-5 text-white" strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="text-[28px] font- text-violet-600 font-large ">Sumairo Inventory Console</h1>
            <p className="text-[11px] text-slate-500 font-medium">Automated inventory intelligence & optimization</p>
          </div>
        </div>

        {/* Global Stats */}
        <div className="hidden md:flex items-center gap-5 text-xs border-l border-slate-200/40 pl-6 h-8">
          {summary && (
            <>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">INVENTORY:</span>
                <span className="px-2.5 py-0.5 rounded-full bg-gradient-to-r from-purple-100 to-purple-50 border border-purple-200/60 text-purple-700 font-bold text-[10px]">
                  {summary.total_products}
                </span>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">VALUE:</span>
                <span className="px-2.5 py-0.5 rounded-full bg-gradient-to-r from-emerald-100 to-emerald-50 border border-emerald-200/60 text-emerald-700 font-bold text-[10px]">
                  ₹{(summary.total_stock_value / 1000000).toFixed(1)}M
                </span>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">ALERTS:</span>
                <span className={`px-2.5 py-0.5 rounded-full font-bold text-[10px] border ${alerts.length > 0 ? 'bg-gradient-to-r from-rose-100 to-rose-50 border-rose-200/60 text-rose-700' : 'bg-gradient-to-r from-emerald-100 to-emerald-50 border-emerald-200/60 text-emerald-700'}`}>
                  {alerts.length}
                </span>
              </div>
            </>
          )}

          <button 
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-1.5 rounded-lg border border-slate-200/40 hover:bg-slate-100/50 text-slate-500 hover:text-slate-600 shrink-0 transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => setUploadPanelOpen(true)}
            className="p-1.5 rounded-lg border border-blue-300/60 bg-blue-50 text-blue-600 hover:bg-blue-100 shrink-0 transition-all"
            title="Open Upload Panel"
          >
            <Upload className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      {/* Main 2-Column Layout */}
      <main className="flex-1 w-full flex gap-4 p-4 min-h-0 overflow-hidden">

        {/* ==========================================
            COLUMN 1: INVENTORY MONITOR & ANALYTICS
            ========================================== */}
        <section className="flex flex-col flex-[2] min-w-0 h-full bg-gradient-to-br from-white to-cyan-50/30 rounded-2xl border border-cyan-200/40 shadow-lg hover:shadow-xl transition-all duration-300 min-h-0 overflow-hidden">
          {/* Header */}
          <div className="shrink-0 px-5 pt-5 pb-4 border-b border-cyan-100/50">
            <div className="flex items-center gap-2.5 mb-2">
              <span className="w-3 h-3 rounded-full bg-gradient-to-br from-cyan-400 to-cyan-500 shadow-md"></span>
              <h2 className="text-sm font-extrabold uppercase tracking-widest text-slate-900">1. Analytics & Monitor</h2>
            </div>
            <p className="text-[11px] text-slate-600 font-medium">Track metrics and monitor inventory health status.</p>
          </div>
          
          <div className="flex-1 flex flex-col justify-between min-h-0 px-5 py-4 space-y-4">
            
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

            {/* Date Filters */}
            <div className="shrink-0 grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <label className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">As Of</label>
                <select
                  value={asOfDate}
                  onChange={(e) => setAsOfDate(e.target.value)}
                  className="w-full text-[10px] px-2 py-1.5 rounded-md border border-slate-200 bg-white"
                >
                  {(availableDates || []).map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Compare To</label>
                <select
                  value={backdate}
                  onChange={(e) => setBackdate(e.target.value)}
                  className="w-full text-[10px] px-2 py-1.5 rounded-md border border-slate-200 bg-white"
                >
                  <option value="">None</option>
                  {(availableDates || []).filter((d) => d !== asOfDate).map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
            </div>

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

            {/* Grouped Stock Summary */}
            <div className="flex-1 flex flex-col min-h-0 space-y-2">
              <div className="flex items-center justify-between">
                <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">Stock Summary (Product + Port + Company)</span>
                <button
                  onClick={handleRefresh}
                  className="text-[9px] px-2 py-1 rounded-md border border-cyan-200 text-cyan-700 hover:bg-cyan-50"
                >
                  Apply
                </button>
              </div>

              <div className="shrink-0">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search product, port, company"
                  className="w-full text-[10px] px-2 py-1.5 rounded-md border border-slate-200 bg-white"
                />
              </div>
              
              <div className="flex-1 overflow-y-auto border border-slate-100 rounded-xl p-2 space-y-1.5 bg-slate-50/50 custom-scrollbar">
                {loadingInventory ? (
                  <div className="text-center py-8 text-[11px] text-slate-400">Loading...</div>
                ) : filteredInventory.length === 0 ? (
                  <div className="text-center py-4 text-[10px] text-slate-500 font-semibold">No rows for selected filters</div>
                ) : filteredInventory.slice(0, 30).map((row, idx) => {
                  const colors = getAlertColor(row.alert_level);
                  const IconComponent = colors.icon;
                  return (
                    <div 
                      key={idx}
                      onClick={() => {
                        setSelectedProduct(row);
                        fetchDrilldown(row);
                      }}
                      className={`p-2 rounded-lg border ${colors.bg} ${colors.border} flex gap-2`}
                    >
                      <IconComponent className={`w-3.5 h-3.5 ${colors.text} flex-shrink-0 mt-0.5`} />
                      <div className="min-w-0 flex-1">
                        <p className={`font-bold text-[9px] ${colors.text} truncate`}>{row.product_name}</p>
                        <p className={`text-[8px] ${colors.text} opacity-80 truncate`}>{row.port_name} • {row.company_name}</p>
                        <div className="grid grid-cols-3 gap-2 mt-1 text-[8px] opacity-90">
                          <span>Stock: {Number(row.physical_stock || 0).toFixed(0)}</span>
                          <span>Δ: {Number(row.delta_physical_stock || 0).toFixed(0)}</span>
                          <span>Margin: ₹{Number(row.margin_per_mt_inr || 0).toFixed(0)}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        {/* ==========================================
            COLUMN 2: INTELLIGENCE INSIGHTS
            ========================================== */}
        <section className="flex flex-col flex-[1] min-w-0 h-full bg-gradient-to-br from-white to-emerald-50/30 rounded-2xl border border-emerald-200/40 shadow-lg hover:shadow-xl transition-all duration-300 min-h-0 overflow-hidden">
          {/* Header */}
          <div className="shrink-0 px-5 pt-5 pb-4 border-b border-emerald-100/50">
            <div className="flex items-center gap-2.5 mb-2">
              <span className="w-3 h-3 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-500 shadow-md"></span>
              <h2 className="text-sm font-extrabold uppercase tracking-widest text-slate-900">2. Intelligence Insights</h2>
            </div>
            <p className="text-[11px] text-slate-600 font-medium">AI-powered analytics and operational recommendations.</p>
          </div>
          
          <div className="flex-1 flex flex-col justify-between min-h-0 px-5 py-4 space-y-4">
            
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
                      <p className="text-xs font-bold text-emerald-600">₹{Number(selectedProduct.stock_value || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="text-[8px] font-bold text-slate-400 uppercase">Avg Selling/MT</p>
                      <p className="text-xs font-bold text-slate-900">₹{Number(selectedProduct.average_selling_price_inr || 0).toLocaleString('en-US', { maximumFractionDigits: 2 })}</p>
                    </div>
                    <div>
                      <p className="text-[8px] font-bold text-slate-400 uppercase">Cost/MT</p>
                      <p className="text-xs font-bold text-purple-600">₹{Number(selectedProduct.cost_price_inr || 0).toLocaleString('en-US', { maximumFractionDigits: 2 })}</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="text-[8px] font-bold text-slate-400 uppercase">Margin/MT</p>
                      <p className={`text-xs font-bold ${Number(selectedProduct.margin_per_mt_inr || 0) < 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                        ₹{Number(selectedProduct.margin_per_mt_inr || 0).toLocaleString('en-US', { maximumFractionDigits: 2 })}
                      </p>
                    </div>
                    <div>
                      <p className="text-[8px] font-bold text-slate-400 uppercase">Vessels</p>
                      <p className="text-xs font-bold text-slate-900">{Number(selectedProduct.vessel_count || 0)}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Drilldown */}
            {selectedProduct && (
              <div className="shrink-0 space-y-2">
                <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">Drill-down by Vessel</span>
                <div className="max-h-40 overflow-y-auto border border-slate-100 rounded-xl p-2 bg-slate-50/50 custom-scrollbar space-y-1.5">
                  {loadingDrilldown ? (
                    <div className="text-center py-3 text-[10px] text-slate-400">Loading drill-down...</div>
                  ) : drilldownRows.length === 0 ? (
                    <div className="text-center py-3 text-[10px] text-slate-400">No vessel rows</div>
                  ) : drilldownRows.slice(0, 12).map((v, idx) => (
                    <div key={idx} className="p-2 bg-white border border-slate-100 rounded-lg">
                      <p className="text-[9px] font-bold text-slate-800 truncate">{v.vessel_name}</p>
                      <p className="text-[8px] text-slate-500">{v.vessel_date || 'NA'} • {v.terminal || 'NA'}</p>
                      <div className="grid grid-cols-3 gap-2 mt-1 text-[8px] text-slate-700">
                        <span>Stock: {Number(v.physical_stock || 0).toFixed(0)}</span>
                        <span>Δ: {Number(v.delta_physical_stock || 0).toFixed(0)}</span>
                        <span>Margin: ₹{Number(v.margin_per_mt_inr || 0).toFixed(0)}</span>
                      </div>
                    </div>
                  ))}
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
                      {narrative.recommended_actions.slice(0, 4).map((action: string, idx: number) => (
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

            {/* Footer Action Button */}
            <button 
              onClick={fetchAnalyticsData}
              className="shrink-0 w-full mt-4 py-3 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white font-bold text-sm rounded-xl shadow-lg shadow-emerald-500/20 hover:shadow-xl hover:shadow-emerald-500/30 cursor-pointer flex items-center justify-center gap-2 active:scale-95 transition-all border border-emerald-400/30"
            >
              <Zap className="w-4 h-4" />
              Regenerate Insights
            </button>
          </div>
        </section>

      </main>

      {/* Upload Panel Sidebar */}
      <UploadPanel 
        isOpen={uploadPanelOpen}
        onClose={() => setUploadPanelOpen(false)}
        onUploadSuccess={(type) => {
          showToast(`${type} file uploaded successfully!`);
          // Optionally refresh data here
        }}
      />
      
      {/* Footer */}
      <footer className="h-10 bg-white/50 backdrop-blur-sm border-t border-slate-200/40 px-6 flex items-center justify-between text-[10px] text-slate-500 shrink-0">
        <div className="flex items-center gap-4">
          <span className="font-medium">Database Status: <span className="text-emerald-600 font-bold">● Connected</span></span>
          <span className="text-slate-300">•</span>
          <span>Version 2.1.0</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-400">Powered by</span>
          <span className="font-bold text-slate-700">Sumairo Intelligence</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
