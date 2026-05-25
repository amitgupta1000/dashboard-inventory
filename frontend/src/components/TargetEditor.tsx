import { useState, useEffect } from 'react';
import { X, Edit2, Save, History, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

interface Target {
  id: number;
  commodity_id: number;
  commodity_name: string;
  config_date: string;
  desired_stock_level: number | null;
  min_stock_level: number | null;
  max_stock_level: number | null;
  target_inventory_days: number | null;
  is_finalized: boolean;
  notes: string | null;
}

interface TargetEditorProps {
  isOpen: boolean;
  onClose?: () => void;
  onSaveSuccess?: () => void;
}

const TargetEditor: React.FC<TargetEditorProps> = ({ isOpen, onClose, onSaveSuccess }) => {
  const [targets, setTargets] = useState<Target[]>([]);
  const [loading, setLoading] = useState(false);
  const [saveStatus, setSaveStatus] = useState<{
    type: 'idle' | 'saving' | 'success' | 'error';
    message: string;
  }>({ type: 'idle', message: '' });
  const [editedTargets, setEditedTargets] = useState<Map<number, Partial<Target>>>(new Map());
  const [showHistory, setShowHistory] = useState<number | null>(null);
  const [history, setHistory] = useState<Target[]>([]);

  useEffect(() => {
    if (isOpen) {
      fetchTargets();
    }
  }, [isOpen]);

  const fetchTargets = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/targets`);
      if (response.data.success) {
        setTargets(response.data.data);
      }
    } catch (error) {
      setSaveStatus({
        type: 'error',
        message: 'Failed to load targets'
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async (commodityId: number) => {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/targets/history/${commodityId}`
      );
      if (response.data.success) {
        setHistory(response.data.history);
        setShowHistory(commodityId);
      }
    } catch (error) {
      setSaveStatus({
        type: 'error',
        message: 'Failed to load history'
      });
    }
  };

  const handleEdit = (target: Target, field: keyof Target, value: any) => {
    const key = target.id;
    const current = editedTargets.get(key) || { ...target };
    current[field] = value;
    setEditedTargets(new Map(editedTargets.set(key, current)));
  };

  const hasChanges = editedTargets.size > 0;

  const handleSave = async () => {
    if (!hasChanges) return;

    setSaveStatus({ type: 'saving', message: 'Saving targets...' });

    try {
      let savedCount = 0;
      for (const [targetId, updates] of editedTargets.entries()) {
        const target = targets.find(t => t.id === targetId);
        if (!target) continue;

        await axios.put(`${API_BASE_URL}/api/targets/${target.commodity_id}`, {
          desired_stock_level: updates.desired_stock_level ?? target.desired_stock_level,
          min_stock_level: updates.min_stock_level ?? target.min_stock_level,
          max_stock_level: updates.max_stock_level ?? target.max_stock_level,
          target_inventory_days: updates.target_inventory_days ?? target.target_inventory_days,
          is_finalized: updates.is_finalized ?? target.is_finalized,
          notes: updates.notes ?? target.notes
        });
        savedCount++;
      }

      setSaveStatus({
        type: 'success',
        message: `Saved ${savedCount} target${savedCount !== 1 ? 's' : ''}`
      });

      setEditedTargets(new Map());
      await fetchTargets();
      onSaveSuccess?.();

      setTimeout(() => {
        setSaveStatus({ type: 'idle', message: '' });
      }, 3000);
    } catch (error: any) {
      setSaveStatus({
        type: 'error',
        message: error.response?.data?.detail || 'Failed to save targets'
      });
    }
  };

  if (!isOpen) return null;

  const getEditValue = (target: Target, field: keyof Target) => {
    const edited = editedTargets.get(target.id);
    return edited && field in edited ? edited[field] : target[field];
  };

  const isEdited = (target: Target) => editedTargets.has(target.id);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="sticky top-0 bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6 shadow-md flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white bg-opacity-20 rounded-lg">
                <Edit2 className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-2xl font-bold">Target Editor</h2>
                <p className="text-sm text-blue-100">
                  {targets.length} commodities • Changes create new versions with today's date
                </p>
              </div>
            </div>
            {onClose && (
              <button
                onClick={onClose}
                className="p-2 hover:bg-blue-700 rounded-lg transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            )}
          </div>

          {/* Content */}
          <div className="p-6 space-y-4">
            {/* Status Alert */}
            {saveStatus.type !== 'idle' && (
              <div
                className={`p-4 rounded-lg border flex items-start gap-3 ${
                  saveStatus.type === 'success'
                    ? 'bg-green-50 border-green-200 text-green-800'
                    : saveStatus.type === 'error'
                    ? 'bg-red-50 border-red-200 text-red-800'
                    : 'bg-blue-50 border-blue-200 text-blue-800'
                }`}
              >
                {saveStatus.type === 'success' ? (
                  <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                ) : saveStatus.type === 'error' ? (
                  <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                ) : (
                  <Loader className="w-5 h-5 flex-shrink-0 mt-0.5 animate-spin" />
                )}
                <div className="flex-1">
                  <div className="font-semibold">{saveStatus.message}</div>
                </div>
              </div>
            )}

            {/* History Modal */}
            {showHistory && (
              <div className="fixed inset-0 bg-black bg-opacity-70 z-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto">
                  <div className="sticky top-0 bg-gradient-to-r from-purple-600 to-pink-600 text-white p-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <History className="w-5 h-5" />
                      <h3 className="font-bold">
                        {history[0]?.commodity_name} - Version History
                      </h3>
                    </div>
                    <button
                      onClick={() => setShowHistory(null)}
                      className="p-1 hover:bg-pink-700 rounded-lg"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  <div className="p-4 space-y-2">
                    {history.map((h, idx) => (
                      <div
                        key={idx}
                        className="p-3 border border-gray-200 rounded-lg bg-gray-50"
                      >
                        <div className="text-sm font-semibold text-gray-700">
                          {h.config_date}
                          {idx === 0 && (
                            <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                              Current
                            </span>
                          )}
                        </div>
                        <div className="grid grid-cols-2 gap-2 mt-2 text-xs text-gray-600">
                          <div>Desired: {h.desired_stock_level || '-'}</div>
                          <div>Min: {h.min_stock_level || '-'}</div>
                          <div>Max: {h.max_stock_level || '-'}</div>
                          <div>Days: {h.target_inventory_days || '-'}</div>
                        </div>
                        {h.notes && (
                          <div className="mt-2 text-xs text-gray-600 italic">
                            Note: {h.notes}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Targets Table */}
            {loading ? (
              <div className="flex justify-center py-8">
                <Loader className="w-6 h-6 text-blue-600 animate-spin" />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-gray-100 border-b-2 border-gray-300">
                      <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">
                        Commodity
                      </th>
                      <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">
                        Desired Stock
                      </th>
                      <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">
                        Min Level
                      </th>
                      <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">
                        Max Level
                      </th>
                      <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">
                        Target Days
                      </th>
                      <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {targets.map((target) => (
                      <tr
                        key={target.id}
                        className={`border-b transition-colors ${
                          isEdited(target)
                            ? 'bg-blue-50'
                            : 'bg-white hover:bg-gray-50'
                        }`}
                      >
                        <td className="px-4 py-3 text-sm font-semibold text-gray-800">
                          {target.commodity_name}
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="number"
                            value={getEditValue(target, 'desired_stock_level') || ''}
                            onChange={(e) =>
                              handleEdit(
                                target,
                                'desired_stock_level',
                                e.target.value ? parseFloat(e.target.value) : null
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="-"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="number"
                            value={getEditValue(target, 'min_stock_level') || ''}
                            onChange={(e) =>
                              handleEdit(
                                target,
                                'min_stock_level',
                                e.target.value ? parseFloat(e.target.value) : null
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="-"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="number"
                            value={getEditValue(target, 'max_stock_level') || ''}
                            onChange={(e) =>
                              handleEdit(
                                target,
                                'max_stock_level',
                                e.target.value ? parseFloat(e.target.value) : null
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="-"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="number"
                            value={getEditValue(target, 'target_inventory_days') || ''}
                            onChange={(e) =>
                              handleEdit(
                                target,
                                'target_inventory_days',
                                e.target.value ? parseFloat(e.target.value) : null
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="-"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => fetchHistory(target.commodity_id)}
                            className="text-purple-600 hover:text-purple-800 font-semibold text-sm"
                            title="View version history"
                          >
                            <History className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Footer */}
            <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 p-4 flex items-center justify-between">
              <div className="text-sm text-gray-600">
                {hasChanges ? (
                  <span className="text-blue-600 font-semibold">
                    {editedTargets.size} target{editedTargets.size !== 1 ? 's' : ''} modified
                  </span>
                ) : (
                  <span>No changes</span>
                )}
              </div>
              <div className="flex gap-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors font-semibold"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={!hasChanges || saveStatus.type === 'saving'}
                  className={`px-4 py-2 rounded-lg font-semibold flex items-center gap-2 transition-colors ${
                    hasChanges && saveStatus.type !== 'saving'
                      ? 'bg-green-600 text-white hover:bg-green-700'
                      : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }`}
                >
                  <Save className="w-4 h-4" />
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default TargetEditor;
