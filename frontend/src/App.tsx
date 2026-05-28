import { useState, useEffect } from 'react';
import {
  Package, Sparkles, Zap, RefreshCw, Upload, X
} from 'lucide-react';
import './styles/animations.css';
import UploadPanel from './components/UploadPanel';

function App() {
  // Layer 1 Analytics: Tab-based exploration
  const [activeAnalyticsTab, setActiveAnalyticsTab] = useState<'inventory' | 'summary'>('inventory');
  const [summaryViewType, setSummaryViewType] = useState<'product' | 'company' | 'port'>('product');
  const [vesselDetails, setVesselDetails] = useState<any[]>([]);
  const [summaryViewData, setSummaryViewData] = useState<any[]>([]);
  const [loadingVesselDetails, setLoadingVesselDetails] = useState(false);
  const [loadingSummaryView, setLoadingSummaryView] = useState(false);
  const [analyticsAsOfDate, setAnalyticsAsOfDate] = useState('');
  const [analyticsBackdate, setAnalyticsBackdate] = useState('');
  const [analyticsAvailableDates, setAnalyticsAvailableDates] = useState<string[]>([]);

  // Layer 2: Selected product details and drilldown
  const [selectedProduct, setSelectedProduct] = useState<any>(null);
  const [drilldownRows, setDrilldownRows] = useState<any[]>([]);
  const [loadingDrilldown, setLoadingDrilldown] = useState(false);
  const [narrative, setNarrative] = useState<any>(null);

  // UI State
  const [toast, setToast] = useState<any>(null);
  const [uploadPanelOpen, setUploadPanelOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const API_BASE_URL = 'http://localhost:8000';

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const fetchAnalyticsLayerDates = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/analytics/dates`);
      const data = await response.json();
      if (data.success) {
        const dates = data.available_dates || [];
        setAnalyticsAvailableDates(dates);
        if (dates.length > 0 && !analyticsAsOfDate) {
          setAnalyticsAsOfDate(dates[0]);
        }
      }
    } catch (e) {
      console.error('Failed to fetch analytics dates:', e);
    }
  };

  const fetchVesselDetails = async (asOfParam = analyticsAsOfDate, backdateParam = analyticsBackdate) => {
    setLoadingVesselDetails(true);
    try {
      const params = new URLSearchParams();
      if (asOfParam) params.set('as_of', asOfParam);
      if (backdateParam) params.set('backdate', backdateParam);
      
      const url = params.toString()
        ? `${API_BASE_URL}/api/analytics/vessel-detail?${params.toString()}`
        : `${API_BASE_URL}/api/analytics/vessel-detail`;
      
      const response = await fetch(url);
      const data = await response.json();
      if (data.success) {
        setVesselDetails(data.data || []);
      }
    } catch (e) {
      console.error('Failed to fetch vessel details:', e);
      showToast('Failed to load vessel details', 'error');
    } finally {
      setLoadingVesselDetails(false);
    }
  };

  const fetchSummaryView = async (viewType = summaryViewType, asOfParam = analyticsAsOfDate, backdateParam = analyticsBackdate) => {
    setLoadingSummaryView(true);
    try {
      const params = new URLSearchParams();
      params.set('view_type', viewType);
      if (asOfParam) params.set('as_of', asOfParam);
      if (backdateParam) params.set('backdate', backdateParam);
      
      const response = await fetch(`${API_BASE_URL}/api/analytics/summary?${params.toString()}`);
      const data = await response.json();
      if (data.success) {
        setSummaryViewData(data.data || []);
      }
    } catch (e) {
      console.error('Failed to fetch summary view:', e);
      showToast('Failed to load summary view', 'error');
    } finally {
      setLoadingSummaryView(false);
    }
  };

  const fetchDrilldown = async (product: any = selectedProduct, asOfParam = analyticsAsOfDate, backdateParam = analyticsBackdate) => {
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

  useEffect(() => {
    fetchAnalyticsLayerDates();
  }, []);

  useEffect(() => {
    if (activeAnalyticsTab === 'inventory') {
      fetchVesselDetails(analyticsAsOfDate, analyticsBackdate);
    } else {
      fetchSummaryView(summaryViewType, analyticsAsOfDate, analyticsBackdate);
    }
  }, [activeAnalyticsTab, summaryViewType, analyticsAsOfDate, analyticsBackdate]);




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
      <header className="bg-white/80 backdrop-blur-sm border-b border-slate-200/40 px-6 flex justify-between items-center pt-1.5 pb-1.5 shrink-0 shadow-sm z-20">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 bg-gradient-to-br from-purple-300 to-purple-400 rounded-xl flex items-center justify-center border border-purple-200/60 shadow-md">
            <Package className="w-5 h-5 text-white" strokeWidth={2.5} />
          </div>
          <div className="leading-tight">
            <h1 className="text-[24px] text-violet-600 font-bold">
              Sumairo Inventory Console
              <br />
              <span className="text-[16px] text-slate-500 font-medium">Automated inventory intelligence & optimization</span>
            </h1>
          </div>
        </div>

        {/* Global Stats */}
        <div className="hidden md:flex items-center gap-5 text-xs border-l border-slate-200/40 pl-6 h-8">
          <button 
            onClick={() => {
              setRefreshing(true);
              fetchAnalyticsLayerDates().then(() => setRefreshing(false));
            }}
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
          <div className="shrink-0 px-5 py-2 border-b border-cyan-100/50">
            <div className="flex items-center gap-2.5">
              <span className="w-3 h-3 rounded-full bg-gradient-to-br from-cyan-400 to-cyan-500 shadow-md"></span>
              <h2 className="text-sm font-extrabold uppercase tracking-widest text-slate-900">1. Analytics & Monitor</h2>
            </div>
          </div>
          
          <div className="flex-1 flex flex-col min-h-0 px-5 py-3 space-y-1">
            
            {/* 4 Metric Tabs - Horizontal */}
            <div className="shrink-0 grid grid-cols-4 gap-1">
              <div className="bg-cyan-50 border border-cyan-200/50 p-1.5 rounded-md text-center">
                <span className="text-[7px] font-bold text-cyan-600 uppercase block">Products</span>
                <span className="text-sm font-extrabold text-cyan-900">—</span>
              </div>
              <div className="bg-blue-50 border border-blue-200/50 p-1.5 rounded-md text-center">
                <span className="text-[7px] font-bold text-blue-600 uppercase block">Physical Stock</span>
                <span className="text-sm font-extrabold text-blue-900">—</span>
              </div>
              <div className="bg-purple-50 border border-purple-200/50 p-1.5 rounded-md text-center">
                <span className="text-[7px] font-bold text-purple-600 uppercase block">Stock Value</span>
                <span className="text-sm font-extrabold text-purple-900">—</span>
              </div>
              <div className="bg-emerald-50 border border-emerald-200/50 p-1.5 rounded-md text-center">
                <span className="text-[7px] font-bold text-emerald-600 uppercase block">Inventory Days</span>
                <span className="text-sm font-extrabold text-emerald-900">—</span>
              </div>
            </div>

            {/* Date Filters */}
            <div className="shrink-0 grid grid-cols-2 gap-1.5">
              <div className="space-y-0.5">
                <label className="text-[7px] font-bold text-slate-400 uppercase tracking-widest">As Of</label>
                <select
                  value={analyticsAsOfDate}
                  onChange={(e) => setAnalyticsAsOfDate(e.target.value)}
                  className="w-full text-[9px] px-1.5 py-0.5 rounded-md border border-slate-200 bg-white"
                >
                  {(analyticsAvailableDates || []).map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-0.5">
                <label className="text-[7px] font-bold text-slate-400 uppercase tracking-widest">Compare To</label>
                <select
                  value={analyticsBackdate}
                  onChange={(e) => setAnalyticsBackdate(e.target.value)}
                  className="w-full text-[9px] px-1.5 py-0.5 rounded-md border border-slate-200 bg-white"
                >
                  <option value="">None</option>
                  {(analyticsAvailableDates || []).filter((d) => d !== analyticsAsOfDate).map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Layer 1 Analytics: Tabbed Interface */}
            <div className="flex-1 flex flex-col min-h-0 space-y-1">
              
              {/* Tab Buttons */}
              <div className="shrink-0 flex gap-2 border-b border-slate-200">
                <button
                  onClick={() => setActiveAnalyticsTab('inventory')}
                  className={`px-3 py-2 text-[9px] font-bold uppercase tracking-wider rounded-t-lg transition-all ${
                    activeAnalyticsTab === 'inventory'
                      ? 'bg-cyan-100 border-b-2 border-cyan-500 text-cyan-700'
                      : 'bg-slate-50 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  📦 Inventory (Vessel)
                </button>
                <button
                  onClick={() => setActiveAnalyticsTab('summary')}
                  className={`px-3 py-2 text-[9px] font-bold uppercase tracking-wider rounded-t-lg transition-all ${
                    activeAnalyticsTab === 'summary'
                      ? 'bg-cyan-100 border-b-2 border-cyan-500 text-cyan-700'
                      : 'bg-slate-50 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  📊 Summary
                </button>
              </div>

              {/* Tab Content */}
              <div className="flex-1 flex flex-col min-h-0">
                
                {/* INVENTORY TAB */}
                {activeAnalyticsTab === 'inventory' && (
                  <div className="flex-1 flex flex-col min-h-0">
                    <div className="overflow-y-auto border border-slate-100 rounded-xl p-2 space-y-1.5 bg-slate-50/50 custom-scrollbar flex-1">
                      {loadingVesselDetails ? (
                        <div className="text-center py-8 text-[11px] text-slate-400">Loading vessel data...</div>
                      ) : vesselDetails.length === 0 ? (
                        <div className="text-center py-4 text-[10px] text-slate-500 font-semibold">No vessel data available</div>
                      ) : vesselDetails.slice(0, 50).map((row, idx) => (
                        <div key={idx} className="p-2 bg-white border border-slate-100 rounded-lg space-y-1">
                          <div className="flex justify-between items-start">
                            <div className="min-w-0 flex-1">
                              <p className="font-bold text-[9px] text-slate-900 truncate">{row.vessel_name}</p>
                              <p className="text-[8px] text-slate-600 truncate">{row.product_name} • {row.port_name}</p>
                            </div>
                          </div>
                          <div className="grid grid-cols-2 gap-1 text-[8px]">
                            <span className="text-slate-600">Stock: <span className="font-bold">{Number(row.physical_stock).toFixed(0)}</span></span>
                            <span className="text-slate-600">Days: <span className="font-bold">{Number(row.inventory_days || 0).toFixed(0)}</span></span>
                          </div>
                          {row.delta_physical_stock !== null && (
                            <span className={`text-[8px] font-semibold ${row.delta_physical_stock >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                              Δ {row.delta_physical_stock >= 0 ? '+' : ''}{Number(row.delta_physical_stock).toFixed(0)}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* SUMMARY TAB */}
                {activeAnalyticsTab === 'summary' && (
                  <div className="flex-1 flex flex-col min-h-0">
                    {/* Summary Sub-tabs */}
                    <div className="shrink-0 flex gap-1 bg-slate-100 p-1 rounded-lg mb-1">
                      {(['product', 'company', 'port'] as const).map((type) => (
                        <button
                          key={type}
                          onClick={() => setSummaryViewType(type)}
                          className={`flex-1 px-2 py-1 text-[8px] font-bold uppercase rounded transition-all ${
                            summaryViewType === type
                              ? 'bg-white text-cyan-700 border border-cyan-200 shadow-sm'
                              : 'text-slate-600 hover:bg-white/50'
                          }`}
                        >
                          {type === 'product' ? '📦 Product' : type === 'company' ? '🏢 Company' : '⛴️ Port'}
                        </button>
                      ))}
                    </div>

                    <div className="overflow-y-auto border border-slate-100 rounded-xl p-2 space-y-1.5 bg-slate-50/50 custom-scrollbar flex-1">
                      {loadingSummaryView ? (
                        <div className="text-center py-8 text-[11px] text-slate-400">Loading summary data...</div>
                      ) : summaryViewData.length === 0 ? (
                        <div className="text-center py-4 text-[10px] text-slate-500 font-semibold">No summary data available</div>
                      ) : summaryViewData.map((row, idx) => {
                        const displayName = 
                          summaryViewType === 'product' ? row.product_name :
                          summaryViewType === 'company' ? row.company_name :
                          row.port_name;
                        return (
                          <div key={idx} className="p-2 bg-white border border-slate-100 rounded-lg space-y-1">
                            <div className="flex justify-between items-start">
                              <p className="font-bold text-[9px] text-slate-900 truncate">{displayName}</p>
                              <span className="text-[8px] font-bold text-purple-600 whitespace-nowrap ml-1">₹{(row.stock_value / 1000000).toFixed(1)}M</span>
                            </div>
                            <div className="grid grid-cols-2 gap-1 text-[8px]">
                              <span className="text-slate-600">Stock: <span className="font-bold">{Number(row.physical_stock).toFixed(0)}</span></span>
                              <span className="text-slate-600">Days: <span className="font-bold">{Number(row.inventory_days || 0).toFixed(1)}</span></span>
                            </div>
                            <div className="grid grid-cols-2 gap-1 text-[8px]">
                              <span className="text-slate-600">Cost: <span className="font-bold">₹{Number(row.cost_price_inr).toFixed(0)}/MT</span></span>
                              <span className="text-slate-600">Sell: <span className="font-bold">₹{Number(row.average_selling_price_inr).toFixed(0)}/MT</span></span>
                            </div>
                            {row.delta_physical_stock !== null && (
                              <span className={`text-[8px] font-semibold ${row.delta_physical_stock >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                Δ {row.delta_physical_stock >= 0 ? '+' : ''}{Number(row.delta_physical_stock).toFixed(0)}
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

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
              onClick={() => showToast('Intelligence insights coming in Layer 2', 'success')}
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
