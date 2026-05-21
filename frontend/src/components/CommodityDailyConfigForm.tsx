import { useEffect, useMemo, useState } from 'react';

type Commodity = {
  id: number;
  commodity_name: string;
  commodity_code?: string | null;
  unit_of_measure: string;
  is_active: boolean;
};

type DailyConfig = {
  id: number;
  commodity_id: number;
  config_date: string;
  cost_price_per_unit?: number | null;
  market_price_per_unit?: number | null;
  replacement_cost_per_unit?: number | null;
  desired_stock_level?: number | null;
  min_stock_level?: number | null;
  max_stock_level?: number | null;
  target_inventory_days: number;
  estimated_days_to_sale: number;
  cash_realization_rate: number;
  expected_gross_margin?: number | null;
  annual_cost_of_capital_rate: number;
  is_finalized: boolean;
  notes?: string | null;
};

type ConfigForm = {
  cost_price_per_unit: string;
  market_price_per_unit: string;
  replacement_cost_per_unit: string;
  desired_stock_level: string;
  min_stock_level: string;
  max_stock_level: string;
  target_inventory_days: string;
  estimated_days_to_sale: string;
  cash_realization_rate: string;
  expected_gross_margin: string;
  annual_cost_of_capital_rate: string;
  notes: string;
};

type Props = {
  apiBaseUrl: string;
  onToast?: (message: string, type?: 'success' | 'error') => void;
};

