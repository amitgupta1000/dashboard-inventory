import { useState, useEffect } from 'react';
import {
  Package, Sparkles, Zap, RefreshCw, Upload, X
} from 'lucide-react';
import './styles/animations.css';
import UploadPanel from './components/UploadPanel';

type TopMetrics = {
  products: number;
  unsoldStock: number;
  stockValue: number;
  mtm: number;
  realisedGm: number;
  pricedProducts: number;
  missingMarketPriceProducts: number;
};

function App() {
  // Layer 1 Analytics: Tab-based exploration
  const [activeAnalyticsTab, setActiveAnalyticsTab] = useState<'inventory' | 'summary'>('inventory');
  const [summaryViewType, setSummaryViewType] = useState<'product' | 'port'>('product');
  const [vesselDetails, setVesselDetails] = useState<any[]>([]);
  const [summaryViewData, setSummaryViewData] = useState<any[]>([]);
  const [loadingVesselDetails, setLoadingVesselDetails] = useState(false);
  const [loadingSummaryView, setLoadingSummaryView] = useState(false);
  const [analyticsAsOfDate, setAnalyticsAsOfDate] = useState('');
  const [analyticsBackdate, setAnalyticsBackdate] = useState('');
  const [analyticsAvailableDates, setAnalyticsAvailableDates] = useState<string[]>([]);
  const [unsoldDaysThreshold, setUnsoldDaysThreshold] = useState<number>(25);

  // Layer 2: Selected product details and drilldown
  const [selectedProduct, setSelectedProduct] = useState<any>(null);
  const [drilldownRows, setDrilldownRows] = useState<any[]>([]);
  const [loadingDrilldown, setLoadingDrilldown] = useState(false);
  const [narrative, setNarrative] = useState<any>(null);

  // Modal State
  const [inventoryModalOpen, setInventoryModalOpen] = useState(false);
  const [summaryModalOpen, setSummaryModalOpen] = useState(false);
  const [summaryDrilldownOpen, setSummaryDrilldownOpen] = useState(false);
  const [summaryDrilldownLoading, setSummaryDrilldownLoading] = useState(false);
  const [summaryDrilldownRows, setSummaryDrilldownRows] = useState<any[]>([]);
  const [summaryDrilldownContext, setSummaryDrilldownContext] = useState<any>(null);

  // UI State
  const [toast, setToast] = useState<any>(null);
  const [uploadPanelOpen, setUploadPanelOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [topMetrics, setTopMetrics] = useState<TopMetrics>({
    products: 0,
    unsoldStock: 0,
    stockValue: 0,
    mtm: 0,
    realisedGm: 0,
    pricedProducts: 0,
    missingMarketPriceProducts: 0,
  });
  const [loadingTopMetrics, setLoadingTopMetrics] = useState(false);
  const [kpiRows, setKpiRows] = useState<any[]>([]);
  const [companyOptions, setCompanyOptions] = useState<string[]>([]);
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([]);

  const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

  const apiUrl = (path: string) => (API_BASE_URL ? `${API_BASE_URL}${path}` : path);

  const computeTopMetrics = (rows: any[], selectedCompanyList: string[]): TopMetrics => {
    if (!rows.length || !selectedCompanyList.length) {
      return {
        products: 0,
        unsoldStock: 0,
        stockValue: 0,
        mtm: 0,
        realisedGm: 0,
        pricedProducts: 0,
        missingMarketPriceProducts: 0,
      };
    }

    const selectedSet = new Set(selectedCompanyList.map((c) => c.trim()));
    const filteredRows = rows.filter((row) => selectedSet.has(String(row?.company_name || '').trim()));

    if (!filteredRows.length) {
      return {
        products: 0,
        unsoldStock: 0,
        stockValue: 0,
        mtm: 0,
        realisedGm: 0,
        pricedProducts: 0,
        missingMarketPriceProducts: 0,
      };
    }

    const productAgg: Record<string, {
      physical: number;
      unsold: number;
      stockValue: number;
      mtmValue: number;
      hasMarketPrice: boolean;
    }> = {};

    let totalRealisedGm = 0;

    for (const row of filteredRows) {
      const productName = String(row?.product_name || '').trim();
      if (!productName) continue;

      const physical = Number(row?.physical_stock || 0);
      const unsold = Number(row?.unsold_qty || 0);
      const purchasePrice = Number(row?.cost_price_inr || 0);
      const marketPrice = Number(row?.market_price_inr || 0);

      if (!productAgg[productName]) {
        productAgg[productName] = {
          physical: 0,
          unsold: 0,
          stockValue: 0,
          mtmValue: 0,
          hasMarketPrice: false,
        };
      }

      productAgg[productName].physical += physical;
      productAgg[productName].unsold += unsold;
      productAgg[productName].stockValue += unsold * purchasePrice;
      productAgg[productName].mtmValue += unsold * marketPrice;
      if (marketPrice > 0 && unsold > 0) {
        productAgg[productName].hasMarketPrice = true;
      }

      const avgSalePrice = Number(row?.average_selling_price_inr || 0);
      const otrQty = Number(row?.otr_qty || 0);
      const realizedQty = Math.max(0, otrQty - unsold);
      totalRealisedGm += (avgSalePrice - purchasePrice) * realizedQty;
    }

    let products = 0;
    let totalUnsoldStock = 0;
    let totalStockValue = 0;
    let totalMtmValue = 0;
    let pricedProducts = 0;
    let missingMarketPriceProducts = 0;

    for (const agg of Object.values(productAgg)) {
      if (agg.physical !== 0) {
        products += 1;
        if (agg.hasMarketPrice) {
          pricedProducts += 1;
        } else {
          missingMarketPriceProducts += 1;
        }
      }
      totalUnsoldStock += agg.unsold;
      totalStockValue += agg.stockValue;
      totalMtmValue += agg.mtmValue;
    }

    return {
      products,
      unsoldStock: totalUnsoldStock,
      stockValue: totalStockValue,
      mtm: totalMtmValue - totalStockValue,
      realisedGm: totalRealisedGm,
      pricedProducts,
      missingMarketPriceProducts,
    };
  };

  const toggleCompany = (companyName: string) => {
    setSelectedCompanies((prev) => {
      if (prev.includes(companyName)) {
        if (prev.length === 1) return prev;
        return prev.filter((c) => c !== companyName);
      }
      return [...prev, companyName];
    });
  };

  const toggleAllCompanies = () => {
    if (!companyOptions.length) return;
    setSelectedCompanies(companyOptions);
  };

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const fetchAnalyticsLayerDates = async () => {
    try {
      const response = await fetch(apiUrl('/api/analytics/dates'));
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

  const fetchVesselDetailRowsRaw = async (
    asOfParam = analyticsAsOfDate,
    backdateParam = analyticsBackdate,
    unsoldDaysThresholdParam = unsoldDaysThreshold,
  ) => {
    const params = new URLSearchParams();
    if (asOfParam) params.set('as_of', asOfParam);
    if (backdateParam) params.set('backdate', backdateParam);
    params.set('unsold_days_threshold', String(unsoldDaysThresholdParam));

    const url = params.toString()
      ? apiUrl(`/api/analytics/vessel-detail?${params.toString()}`)
      : apiUrl('/api/analytics/vessel-detail');

    const response = await fetch(url);
    const data = await response.json();
    return Array.isArray(data?.data) ? data.data : [];
  };

  const fetchVesselDetails = async (
    asOfParam = analyticsAsOfDate,
    backdateParam = analyticsBackdate,
    unsoldDaysThresholdParam = unsoldDaysThreshold,
  ) => {
    setLoadingVesselDetails(true);
    try {
      const rows = await fetchVesselDetailRowsRaw(asOfParam, backdateParam, unsoldDaysThresholdParam);
      setVesselDetails(rows);
    } catch (e) {
      console.error('Failed to fetch vessel details:', e);
      showToast('Failed to load vessel details', 'error');
    } finally {
      setLoadingVesselDetails(false);
    }
  };

  const openSummaryDrilldown = async (row: any) => {
    const scope = summaryViewType === 'product'
      ? { key: 'product_name', value: String(row?.product_name || '').trim(), label: 'Product' }
      : { key: 'port_name', value: String(row?.port_name || '').trim(), label: 'Port' };

    if (!scope.value) {
      showToast('Unable to open drill-down for empty selection', 'error');
      return;
    }

    setSummaryDrilldownContext({
      scope,
      title: scope.value,
      summaryRow: row,
    });
    setSummaryDrilldownOpen(true);
    setSummaryDrilldownLoading(true);

    try {
      const detailRows = await fetchVesselDetailRowsRaw(analyticsAsOfDate, analyticsBackdate, unsoldDaysThreshold);
      const allowedCompanies = new Set(selectedCompanies.map((name) => String(name || '').trim()));
      const filtered = detailRows.filter((detail: any) => {
        const companyName = String(detail?.company_name || '').trim();
        const inCompanyScope = !allowedCompanies.size || allowedCompanies.has(companyName);
        const scopeValue = String(detail?.[scope.key] || '').trim();
        return inCompanyScope && scopeValue === scope.value;
      });
      setSummaryDrilldownRows(filtered);
    } catch (e) {
      console.error('Failed to load summary drill-down:', e);
      setSummaryDrilldownRows([]);
      showToast('Failed to load summary drill-down', 'error');
    } finally {
      setSummaryDrilldownLoading(false);
    }
  };

  const fetchSummaryView = async (
    viewType = summaryViewType,
    asOfParam = analyticsAsOfDate,
    backdateParam = analyticsBackdate,
    unsoldDaysThresholdParam = unsoldDaysThreshold,
    selectedCompanyListParam = selectedCompanies,
  ) => {
    setLoadingSummaryView(true);
    try {
      const params = new URLSearchParams();
      params.set('view_type', viewType);
      if (asOfParam) params.set('as_of', asOfParam);
      if (backdateParam) params.set('backdate', backdateParam);
      params.set('unsold_days_threshold', String(unsoldDaysThresholdParam));
      (selectedCompanyListParam || [])
        .map((name) => String(name || '').trim())
        .filter(Boolean)
        .forEach((name) => params.append('company', name));
      
      const response = await fetch(apiUrl(`/api/analytics/summary?${params.toString()}`));
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

      const response = await fetch(apiUrl(`/api/stock-analytics/drilldown?${params.toString()}`));
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

  const fetchNarrative = async (asOfParam = analyticsAsOfDate, backdateParam = analyticsBackdate) => {
    try {
      const params = new URLSearchParams();
      if (asOfParam) params.set('as_of', asOfParam);
      if (backdateParam) params.set('backdate', backdateParam);

      const url = params.toString()
        ? apiUrl(`/api/intelligence/narrative?${params.toString()}`)
        : apiUrl('/api/intelligence/narrative');

      const response = await fetch(url);
      const data = await response.json();
      if (data.success) {
        setNarrative(data.data || null);
      }
    } catch (e) {
      console.error('Failed to fetch narrative:', e);
      setNarrative(null);
    }
  };

  const fetchTopMetrics = async (asOfParam = analyticsAsOfDate, backdateParam = analyticsBackdate) => {
    setLoadingTopMetrics(true);
    try {
      const stockParams = new URLSearchParams();
      if (asOfParam) stockParams.set('as_of', asOfParam);
      if (backdateParam) stockParams.set('backdate', backdateParam);

      const detailUrl = stockParams.toString()
        ? apiUrl(`/api/analytics/vessel-detail?${stockParams.toString()}`)
        : apiUrl('/api/analytics/vessel-detail');

      const detailRes = await fetch(detailUrl);
      const detailJson = await detailRes.json();
      const detailRows = Array.isArray(detailJson?.data) ? detailJson.data : [];

      setKpiRows(detailRows);

      const companies: string[] = Array.from(
        new Set<string>(
          detailRows
            .map((row: any) => String(row?.company_name || '').trim())
            .filter(Boolean)
        )
      ).sort((a: string, b: string) => a.localeCompare(b));

      setCompanyOptions(companies);

      const retainedSelection = selectedCompanies.filter((c) => companies.includes(c));
      const effectiveSelection = retainedSelection.length ? retainedSelection : companies;

      setSelectedCompanies(effectiveSelection);
      setTopMetrics(computeTopMetrics(detailRows, effectiveSelection));
    } catch (e) {
      console.error('Failed to fetch top metrics:', e);
      setTopMetrics({
        products: 0,
        unsoldStock: 0,
        stockValue: 0,
        mtm: 0,
        realisedGm: 0,
        pricedProducts: 0,
        missingMarketPriceProducts: 0,
      });
      setKpiRows([]);
      setCompanyOptions([]);
      setSelectedCompanies([]);
    } finally {
      setLoadingTopMetrics(false);
    }
  };

  const refreshAnalyticsData = async () => {
    await fetchAnalyticsLayerDates();
    await fetchTopMetrics(analyticsAsOfDate, analyticsBackdate);
    await fetchNarrative(analyticsAsOfDate, analyticsBackdate);

    if (inventoryModalOpen) {
      await fetchVesselDetails(analyticsAsOfDate, analyticsBackdate, unsoldDaysThreshold);
    }

    if (summaryModalOpen || activeAnalyticsTab === 'summary') {
      await fetchSummaryView(summaryViewType, analyticsAsOfDate, analyticsBackdate, unsoldDaysThreshold, selectedCompanies);
    }

    if (selectedProduct) {
      await fetchDrilldown(selectedProduct, analyticsAsOfDate, analyticsBackdate);
    }
  };

  useEffect(() => {
    fetchAnalyticsLayerDates();
  }, []);

  useEffect(() => {
    fetchTopMetrics(analyticsAsOfDate, analyticsBackdate);
  }, [analyticsAsOfDate, analyticsBackdate]);

  useEffect(() => {
    if (!kpiRows.length || !selectedCompanies.length) return;
    setTopMetrics(computeTopMetrics(kpiRows, selectedCompanies));
  }, [kpiRows, selectedCompanies]);

  useEffect(() => {
    fetchNarrative(analyticsAsOfDate, analyticsBackdate);
  }, [analyticsAsOfDate, analyticsBackdate]);

  useEffect(() => {
    if (activeAnalyticsTab === 'summary') {
      fetchSummaryView(summaryViewType, analyticsAsOfDate, analyticsBackdate, unsoldDaysThreshold, selectedCompanies);
    }
  }, [summaryViewType, analyticsAsOfDate, analyticsBackdate, unsoldDaysThreshold, selectedCompanies, activeAnalyticsTab]);

  useEffect(() => {
    if (inventoryModalOpen) {
      fetchVesselDetails(analyticsAsOfDate, analyticsBackdate, unsoldDaysThreshold);
    }
  }, [inventoryModalOpen, analyticsAsOfDate, analyticsBackdate, unsoldDaysThreshold]);

  useEffect(() => {
    if (summaryModalOpen) {
      fetchSummaryView(summaryViewType, analyticsAsOfDate, analyticsBackdate, unsoldDaysThreshold, selectedCompanies);
    }
  }, [summaryModalOpen, summaryViewType, analyticsAsOfDate, analyticsBackdate, unsoldDaysThreshold, selectedCompanies]);

  useEffect(() => {
    if (selectedProduct) {
      fetchDrilldown(selectedProduct, analyticsAsOfDate, analyticsBackdate);
    }
  }, [selectedProduct, analyticsAsOfDate, analyticsBackdate]);

  const filteredVesselDetails = vesselDetails.filter((row) => {
    const companyName = String(row?.company_name || '').trim();
    return selectedCompanies.includes(companyName);
  });

  const filteredInventoryDetails = vesselDetails.filter((row: any) => {
    if (!selectedCompanies.length) return true;
    const companyName = String(row?.company_name || '').trim();
    return selectedCompanies.includes(companyName);
  });




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

            <div className="shrink-0 flex flex-wrap items-center gap-1.5 pb-1">
              <span className="text-[8px] font-bold text-slate-500 uppercase tracking-wider mr-1">Companies</span>
              <span className="text-[8px] font-semibold text-slate-500 mr-1">
                Selected: {selectedCompanies.length}/{companyOptions.length}
              </span>
              <button
                onClick={toggleAllCompanies}
                className={`px-2 py-1 rounded-full border text-[9px] font-bold transition-all ${selectedCompanies.length === companyOptions.length && companyOptions.length > 0
                  ? 'bg-cyan-600 text-white border-cyan-600'
                  : 'bg-white text-slate-600 border-slate-300 hover:border-cyan-400'
                }`}
              >
                All ({companyOptions.length})
              </button>
              {companyOptions.map((company) => {
                const isSelected = selectedCompanies.includes(company);
                return (
                  <button
                    key={company}
                    onClick={() => toggleCompany(company)}
                    className={`px-2 py-1 rounded-full border text-[9px] font-semibold transition-all ${isSelected
                      ? 'bg-cyan-100 text-cyan-700 border-cyan-300'
                      : 'bg-white text-slate-500 border-slate-300 hover:border-cyan-300'
                    }`}
                    title={company}
                  >
                    {company}
                  </button>
                );
              })}
            </div>
            
            {/* 5 Metric Tabs - Horizontal */}
            <div className="shrink-0 grid grid-cols-5 gap-1">
              <div className="bg-cyan-50 border border-cyan-200/50 p-1.5 rounded-md text-center">
                <span className="text-[7px] font-bold text-cyan-600 uppercase block">Products</span>
                <span className="text-sm font-extrabold text-cyan-900">
                  {loadingTopMetrics ? '...' : Number(topMetrics.products).toLocaleString('en-US')}
                </span>
              </div>
              <div className="bg-blue-50 border border-blue-200/50 p-1.5 rounded-md text-center">
                <span className="text-[7px] font-bold text-blue-600 uppercase block">Unsold Stock (MT)</span>
                <span className="text-sm font-extrabold text-blue-900">
                  {loadingTopMetrics ? '...' : Number(topMetrics.unsoldStock).toLocaleString('en-US', { maximumFractionDigits: 0 })}
                </span>
              </div>
              <div className="bg-purple-50 border border-purple-200/50 p-1.5 rounded-md text-center">
                <span className="text-[7px] font-bold text-purple-600 uppercase block">Stock Value (Rs. Cr.)</span>
                <span className="text-sm font-extrabold text-purple-900">
                  {loadingTopMetrics ? '...' : `Rs ${(Number(topMetrics.stockValue) / 10000000).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                </span>
              </div>
              <div className="bg-emerald-50 border border-emerald-200/50 p-1.5 rounded-md text-center">
                <span className="text-[7px] font-bold text-emerald-600 uppercase block">MTM (Rs. Cr.)</span>
                <span className="text-sm font-extrabold text-emerald-900">
                  {loadingTopMetrics ? '...' : `Rs ${(Number(topMetrics.mtm) / 10000000).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                </span>
              </div>
              <div className="bg-amber-50 border border-amber-200/50 p-1.5 rounded-md text-center">
                <span className="text-[7px] font-bold text-amber-600 uppercase block">REALISED GM (Rs. Cr.)</span>
                <span className="text-sm font-extrabold text-amber-900">
                  {loadingTopMetrics ? '...' : `Rs ${(Number(topMetrics.realisedGm) / 10000000).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                </span>
              </div>
            </div>

            <div className="shrink-0 text-[9px] text-slate-500 px-1">
              {loadingTopMetrics
                ? 'MTM coverage: loading...'
                : `MTM coverage: ${topMetrics.pricedProducts} priced, ${topMetrics.missingMarketPriceProducts} missing market price`}
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

            <div className="shrink-0 flex items-center gap-2">
              <label className="text-[8px] font-bold text-slate-500 uppercase tracking-wider">
                Inventory Days Min Unsold Qty
              </label>
              <input
                type="number"
                min={0}
                step={1}
                value={unsoldDaysThreshold}
                onChange={(e) => {
                  const next = Number(e.target.value);
                  setUnsoldDaysThreshold(Number.isFinite(next) && next >= 0 ? next : 0);
                }}
                className="w-20 text-[10px] px-2 py-1 rounded-md border border-slate-300 bg-white font-semibold text-slate-700"
              />
              <span className="text-[8px] text-slate-500">(Inventory days shown only when Unsold Qty &gt; threshold)</span>
            </div>

            {/* Layer 1 Analytics: Tabbed Interface */}
            <div className="flex-1 flex flex-col min-h-0 space-y-1">
              
              {/* Tab Buttons */}
              <div className="shrink-0 flex gap-2 border-b border-slate-200">
                <button
                  onClick={() => setInventoryModalOpen(true)}
                  className={`px-3 py-2 text-[9px] font-bold uppercase tracking-wider rounded-t-lg transition-all bg-slate-50 text-slate-600 hover:bg-slate-100`}
                >
                  📦 Inventory (Detail)
                </button>
                <button
                  onClick={() => setSummaryModalOpen(true)}
                  className={`px-3 py-2 text-[9px] font-bold uppercase tracking-wider rounded-t-lg transition-all bg-slate-50 text-slate-600 hover:bg-slate-100`}
                >
                  📊 Summary
                </button>
              </div>

              {/* Tab Content */}
              <div className="flex-1 flex flex-col min-h-0">
                <div className="text-center py-8 text-[11px] text-slate-400">Click on a tab above to view details</div>
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

      {/* Inventory Detail Modal */}
      {inventoryModalOpen && (
        <div className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col border border-slate-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 shrink-0">
              <div className="flex items-center gap-3">
                <span className="w-3 h-3 rounded-full bg-gradient-to-br from-cyan-400 to-cyan-500 shadow-md"></span>
                <h2 className="text-lg font-bold text-slate-900">Inventory Details (Latest Config Date)</h2>
              </div>
              <button
                onClick={() => setInventoryModalOpen(false)}
                className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-700 transition-all"
                title="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto custom-scrollbar">
              <div className="p-4 space-y-1.5">
                <div className="mb-2 p-2 rounded-lg border border-cyan-100 bg-cyan-50/60">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-[9px] uppercase tracking-wider font-bold text-cyan-700 mr-1">Company Filters</span>
                    <span className="text-[8px] font-semibold text-slate-600 mr-1">
                      Selected: {selectedCompanies.length}/{companyOptions.length}
                    </span>
                    <button
                      onClick={toggleAllCompanies}
                      className={`px-2 py-1 rounded-full border text-[9px] font-bold transition-all ${selectedCompanies.length === companyOptions.length && companyOptions.length > 0
                        ? 'bg-cyan-600 text-white border-cyan-600'
                        : 'bg-white text-slate-600 border-slate-300 hover:border-cyan-400'
                      }`}
                    >
                      All ({companyOptions.length})
                    </button>
                    {companyOptions.map((company) => {
                      const isSelected = selectedCompanies.includes(company);
                      return (
                        <button
                          key={company}
                          onClick={() => toggleCompany(company)}
                          className={`px-2 py-1 rounded-full border text-[9px] font-semibold transition-all ${isSelected
                            ? 'bg-cyan-100 text-cyan-700 border-cyan-300'
                            : 'bg-white text-slate-500 border-slate-300 hover:border-cyan-300'
                          }`}
                          title={company}
                        >
                          {company}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {loadingVesselDetails ? (
                  <div className="text-center py-12 text-slate-400">
                    <div className="inline-block text-3xl mb-3">⏳</div>
                    <p className="font-medium">Loading inventory data...</p>
                  </div>
                ) : filteredVesselDetails.length === 0 ? (
                  <div className="text-center py-12 text-slate-400">
                    <div className="inline-block text-3xl mb-3">📭</div>
                    <p className="font-medium">No inventory data available for selected companies</p>
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    {filteredVesselDetails.map((row, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 bg-gradient-to-r from-slate-50 to-cyan-50 border border-slate-200 rounded-lg hover:border-cyan-300 transition-all cursor-pointer"
                        onClick={() => {
                          setSelectedProduct({
                            product_name: row.product_name,
                            port_name: row.port_name,
                            company_name: row.company_name,
                            physical_stock: row.physical_stock,
                            stock_value: Number(row.physical_stock || 0) * Number(row.cost_price_inr || 0),
                            average_selling_price_inr: row.average_selling_price_inr,
                            market_price_inr: row.effective_market_price_inr ?? row.market_price_inr,
                            market_price_source: row.market_price_source,
                            cost_price_inr: row.cost_price_inr,
                            margin_per_mt_inr: Number(row.average_selling_price_inr || 0) - Number(row.cost_price_inr || 0),
                            vessel_count: 1,
                          });
                          setInventoryModalOpen(false);
                        }}
                        title="Select product for Layer 2 drill-down"
                      >
                        {/* Vessel Header */}
                        <div className="flex justify-between items-start mb-2">
                          <div className="min-w-0 flex-1">
                            <p className="font-bold text-xs text-slate-900 truncate">{row.vessel_name}</p>
                            <p className="text-[11px] text-slate-600 truncate">{row.product_name}</p>
                          </div>
                          <div className="ml-2 text-right">
                            <p className="text-[10px] text-slate-500"><span className="font-semibold text-slate-700">{row.company_name}</span></p>
                            <p className="text-[10px] text-slate-500">{row.port_name}</p>
                          </div>
                        </div>

                        {/* All Fields Grid - Compact */}
                        <div className="grid grid-cols-6 gap-1.5 text-[10px]">
                          {/* Col 1 */}
                          <div className="bg-white rounded p-1.5 border border-slate-100">
                            <p className="text-slate-500 font-semibold text-[9px]">Date</p>
                            <p className="font-bold text-slate-900 text-[10px]">{row.date ? row.date.split('-').slice(1).join('-') : 'N/A'}</p>
                          </div>
                          <div className="bg-white rounded p-1.5 border border-slate-100">
                            <p className="text-slate-500 font-semibold text-[9px]">Vessel Date</p>
                            <p className="font-bold text-slate-900 text-[10px]">{row.vessel_date ? row.vessel_date.split('-').slice(1).join('-') : 'N/A'}</p>
                          </div>
                          <div className="bg-white rounded p-1.5 border border-slate-100">
                            <p className="text-slate-500 font-semibold text-[9px]">Terminal</p>
                            <p className="font-bold text-slate-900 text-[10px] truncate">{row.terminal || 'N/A'}</p>
                          </div>

                          {/* Col 2 - Stock Quantities */}
                          <div className="bg-white rounded p-1.5 border border-slate-100">
                            <p className="text-slate-500 font-semibold text-[9px]">Physical Stock</p>
                            <p className="font-bold text-slate-900 text-[10px]">{Number(row.physical_stock || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                          </div>
                          <div className="bg-white rounded p-1.5 border border-slate-100">
                            <p className="text-slate-500 font-semibold text-[9px]">Unsold Qty</p>
                            <p className="font-bold text-slate-900 text-[10px]">{Number(row.unsold_qty || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                          </div>
                          <div className="bg-white rounded p-1.5 border border-slate-100">
                            <p className="text-slate-500 font-semibold text-[9px]">Sold Pending</p>
                            <p className="font-bold text-slate-900 text-[10px]">{Number(row.sold_qty_pending_lifting || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                          </div>

                          {/* Col 3 - Other Metrics */}
                          <div className="bg-white rounded p-1.5 border border-slate-100">
                            <p className="text-slate-500 font-semibold text-[9px]">OTR Qty</p>
                            <p className="font-bold text-slate-900 text-[10px]">{Number(row.otr_qty || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                          </div>
                          <div className="bg-white rounded p-1.5 border border-slate-100">
                            <p className="text-slate-500 font-semibold text-[9px]">Inventory Days</p>
                            <p className="font-bold text-slate-900 text-[10px]">{Number(row.inventory_days || 0).toFixed(1)}</p>
                          </div>

                          {/* Col 4 - Pricing */}
                          <div className="bg-white rounded p-1.5 border border-slate-100">
                            <p className="text-slate-500 font-semibold text-[9px]">Cost/MT</p>
                            <p className="font-bold text-slate-900 text-[10px]">₹{Number(row.cost_price_inr || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                          </div>
                          <div className="bg-white rounded p-1.5 border border-slate-100">
                            <p className="text-slate-500 font-semibold text-[9px]">Market Price/MT</p>
                            <p className="font-bold text-slate-900 text-[10px]">₹{Number((row.effective_market_price_inr ?? row.market_price_inr) || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                            {(() => {
                              const explicitSource = String(row.market_price_source || '').trim();
                              const rawMarketPrice = Number(row.market_price_inr || 0);
                              const avgSalePrice = Number(row.average_selling_price_inr || 0);
                              const inferredSource = explicitSource
                                ? explicitSource
                                : rawMarketPrice > 0
                                  ? 'stock_report'
                                  : 'avg_sale_price_fallback';

                              const badgeClass =
                                inferredSource === 'stock_report'
                                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                  : inferredSource === 'market_table_fallback'
                                    ? 'bg-amber-50 text-amber-700 border-amber-200'
                                    : 'bg-slate-100 text-slate-600 border-slate-200';

                              const badgeText =
                                inferredSource === 'stock_report'
                                  ? 'Stock Report'
                                  : inferredSource === 'market_table_fallback'
                                    ? 'Market Table'
                                    : rawMarketPrice <= 0 && avgSalePrice > 0
                                      ? 'Avg Sale'
                                      : 'Fallback';

                              return (
                                <span className={`inline-block mt-1 px-1.5 py-0.5 rounded-full text-[8px] font-semibold border ${badgeClass}`}>
                                  {badgeText}
                                </span>
                              );
                            })()}
                          </div>
                          <div className="bg-white rounded p-1.5 border border-slate-100">
                            <p className="text-slate-500 font-semibold text-[9px]">Sell Price/MT</p>
                            <p className="font-bold text-slate-900 text-[10px]">₹{Number(row.average_selling_price_inr || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                          </div>
                          <div className={`bg-white rounded p-1.5 border ${row.average_selling_price_inr - row.cost_price_inr >= 0 ? 'border-emerald-200' : 'border-rose-200'}`}>
                            <p className="text-slate-500 font-semibold text-[9px]">Margin/MT</p>
                            <p className={`font-bold text-[10px] ${row.average_selling_price_inr - row.cost_price_inr >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                              ₹{Number((row.average_selling_price_inr || 0) - (row.cost_price_inr || 0)).toLocaleString('en-US', { maximumFractionDigits: 0 })}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
              <p className="text-xs text-slate-600">
                Showing <span className="font-bold text-slate-900">{Math.min(filteredVesselDetails.length, 100)}</span> of <span className="font-bold text-slate-900">{filteredVesselDetails.length}</span> records
              </p>
              <button
                onClick={() => setInventoryModalOpen(false)}
                className="px-4 py-2 bg-slate-900 text-white text-sm font-bold rounded-lg hover:bg-slate-800 transition-all"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Summary Modal */}
      {summaryModalOpen && (
        <div className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-6xl w-full max-h-[90vh] flex flex-col border border-slate-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 shrink-0">
              <div className="flex items-center gap-3 flex-1">
                <span className="w-3 h-3 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-500 shadow-md"></span>
                <h2 className="text-lg font-bold text-slate-900">Summary Analysis</h2>
                <div className="flex gap-1 ml-auto">
                  {(['product', 'port'] as const).map((type) => (
                    <button
                      key={type}
                      onClick={() => setSummaryViewType(type)}
                      className={`px-2 py-1 text-[8px] font-bold uppercase rounded transition-all ${
                        summaryViewType === type
                          ? 'bg-emerald-100 text-emerald-700 border border-emerald-300'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      {type === 'product' ? '📦 Product' : '⛴️ Port'}
                    </button>
                  ))}
                </div>
              </div>
              <button
                onClick={() => setSummaryModalOpen(false)}
                className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-700 transition-all"
                title="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto custom-scrollbar">
              <div className="p-4 space-y-1.5">
                <div className="mb-2 p-2 rounded-lg border border-emerald-100 bg-emerald-50/60">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-[9px] uppercase tracking-wider font-bold text-emerald-700 mr-1">Company Filters</span>
                    <span className="text-[8px] font-semibold text-slate-600 mr-1">
                      Selected: {selectedCompanies.length}/{companyOptions.length}
                    </span>
                    <button
                      onClick={toggleAllCompanies}
                      className={`px-2 py-1 rounded-full border text-[9px] font-bold transition-all ${selectedCompanies.length === companyOptions.length && companyOptions.length > 0
                        ? 'bg-cyan-600 text-white border-cyan-600'
                        : 'bg-white text-slate-600 border-slate-300 hover:border-cyan-400'
                      }`}
                    >
                      All ({companyOptions.length})
                    </button>
                    {companyOptions.map((company) => {
                      const isSelected = selectedCompanies.includes(company);
                      return (
                        <button
                          key={company}
                          onClick={() => toggleCompany(company)}
                          className={`px-2 py-1 rounded-full border text-[9px] font-semibold transition-all ${isSelected
                            ? 'bg-cyan-100 text-cyan-700 border-cyan-300'
                            : 'bg-white text-slate-500 border-slate-300 hover:border-cyan-300'
                          }`}
                          title={company}
                        >
                          {company}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {loadingSummaryView ? (
                  <div className="text-center py-12 text-slate-400">
                    <div className="inline-block text-3xl mb-3">⏳</div>
                    <p className="font-medium">Loading summary data...</p>
                  </div>
                ) : summaryViewData.length === 0 ? (
                  <div className="text-center py-12 text-slate-400">
                    <div className="inline-block text-3xl mb-3">📭</div>
                    <p className="font-medium">No summary data available</p>
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    {summaryViewData.map((row, idx) => {
                      const displayName =
                        summaryViewType === 'product' ? row.product_name : row.port_name;
                      const entityCount =
                        summaryViewType === 'product' ? row.vessel_count : row.company_count;
                      return (
                        <div
                          key={idx}
                          className="p-2.5 bg-gradient-to-r from-slate-50 to-emerald-50 border border-slate-200 rounded-lg hover:border-emerald-300 transition-all cursor-pointer"
                          onClick={() => openSummaryDrilldown(row)}
                        >
                          {/* Header */}
                          <div className="flex justify-between items-start mb-2">
                            <div className="min-w-0 flex-1">
                              <p className="font-bold text-xs text-slate-900 truncate">{displayName}</p>
                              <p className="text-[10px] text-slate-600">
                                {summaryViewType === 'product' ? `${entityCount} vessels` : `${entityCount} companies`}
                              </p>
                            </div>
                            <div className="ml-2 text-right">
                              <p className="text-[10px] font-bold text-emerald-600">Stock Value (Rs. Cr.)</p>
                              <p className="text-xs font-bold text-emerald-700">Rs {(Number(row.stock_value || 0) / 10000000).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                            </div>
                          </div>

                          {/* All Fields Grid - Compact */}
                          <div className="grid grid-cols-7 gap-1.5 text-[10px]">
                            {/* Col 1 - Physical Stock */}
                            <div className="bg-white rounded p-1.5 border border-slate-100">
                              <p className="text-slate-500 font-semibold text-[9px]">Physical Stock</p>
                              <p className="font-bold text-slate-900 text-[10px]">{Number(row.physical_stock || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                            </div>

                            {/* Col 2 - Quantities */}
                            <div className="bg-white rounded p-1.5 border border-slate-100">
                              <p className="text-slate-500 font-semibold text-[9px]">Unsold Qty</p>
                              <p className="font-bold text-slate-900 text-[10px]">{Number(row.unsold_qty || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                            </div>
                            <div className="bg-white rounded p-1.5 border border-slate-100">
                              <p className="text-slate-500 font-semibold text-[9px]">Sold Pending</p>
                              <p className="font-bold text-slate-900 text-[10px]">{Number(row.sold_qty_pending_lifting || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                            </div>
                            <div className="bg-white rounded p-1.5 border border-slate-100">
                              <p className="text-slate-500 font-semibold text-[9px]">OTR Qty</p>
                              <p className="font-bold text-slate-900 text-[10px]">{Number(row.otr_qty || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                            </div>

                            {/* Col 3 - Weighted Metrics */}
                            <div className="bg-white rounded p-1.5 border border-slate-100">
                              <p className="text-slate-500 font-semibold text-[9px]">Inv. Days (W.Avg)</p>
                              <p className="font-bold text-slate-900 text-[10px]">{Number(row.inventory_days || 0).toFixed(1)}</p>
                            </div>

                            {/* Col 4 - Weighted Pricing */}
                            <div className="bg-white rounded p-1.5 border border-slate-100">
                              <p className="text-slate-500 font-semibold text-[9px]">Cost/MT (W.Avg)</p>
                              <p className="font-bold text-slate-900 text-[10px]">₹{Number(row.cost_price_inr || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                            </div>
                            <div className="bg-white rounded p-1.5 border border-slate-100">
                              <p className="text-slate-500 font-semibold text-[9px]">Sell/MT (W.Avg)</p>
                              <p className="font-bold text-slate-900 text-[10px]">₹{Number(row.average_selling_price_inr || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                            </div>
                            <div className={`bg-white rounded p-1.5 border ${Number(row.margin_per_mt_inr || 0) >= 0 ? 'border-emerald-200' : 'border-rose-200'}`}>
                              <p className="text-slate-500 font-semibold text-[9px]">Margin/MT</p>
                              <p className={`font-bold text-[10px] ${Number(row.margin_per_mt_inr || 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                ₹{Number(row.margin_per_mt_inr || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}
                              </p>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
              <p className="text-xs text-slate-600">
                Showing <span className="font-bold text-slate-900">{summaryViewData.length}</span> {summaryViewType} records by weighted averages (physical stock as weight)
              </p>
              <button
                onClick={() => setSummaryModalOpen(false)}
                className="px-4 py-2 bg-slate-900 text-white text-sm font-bold rounded-lg hover:bg-slate-800 transition-all"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Summary Drill-down Popup */}
      {summaryDrilldownOpen && (
        <div className="fixed inset-0 z-50 bg-black/45 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-5xl w-full max-h-[88vh] flex flex-col border border-slate-200">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 shrink-0">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-700">Summary Drill-down</p>
                <h3 className="text-base font-extrabold text-slate-900">
                  {summaryDrilldownContext?.scope?.label || 'Object'}: {summaryDrilldownContext?.title || 'N/A'}
                </h3>
                <p className="text-[11px] text-slate-600 mt-0.5">
                  {summaryDrilldownRows.length} related transactions in current filter scope
                </p>
              </div>
              <button
                onClick={() => setSummaryDrilldownOpen(false)}
                className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-700 transition-all"
                title="Close drill-down"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
              {summaryDrilldownLoading ? (
                <div className="text-center py-16 text-slate-400">
                  <div className="inline-block text-3xl mb-3">⏳</div>
                  <p className="font-medium">Loading related transactions...</p>
                </div>
              ) : summaryDrilldownRows.length === 0 ? (
                <div className="text-center py-16 text-slate-400">
                  <div className="inline-block text-3xl mb-3">📭</div>
                  <p className="font-medium">No related transactions found</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {summaryDrilldownRows.map((detail, idx) => (
                    <div key={idx} className="p-3 rounded-lg border border-slate-200 bg-gradient-to-r from-slate-50 to-white">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-xs font-bold text-slate-900 truncate">{detail.vessel_name || 'Unknown Vessel'}</p>
                          <p className="text-[10px] text-slate-600 truncate">
                            {detail.product_name || 'N/A'} • {detail.company_name || 'N/A'} • {detail.port_name || 'N/A'}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-[9px] text-slate-500">Vessel Date</p>
                          <p className="text-[10px] font-bold text-slate-800">{detail.vessel_date || 'N/A'}</p>
                        </div>
                      </div>

                      <div className="grid grid-cols-6 gap-2 mt-2 text-[10px]">
                        <div className="bg-white rounded p-1.5 border border-slate-100">
                          <p className="text-slate-500 font-semibold text-[9px]">Unsold</p>
                          <p className="font-bold text-slate-900">{Number(detail.unsold_qty || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                        </div>
                        <div className="bg-white rounded p-1.5 border border-slate-100">
                          <p className="text-slate-500 font-semibold text-[9px]">Physical</p>
                          <p className="font-bold text-slate-900">{Number(detail.physical_stock || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                        </div>
                        <div className="bg-white rounded p-1.5 border border-slate-100">
                          <p className="text-slate-500 font-semibold text-[9px]">Sold Pending</p>
                          <p className="font-bold text-slate-900">{Number(detail.sold_qty_pending_lifting || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                        </div>
                        <div className="bg-white rounded p-1.5 border border-slate-100">
                          <p className="text-slate-500 font-semibold text-[9px]">OTR</p>
                          <p className="font-bold text-slate-900">{Number(detail.otr_qty || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                        </div>
                        <div className="bg-white rounded p-1.5 border border-slate-100">
                          <p className="text-slate-500 font-semibold text-[9px]">Cost/MT</p>
                          <p className="font-bold text-slate-900">₹{Number(detail.cost_price_inr || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                        </div>
                        <div className="bg-white rounded p-1.5 border border-slate-100">
                          <p className="text-slate-500 font-semibold text-[9px]">Sell/MT</p>
                          <p className="font-bold text-slate-900">₹{Number(detail.average_selling_price_inr || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
              <p className="text-xs text-slate-600">
                Showing <span className="font-bold text-slate-900">{summaryDrilldownRows.length}</span> related rows
              </p>
              <button
                onClick={() => setSummaryDrilldownOpen(false)}
                className="px-4 py-2 bg-slate-900 text-white text-sm font-bold rounded-lg hover:bg-slate-800 transition-all"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Panel Sidebar */}
      <UploadPanel 
        isOpen={uploadPanelOpen}
        onClose={() => setUploadPanelOpen(false)}
        onUploadSuccess={async (type) => {
          showToast(`${type} file uploaded successfully!`);
          await refreshAnalyticsData();
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
