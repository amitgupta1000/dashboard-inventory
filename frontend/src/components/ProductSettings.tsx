import { useEffect, useState } from 'react';
import axios from 'axios';

interface ProductSetting {
  id?: number;
  item: string;
  safety_stock: number | null;
  reorder_point: number | null;
  max_storage_days: number | null;
  max_inventory_days: number | null;
  monthly_target_volume: number | null;
  notes?: string;
  is_active?: boolean;
  updated_at?: string;
}

const API_BASE_URL = 'http://localhost:8000';

const ProductSettings: React.FC = () => {
  const [settings, setSettings] = useState<ProductSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<Partial<ProductSetting>>({});
  const [showAddForm, setShowAddForm] = useState(false);
  const [newProduct, setNewProduct] = useState<Partial<ProductSetting>>({
    item: '',
    safety_stock: null,
    reorder_point: null,
    max_storage_days: null,
    max_inventory_days: null,
    monthly_target_volume: null,
    notes: ''
  });

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/product-settings`);
      if (response.data.success) {
        setSettings(response.data.data);
      }
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch product settings');
      console.error('Error fetching settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (setting: ProductSetting) => {
    setEditingId(setting.id!);
    setEditForm({ ...setting });
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditForm({});
  };

  const handleSave = async (id: number) => {
    try {
      const response = await axios.put(
        `${API_BASE_URL}/api/product-settings/${id}`,
        editForm
      );
      if (response.data.success) {
        await fetchSettings();
        setEditingId(null);
        setEditForm({});
      }
    } catch (err: any) {
      alert(`Failed to update: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this product setting?')) {
      return;
    }
    try {
      const response = await axios.delete(
        `${API_BASE_URL}/api/product-settings/${id}`
      );
      if (response.data.success) {
        await fetchSettings();
      }
    } catch (err: any) {
      alert(`Failed to delete: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleAddProduct = async () => {
    if (!newProduct.item) {
      alert('Product name is required');
      return;
    }
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/product-settings`,
        newProduct
      );
      if (response.data.success) {
        await fetchSettings();
        setShowAddForm(false);
        setNewProduct({
          item: '',
          safety_stock: null,
          reorder_point: null,
          max_storage_days: null,
          max_inventory_days: null,
          monthly_target_volume: null,
          notes: ''
        });
      }
    } catch (err: any) {
      alert(`Failed to add product: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleInputChange = (
    field: keyof ProductSetting,
    value: string | number | null,
    isEditing: boolean = true
  ) => {
    if (isEditing) {
      setEditForm((prev) => ({ ...prev, [field]: value }));
    } else {
      setNewProduct((prev) => ({ ...prev, [field]: value }));
    }
  };

  const renderEditableCell = (
    setting: ProductSetting,
    field: keyof ProductSetting,
    isNumeric: boolean = false
  ) => {
    const isEditing = editingId === setting.id;
    const value = isEditing ? editForm[field] : setting[field];

    if (!isEditing) {
      return (
        <td className="px-4 py-3 text-sm text-gray-700 border-b border-gray-200">
          {value !== null && value !== undefined ? String(value) : '-'}
        </td>
      );
    }

    return (
      <td className="px-4 py-3 text-sm border-b border-gray-200">
        <input
          type={isNumeric ? 'number' : 'text'}
          value={value !== null && value !== undefined ? String(value) : ''}
          onChange={(e) =>
            handleInputChange(
              field,
              isNumeric ? (e.target.value ? Number(e.target.value) : null) : e.target.value,
              true
            )
          }
          className="w-full px-2 py-1 border border-blue-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={field === 'item'}
        />
      </td>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-16">
        <div className="text-center">
          <div className="inline-block mb-4">
            <div className="animate-spin">
              <span className="text-5xl">⏳</span>
            </div>
          </div>
          <p className="text-xl text-slate-600 font-semibold">Loading product settings...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gradient-to-br from-white to-slate-50 rounded-2xl shadow-lg border border-slate-200 p-12 max-w-2xl mx-auto">
        <div className="mb-8 bg-gradient-to-br from-rose-50 to-rose-100/50 border border-rose-200 rounded-2xl p-6">
          <div className="flex items-start gap-4">
            <div className="text-4xl">⚠️</div>
            <div>
              <h3 className="text-lg font-bold text-rose-900">Backend Connection Error</h3>
              <p className="text-rose-800 mt-1 font-medium">{error}</p>
            </div>
          </div>
        </div>
        <div className="text-center">
          <button
            onClick={fetchSettings}
            className="px-8 py-3 bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-bold rounded-xl hover:shadow-lg transition-all duration-300 hover:scale-105"
          >
            🔄 Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-white to-slate-50 rounded-2xl shadow-md border border-slate-200 p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent">
            ⚙️ Product Settings
          </h2>
          <p className="text-slate-600 mt-2 font-medium">Manage inventory parameters and operational targets</p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className={`px-8 py-3 font-bold rounded-xl transition-all duration-300 whitespace-nowrap ${
            showAddForm
              ? 'bg-gradient-to-r from-slate-100 to-slate-50 text-slate-700 border border-slate-200 hover:shadow-lg'
              : 'bg-gradient-to-r from-emerald-500 to-green-500 text-white hover:shadow-lg hover:scale-105'
          }`}
        >
          {showAddForm ? '✕ Cancel' : '+ Add Product'}
        </button>
      </div>

      {/* Add Product Form */}
      {showAddForm && (
        <div className="bg-gradient-to-br from-emerald-50 to-emerald-100/50 rounded-2xl border-2 border-emerald-200 shadow-md p-8">
          <h3 className="text-2xl font-bold text-emerald-900 mb-8 flex items-center gap-3">
            <span className="text-3xl">📦</span> Add New Product
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              { label: 'Product Name *', key: 'item', type: 'text', placeholder: 'e.g., Toluene' },
              { label: 'Safety Stock', key: 'safety_stock', type: 'number' },
              { label: 'Reorder Point', key: 'reorder_point', type: 'number' },
              { label: 'Max Storage Days', key: 'max_storage_days', type: 'number' },
              { label: 'Max Inventory Days', key: 'max_inventory_days', type: 'number' },
              { label: 'Monthly Target Volume', key: 'monthly_target_volume', type: 'number' },
            ].map((field) => (
              <div key={field.key}>
                <label className="block text-sm font-bold text-emerald-900 mb-2">
                  {field.label}
                </label>
                <input
                  type={field.type}
                  value={
                    newProduct[field.key as keyof ProductSetting] !== null &&
                    newProduct[field.key as keyof ProductSetting] !== undefined
                      ? newProduct[field.key as keyof ProductSetting]
                      : ''
                  }
                  onChange={(e) =>
                    handleInputChange(
                      field.key as keyof ProductSetting,
                      field.type === 'number'
                        ? e.target.value
                          ? Number(e.target.value)
                          : null
                        : e.target.value,
                      false
                    )
                  }
                  placeholder={field.placeholder || ''}
                  className="w-full px-4 py-2.5 border-2 border-emerald-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent bg-white font-medium"
                />
              </div>
            ))}
          </div>
          <div className="mt-8 flex gap-4">
            <button
              onClick={handleAddProduct}
              className="px-8 py-3 bg-gradient-to-r from-emerald-500 to-green-500 text-white font-bold rounded-xl hover:shadow-lg transition-all duration-300 hover:scale-105"
            >
              ✓ Save Product
            </button>
            <button
              onClick={() => setShowAddForm(false)}
              className="px-8 py-3 bg-white text-slate-700 font-bold rounded-xl border-2 border-slate-200 hover:shadow-lg transition-all duration-300"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Settings Table */}
      {settings.length > 0 ? (
        <div className="bg-gradient-to-br from-white to-slate-50 rounded-2xl shadow-lg border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-gradient-to-r from-slate-100 to-slate-50 border-b-2 border-slate-200">
                <tr>
                  {['Product Name', 'Safety Stock', 'Reorder Point', 'Max Storage Days', 'Max Inventory Days', 'Monthly Target', 'Actions'].map(
                    (header, idx) => (
                      <th
                        key={idx}
                        className={`px-6 py-4 text-xs font-bold text-slate-600 uppercase tracking-wider ${
                          idx === 0 ? 'rounded-tl-lg' : ''
                        } ${idx === 6 ? 'rounded-tr-lg' : ''}`}
                      >
                        {header}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {settings.map((setting, index) => (
                  <tr
                    key={setting.id}
                    className="hover:bg-gradient-to-r hover:from-slate-50 hover:to-blue-50/30 transition-all duration-200"
                  >
                    {editingId === setting.id ? (
                      <>
                        <td className="px-6 py-4 text-sm font-semibold text-slate-800">
                          {setting.item}
                        </td>
                        {['safety_stock', 'reorder_point', 'max_storage_days', 'max_inventory_days', 'monthly_target_volume'].map(
                          (field) => (
                            <td key={field} className="px-6 py-4">
                              <input
                                type="number"
                                value={
                                  editForm[field as keyof ProductSetting] !== null &&
                                  editForm[field as keyof ProductSetting] !== undefined
                                    ? editForm[field as keyof ProductSetting]
                                    : ''
                                }
                                onChange={(e) =>
                                  handleInputChange(
                                    field as keyof ProductSetting,
                                    e.target.value ? Number(e.target.value) : null,
                                    true
                                  )
                                }
                                className="w-full px-3 py-2 border-2 border-blue-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm font-medium"
                              />
                            </td>
                          )
                        )}
                        <td className="px-6 py-4 text-sm">
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleSave(setting.id!)}
                              className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-green-500 text-white font-bold rounded-lg hover:shadow-lg transition-all text-xs"
                            >
                              ✓ Save
                            </button>
                            <button
                              onClick={handleCancelEdit}
                              className="px-4 py-2 bg-slate-200 text-slate-700 font-bold rounded-lg hover:bg-slate-300 transition-all text-xs"
                            >
                              Cancel
                            </button>
                          </div>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-6 py-4 text-sm font-semibold text-slate-800">
                          {setting.item}
                        </td>
                        {['safety_stock', 'reorder_point', 'max_storage_days', 'max_inventory_days', 'monthly_target_volume'].map(
                          (field) => (
                            <td key={field} className="px-6 py-4 text-sm text-slate-700">
                              {setting[field as keyof ProductSetting] !== null &&
                              setting[field as keyof ProductSetting] !== undefined
                                ? setting[field as keyof ProductSetting]
                                : '-'}
                            </td>
                          )
                        )}
                        <td className="px-6 py-4 text-sm">
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleEdit(setting)}
                              className="px-4 py-2 bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-bold rounded-lg hover:shadow-lg transition-all text-xs"
                            >
                              ✎ Edit
                            </button>
                            <button
                              onClick={() => handleDelete(setting.id!)}
                              className="px-4 py-2 bg-gradient-to-r from-rose-500 to-red-500 text-white font-bold rounded-lg hover:shadow-lg transition-all text-xs"
                            >
                              🗑️ Delete
                            </button>
                          </div>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-gradient-to-br from-white to-slate-50 rounded-2xl shadow-lg border-2 border-dashed border-slate-300 p-16 text-center">
          <p className="text-3xl mb-4">📋</p>
          <p className="text-2xl font-bold text-slate-800 mb-2">No Products Yet</p>
          <p className="text-slate-600 font-medium mb-8">Click "Add Product" above to create your first product setting</p>
          <button
            onClick={() => setShowAddForm(true)}
            className="px-8 py-3 bg-gradient-to-r from-emerald-500 to-green-500 text-white font-bold rounded-xl hover:shadow-lg transition-all duration-300 hover:scale-105"
          >
            + Add First Product
          </button>
        </div>
      )}
    </div>
  );
};

export default ProductSettings;
