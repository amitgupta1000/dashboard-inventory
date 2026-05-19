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
      <div className="flex items-center justify-center p-8">
        <div className="text-xl text-gray-600">Loading product settings...</div>
      </div>
    );
  }

  if (error) {
    return (
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
          <p className="text-lg text-gray-600 mb-4">⚙️ Cannot load product settings</p>
          <button
            onClick={fetchSettings}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
          >
            🔄 Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-semibold text-gray-800">Product Settings</h2>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
        >
          {showAddForm ? 'Cancel' : '+ Add Product'}
        </button>
      </div>

      {showAddForm && (
        <div className="mb-6 p-4 bg-blue-50 rounded-lg border-2 border-blue-200">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">Add New Product</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Product Name *
              </label>
              <input
                type="text"
                value={newProduct.item || ''}
                onChange={(e) => handleInputChange('item', e.target.value, false)}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Toluene"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Safety Stock
              </label>
              <input
                type="number"
                value={newProduct.safety_stock !== null ? newProduct.safety_stock : ''}
                onChange={(e) =>
                  handleInputChange('safety_stock', e.target.value ? Number(e.target.value) : null, false)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Reorder Point
              </label>
              <input
                type="number"
                value={newProduct.reorder_point !== null ? newProduct.reorder_point : ''}
                onChange={(e) =>
                  handleInputChange('reorder_point', e.target.value ? Number(e.target.value) : null, false)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max Storage Days
              </label>
              <input
                type="number"
                value={newProduct.max_storage_days !== null ? newProduct.max_storage_days : ''}
                onChange={(e) =>
                  handleInputChange('max_storage_days', e.target.value ? Number(e.target.value) : null, false)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max Inventory Days
              </label>
              <input
                type="number"
                value={newProduct.max_inventory_days !== null ? newProduct.max_inventory_days : ''}
                onChange={(e) =>
                  handleInputChange('max_inventory_days', e.target.value ? Number(e.target.value) : null, false)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Monthly Target Volume
              </label>
              <input
                type="number"
                value={newProduct.monthly_target_volume !== null ? newProduct.monthly_target_volume : ''}
                onChange={(e) =>
                  handleInputChange('monthly_target_volume', e.target.value ? Number(e.target.value) : null, false)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              onClick={handleAddProduct}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
            >
              Save Product
            </button>
            <button
              onClick={() => setShowAddForm(false)}
              className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-blue-500">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold text-white">Product Name</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-white">Safety Stock</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-white">Reorder Point</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-white">Max Storage Days</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-white">Max Inventory Days</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-white">Monthly Target</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-white">Actions</th>
            </tr>
          </thead>
          <tbody>
            {settings.map((setting, index) => (
              <tr
                key={setting.id}
                className={`${
                  index % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                } hover:bg-blue-50 transition-colors`}
              >
                {renderEditableCell(setting, 'item', false)}
                {renderEditableCell(setting, 'safety_stock', true)}
                {renderEditableCell(setting, 'reorder_point', true)}
                {renderEditableCell(setting, 'max_storage_days', true)}
                {renderEditableCell(setting, 'max_inventory_days', true)}
                {renderEditableCell(setting, 'monthly_target_volume', true)}
                <td className="px-4 py-3 text-sm border-b border-gray-200">
                  {editingId === setting.id ? (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleSave(setting.id!)}
                        className="px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600 text-xs"
                      >
                        Save
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="px-3 py-1 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 text-xs"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEdit(setting)}
                        className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-xs"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(setting.id!)}
                        className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 text-xs"
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {settings.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          No product settings found. Click "Add Product" to create one.
        </div>
      )}
    </div>
  );
};

export default ProductSettings;