const blankForm: ConfigForm = {
  cost_price_per_unit: '',
  market_price_per_unit: '',
  replacement_cost_per_unit: '',
  desired_stock_level: '',
  min_stock_level: '',
  max_stock_level: '',
  target_inventory_days: '30',
  estimated_days_to_sale: '15',
  cash_realization_rate: '0.95',
  expected_gross_margin: '',
  annual_cost_of_capital_rate: '0.08',
  notes: '',
};

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function numOrNull(value: string): number | null {
  if (value.trim() === '') {
    return null;
  }
  const parsed = Number(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function fromConfigToForm(config: DailyConfig): ConfigForm {
  return {
    cost_price_per_unit: config.cost_price_per_unit?.toString() ?? '',
    market_price_per_unit: config.market_price_per_unit?.toString() ?? '',
    replacement_cost_per_unit: config.replacement_cost_per_unit?.toString() ?? '',
    desired_stock_level: config.desired_stock_level?.toString() ?? '',
    min_stock_level: config.min_stock_level?.toString() ?? '',
    max_stock_level: config.max_stock_level?.toString() ?? '',
    target_inventory_days: config.target_inventory_days?.toString() ?? '30',
    estimated_days_to_sale: config.estimated_days_to_sale?.toString() ?? '15',
    cash_realization_rate: config.cash_realization_rate?.toString() ?? '0.95',
    expected_gross_margin: config.expected_gross_margin?.toString() ?? '',
    annual_cost_of_capital_rate: config.annual_cost_of_capital_rate?.toString() ?? '0.08',
    notes: config.notes ?? '',
  };
}

export default function CommodityDailyConfigForm({ apiBaseUrl, onToast }: Props) {
  const [configDate, setConfigDate] = useState<string>(todayIsoDate());
  const [commodities, setCommodities] = useState<Commodity[]>([]);
  const [configs, setConfigs] = useState<DailyConfig[]>([]);
  const [selectedCommodityId, setSelectedCommodityId] = useState<number | null>(null);
  const [form, setForm] = useState<ConfigForm>(blankForm);
  const [loading, setLoading] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);

  const selectedCommodity = useMemo(
    () => commodities.find((c) => c.id === selectedCommodityId) ?? null,
    [commodities, selectedCommodityId]
  );

  const existingConfig = useMemo(
    () => configs.find((c) => c.commodity_id === selectedCommodityId) ?? null,
    [configs, selectedCommodityId]
  );

  const notify = (message: string, type: 'success' | 'error' = 'success') => {
    if (onToast) {
      onToast(message, type);
    }
  };

  const loadAll = async () => {
    setLoading(true);
    try {
      const [commoditiesRes, configsRes] = await Promise.all([
        fetch(`${apiBaseUrl}/api/inventory/commodities`),
        fetch(`${apiBaseUrl}/api/inventory/config/commodities/${configDate}`),
      ]);

      const commoditiesJson = await commoditiesRes.json();
      const configsJson = await configsRes.json();

      if (!commoditiesRes.ok) {
        throw new Error(commoditiesJson.detail || 'Failed to load commodities');
      }

      setCommodities(commoditiesJson);
      setConfigs(configsRes.ok ? configsJson : []);

      if (commoditiesJson.length > 0 && !selectedCommodityId) {
        setSelectedCommodityId(commoditiesJson[0].id);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load commodity config data';
      notify(message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configDate]);

  useEffect(() => {
    if (existingConfig) {
      setForm(fromConfigToForm(existingConfig));
    } else {
      setForm(blankForm);
    }
  }, [existingConfig]);

  const updateForm = (field: keyof ConfigForm, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleCopyFromPrevious = async () => {
    try {
      const res = await fetch(
        `${apiBaseUrl}/api/inventory/config/copy-from-previous?config_date=${configDate}`,
        { method: 'POST' }
      );
      const body = await res.json();
      if (!res.ok) {
        throw new Error(body.detail || 'Failed to copy previous day configuration');
      }
      notify(body.message || 'Copied config from previous day');
      await loadAll();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to copy previous day config';
      notify(message, 'error');
    }
  };

  const handleSave = async () => {
    if (!selectedCommodityId) {
      notify('Select a commodity first', 'error');
      return;
    }

    if (form.cost_price_per_unit.trim() === '') {
      notify('Cost price is required for daily config', 'error');
      return;
    }

    const payload = {
      commodity_id: selectedCommodityId,
      config_date: configDate,
      cost_price_per_unit: numOrNull(form.cost_price_per_unit),
      market_price_per_unit: numOrNull(form.market_price_per_unit),
      replacement_cost_per_unit: numOrNull(form.replacement_cost_per_unit),
      desired_stock_level: numOrNull(form.desired_stock_level),
      min_stock_level: numOrNull(form.min_stock_level),
      max_stock_level: numOrNull(form.max_stock_level),
      target_inventory_days: numOrNull(form.target_inventory_days) ?? 30,
      estimated_days_to_sale: numOrNull(form.estimated_days_to_sale) ?? 15,
      cash_realization_rate: numOrNull(form.cash_realization_rate) ?? 0.95,
      expected_gross_margin: numOrNull(form.expected_gross_margin),
      annual_cost_of_capital_rate: numOrNull(form.annual_cost_of_capital_rate) ?? 0.08,
      notes: form.notes || null,
    };

    setSaving(true);
    try {
      let res: Response;
      if (existingConfig) {
        res = await fetch(`${apiBaseUrl}/api/inventory/config/${existingConfig.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else {
        res = await fetch(`${apiBaseUrl}/api/inventory/config`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }

      const body = await res.json();
      if (!res.ok) {
        throw new Error(body.detail || 'Failed to save daily configuration');
      }

      notify(existingConfig ? 'Configuration updated' : 'Configuration created');
      await loadAll();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to save configuration';
      notify(message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3 border-t border-slate-100 pt-3">
      <div className="flex items-center justify-between gap-2">
        <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">
          Commodity Daily Config
        </span>
        <button
          type="button"
          onClick={handleCopyFromPrevious}
          className="px-2 py-1 text-[10px] font-semibold rounded-md border border-cyan-200 bg-cyan-50 text-cyan-700 hover:bg-cyan-100"
        >
          Copy Prev Day
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <input
          type="date"
          value={configDate}
          onChange={(e) => setConfigDate(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px] text-slate-800"
        />
        <select
          value={selectedCommodityId ?? ''}
          onChange={(e) => setSelectedCommodityId(Number(e.target.value))}
          className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px] text-slate-800"
        >
          {commodities.map((commodity) => (
            <option key={commodity.id} value={commodity.id}>
              {commodity.commodity_name}
            </option>
          ))}
        </select>
      </div>

      {selectedCommodity && (
        <div className="text-[10px] text-slate-500 bg-slate-50 rounded-lg border border-slate-100 px-2 py-1.5">
          Selected: <span className="font-semibold text-slate-700">{selectedCommodity.commodity_name}</span>
        </div>
      )}

      {loading ? (
        <div className="text-[10px] text-slate-400">Loading commodity data...</div>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          <input
            type="number"
            placeholder="Cost Price*"
            value={form.cost_price_per_unit}
            onChange={(e) => updateForm('cost_price_per_unit', e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px]"
          />
          <input
            type="number"
            placeholder="Market Price"
            value={form.market_price_per_unit}
            onChange={(e) => updateForm('market_price_per_unit', e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px]"
          />
          <input
            type="number"
            placeholder="Replacement Cost"
            value={form.replacement_cost_per_unit}
            onChange={(e) => updateForm('replacement_cost_per_unit', e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px]"
          />
          <input
            type="number"
            placeholder="Desired Stock"
            value={form.desired_stock_level}
            onChange={(e) => updateForm('desired_stock_level', e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px]"
          />
          <input
            type="number"
            placeholder="Min Stock"
            value={form.min_stock_level}
            onChange={(e) => updateForm('min_stock_level', e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px]"
          />
          <input
            type="number"
            placeholder="Max Stock"
            value={form.max_stock_level}
            onChange={(e) => updateForm('max_stock_level', e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px]"
          />
          <input
            type="number"
            placeholder="Target Days"
            value={form.target_inventory_days}
            onChange={(e) => updateForm('target_inventory_days', e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px]"
          />
          <input
            type="number"
            step="0.01"
            placeholder="Cash Realization (0-1)"
            value={form.cash_realization_rate}
            onChange={(e) => updateForm('cash_realization_rate', e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px]"
          />
        </div>
      )}

      <textarea
        rows={2}
        placeholder="Notes"
        value={form.notes}
        onChange={(e) => updateForm('notes', e.target.value)}
        className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px] text-slate-800"
      />

      <button
        type="button"
        onClick={handleSave}
        disabled={saving || loading || !selectedCommodityId}
        className="w-full py-2 bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-600 hover:to-cyan-700 text-white font-bold text-xs rounded-lg disabled:opacity-50"
      >
        {saving ? 'Saving...' : existingConfig ? 'Update Daily Config' : 'Create Daily Config'}
      </button>
    </div>
  );
}
