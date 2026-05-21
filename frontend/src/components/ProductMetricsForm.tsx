/**
 * ProductMetricsForm - Editable table for daily product metrics
 * Auto-populates from latest DB data, allows bulk editing and saves with new date
 */

import React, { useState, useEffect } from 'react';
import './ProductMetricsForm.css';

interface ProductMetric {
  id: number;
  product_name: string;
  metric_date: string;
  market_price: number | null;
  replacement_cost: number | null;
  safety_stock_level: number | null;
  reorder_stock_level: number | null;
  target_monthly_sales: number | null;
  target_storage_cap_days: number | null;
  target_inventory_days: number | null;
  target_cash_realization_days: number | null;
}

interface ProductMetricFormData extends Omit<ProductMetric, 'id' | 'metric_date'> {
  metric_date?: string; // Will use new date on save
}

const ProductMetricsForm: React.FC = () => {
  const [metrics, setMetrics] = useState<ProductMetric[]>([]);
  const [editedMetrics, setEditedMetrics] = useState<Record<number, ProductMetricFormData>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [newDate, setNewDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [hasChanges, setHasChanges] = useState(false);

  // Fetch latest metrics on component mount
  useEffect(() => {
    fetchLatestMetrics();
  }, []);

  const fetchLatestMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/inventory/product-metrics/latest');
      if (!response.ok) throw new Error('Failed to fetch metrics');
      const data = await response.json();
      setMetrics(data);
      setEditedMetrics({}); // Clear edits on fresh load
      setHasChanges(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleCellChange = (id: number, field: keyof ProductMetricFormData, value: string | number | null) => {
    setEditedMetrics(prev => ({
      ...prev,
      [id]: {
        ...prev[id],
        [field]: value === '' ? null : (field === 'product_name' ? value : parseFloat(value as string) || null)
      }
    }));
    setHasChanges(true);
    setSuccess(null);
  };

  const handleSave = async () => {
    if (!hasChanges) {
      setError('No changes to save');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Prepare updates
      const updates = metrics
        .filter(metric => editedMetrics[metric.id])
        .map(metric => ({
          product_name: editedMetrics[metric.id].product_name || metric.product_name,
          market_price: editedMetrics[metric.id].market_price,
          replacement_cost: editedMetrics[metric.id].replacement_cost,
          safety_stock_level: editedMetrics[metric.id].safety_stock_level,
          reorder_stock_level: editedMetrics[metric.id].reorder_stock_level,
          target_monthly_sales: editedMetrics[metric.id].target_monthly_sales,
          target_storage_cap_days: editedMetrics[metric.id].target_storage_cap_days,
          target_inventory_days: editedMetrics[metric.id].target_inventory_days,
          target_cash_realization_days: editedMetrics[metric.id].target_cash_realization_days,
        }));

      if (updates.length === 0) {
        setError('No metrics changed');
        return;
      }

      const response = await fetch(`/api/inventory/product-metrics/by-date?new_date=${newDate}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });

      if (!response.ok) throw new Error('Failed to save metrics');

      const updatedData = await response.json();
      setMetrics(updatedData);
      setEditedMetrics({});
      setHasChanges(false);
      setSuccess(`Successfully updated ${updatedData.length} metrics for ${newDate}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getDisplayValue = (metricId: number, field: keyof ProductMetric, originalValue: any) => {
    return editedMetrics[metricId]?.[field] !== undefined ? editedMetrics[metricId][field] : originalValue;
  };

  const getRowClass = (metricId: number) => {
    return editedMetrics[metricId] ? 'row-edited' : '';
  };

  if (loading && metrics.length === 0) return <div className="loading">Loading product metrics...</div>;

  return (
    <div className="product-metrics-form">
      <div className="form-header">
        <h2>Product Daily Metrics Configuration</h2>
        <p>Edit values below and save with a new date</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="controls">
        <div className="date-picker">
          <label htmlFor="new-date">Save Date:</label>
          <input
            id="new-date"
            type="date"
            value={newDate}
            onChange={(e) => setNewDate(e.target.value)}
            disabled={loading}
          />
        </div>

        <button
          className="btn btn-reload"
          onClick={fetchLatestMetrics}
          disabled={loading || hasChanges}
          title="Reload from database"
        >
          ↻ Reload
        </button>

        <button
          className="btn btn-save"
          onClick={handleSave}
          disabled={loading || !hasChanges}
        >
          {loading ? 'Saving...' : '💾 Save Changes'}
        </button>
      </div>

      <div className="metrics-table-wrapper">
        <table className="metrics-table">
          <thead>
            <tr>
              <th>Product Name</th>
              <th>Market Price (₹/MT)</th>
              <th>Replacement Cost (₹/MT)</th>
              <th>Safety Stock Level (MT)</th>
              <th>Reorder Stock Level (MT)</th>
              <th>Target Monthly Sales (MT)</th>
              <th>Storage Cap Days</th>
              <th>Inventory Holding Days</th>
              <th>Cash Realization Days</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map(metric => (
              <tr key={metric.id} className={getRowClass(metric.id)}>
                <td className="cell-product-name">
                  <input
                    type="text"
                    value={getDisplayValue(metric.id, 'product_name', metric.product_name)}
                    onChange={(e) => handleCellChange(metric.id, 'product_name', e.target.value)}
                    readOnly
                    title="Product names cannot be edited"
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="0.01"
                    value={getDisplayValue(metric.id, 'market_price', metric.market_price) || ''}
                    onChange={(e) => handleCellChange(metric.id, 'market_price', e.target.value)}
                    disabled={loading}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="0.01"
                    value={getDisplayValue(metric.id, 'replacement_cost', metric.replacement_cost) || ''}
                    onChange={(e) => handleCellChange(metric.id, 'replacement_cost', e.target.value)}
                    disabled={loading}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="0.001"
                    value={getDisplayValue(metric.id, 'safety_stock_level', metric.safety_stock_level) || ''}
                    onChange={(e) => handleCellChange(metric.id, 'safety_stock_level', e.target.value)}
                    disabled={loading}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="0.001"
                    value={getDisplayValue(metric.id, 'reorder_stock_level', metric.reorder_stock_level) || ''}
                    onChange={(e) => handleCellChange(metric.id, 'reorder_stock_level', e.target.value)}
                    disabled={loading}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="0.001"
                    value={getDisplayValue(metric.id, 'target_monthly_sales', metric.target_monthly_sales) || ''}
                    onChange={(e) => handleCellChange(metric.id, 'target_monthly_sales', e.target.value)}
                    disabled={loading}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="0.01"
                    value={getDisplayValue(metric.id, 'target_storage_cap_days', metric.target_storage_cap_days) || ''}
                    onChange={(e) => handleCellChange(metric.id, 'target_storage_cap_days', e.target.value)}
                    disabled={loading}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="0.01"
                    value={getDisplayValue(metric.id, 'target_inventory_days', metric.target_inventory_days) || ''}
                    onChange={(e) => handleCellChange(metric.id, 'target_inventory_days', e.target.value)}
                    disabled={loading}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="0.01"
                    value={getDisplayValue(metric.id, 'target_cash_realization_days', metric.target_cash_realization_days) || ''}
                    onChange={(e) => handleCellChange(metric.id, 'target_cash_realization_days', e.target.value)}
                    disabled={loading}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="form-footer">
        <p>
          {metrics.length} products loaded | {Object.keys(editedMetrics).length} products edited | 
          {hasChanges ? ' Unsaved changes' : ' All saved'}
        </p>
      </div>
    </div>
  );
};

export default ProductMetricsForm;
