import { useState } from 'react';
import {
  Upload, Zap, BarChart3, Target, ExternalLink, 
  X, CheckCircle, AlertCircle, Loader
} from 'lucide-react';
import axios from 'axios';
import TargetEditor from './TargetEditor';

const API_BASE_URL = 'http://localhost:8000';

interface UploadStatus {
  type: 'inventory' | 'prices' | 'sales' | null;
  status: 'idle' | 'uploading' | 'success' | 'error';
  message: string;
  fileName: string;
}

interface UploadPanelProps {
  isOpen: boolean;
  onClose?: () => void;
  onUploadSuccess?: (type: string) => void;
}

const UploadPanel: React.FC<UploadPanelProps> = ({ isOpen, onClose, onUploadSuccess }) => {
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({
    type: null,
    status: 'idle',
    message: '',
    fileName: ''
  });
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [showTargetEditor, setShowTargetEditor] = useState(false);

  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>,
    uploadType: 'inventory' | 'prices' | 'sales'
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const endpoint = {
      inventory: '/api/uploads/inventory',
      prices: '/api/uploads/prices',
      sales: '/api/uploads/sales-register'
    }[uploadType];

    try {
      setUploadStatus({
        type: uploadType,
        status: 'uploading',
        message: `Uploading ${file.name}...`,
        fileName: file.name
      });

      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_BASE_URL}${endpoint}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data.success) {
        setUploadStatus({
          type: uploadType,
          status: 'success',
          message: response.data.message,
          fileName: file.name
        });

        onUploadSuccess?.(uploadType);

        // Reset after 3 seconds
        setTimeout(() => {
          setUploadStatus({
            type: null,
            status: 'idle',
            message: '',
            fileName: ''
          });
        }, 3000);
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || 'Upload failed';
      setUploadStatus({
        type: uploadType,
        status: 'error',
        message: errorMsg,
        fileName: file.name
      });
    }

    // Reset file input
    event.target.value = '';
  };

  const UploadButton: React.FC<{
    icon: React.ReactNode;
    title: string;
    description: string;
    uploadType: 'inventory' | 'prices' | 'sales';
    isLoading?: boolean;
  }> = ({ icon, title, description, uploadType, isLoading }) => (
    <label className="cursor-pointer">
      <input
        type="file"
        accept=".xlsx,.csv,.xls"
        onChange={(e) => handleFileUpload(e, uploadType)}
        className="hidden"
        disabled={isLoading}
      />
      <div className="flex items-center gap-4 p-4 rounded-xl bg-gradient-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 transition-all border border-blue-200 hover:border-blue-400 hover:shadow-md cursor-pointer">
        <div className="p-3 rounded-lg bg-white shadow-sm">
          {isLoading ? (
            <Loader className="w-6 h-6 text-blue-500 animate-spin" />
          ) : (
            <>{icon}</>
          )}
        </div>
        <div className="flex-1">
          <div className="font-semibold text-gray-800">{title}</div>
          <div className="text-sm text-gray-600">{description}</div>
        </div>
        <Upload className="w-5 h-5 text-blue-500 flex-shrink-0" />
      </div>
    </label>
  );

  const ActionButton: React.FC<{
    icon: React.ReactNode;
    title: string;
    description: string;
    onClick?: () => void;
    isExternal?: boolean;
  }> = ({ icon, title, description, onClick, isExternal }) => (
    <div 
      onClick={onClick}
      className={`flex items-center gap-4 p-4 rounded-xl transition-all border cursor-pointer ${
        isExternal
          ? 'bg-gradient-to-r from-amber-50 to-orange-50 hover:from-amber-100 hover:to-orange-100 border-amber-200 hover:border-amber-400 hover:shadow-md'
          : 'bg-gradient-to-r from-green-50 to-teal-50 hover:from-green-100 hover:to-teal-100 border-green-200 hover:border-green-400 hover:shadow-md'
      }`}
    >
      <div className="p-3 rounded-lg bg-white shadow-sm">
        {icon}
      </div>
      <div className="flex-1">
        <div className="font-semibold text-gray-800">{title}</div>
        <div className="text-sm text-gray-600">{description}</div>
      </div>
      {isExternal ? (
        <ExternalLink className="w-5 h-5 text-amber-500 flex-shrink-0" />
      ) : (
        <Zap className="w-5 h-5 text-green-500 flex-shrink-0" />
      )}
    </div>
  );

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="sticky top-0 bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6 shadow-md flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white bg-opacity-20 rounded-lg">
                <Upload className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-2xl font-bold">Data Management Hub</h2>
                <p className="text-sm text-blue-100">Upload files and manage your inventory data</p>
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
          <div className="p-6 space-y-6">
            {/* Upload Status Alert */}
            {uploadStatus.status !== 'idle' && (
              <div className={`p-4 rounded-lg border flex items-start gap-3 ${
                uploadStatus.status === 'success'
                  ? 'bg-green-50 border-green-200 text-green-800'
                  : uploadStatus.status === 'error'
                  ? 'bg-red-50 border-red-200 text-red-800'
                  : 'bg-blue-50 border-blue-200 text-blue-800'
              }`}>
                {uploadStatus.status === 'success' ? (
                  <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                ) : uploadStatus.status === 'error' ? (
                  <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                ) : (
                  <Loader className="w-5 h-5 flex-shrink-0 mt-0.5 animate-spin" />
                )}
                <div className="flex-1">
                  <div className="font-semibold">{uploadStatus.message}</div>
                  <div className="text-sm opacity-75">{uploadStatus.fileName}</div>
                </div>
              </div>
            )}

            {/* Upload Section */}
            <div>
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="text-2xl">📤</span>
                File Uploads
              </h3>
              <div className="grid grid-cols-1 gap-3">
                <UploadButton
                  icon={<BarChart3 className="w-6 h-6 text-blue-600" />}
                  title="Upload Inventory"
                  description="Daily stock levels by commodity"
                  uploadType="inventory"
                  isLoading={uploadStatus.type === 'inventory' && uploadStatus.status === 'uploading'}
                />
                <UploadButton
                  icon={<Target className="w-6 h-6 text-indigo-600" />}
                  title="Upload Market Prices"
                  description="Current prices & replacement costs"
                  uploadType="prices"
                  isLoading={uploadStatus.type === 'prices' && uploadStatus.status === 'uploading'}
                />
                <UploadButton
                  icon={<Upload className="w-6 h-6 text-purple-600" />}
                  title="Upload Sales Register"
                  description="Recent sales transactions"
                  uploadType="sales"
                  isLoading={uploadStatus.type === 'sales' && uploadStatus.status === 'uploading'}
                />
              </div>
            </div>

            {/* Configuration Section */}
            <div>
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="text-2xl">⚙️</span>
                Configuration
              </h3>
              <ActionButton
                icon={<Target className="w-6 h-6 text-green-600" />}
                title="Review & Update Targets"
                description="Manage safety stock & reorder points"
                onClick={() => setShowTargetEditor(true)}
              />
            </div>

            {/* Analytics Section */}
            <div>
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="text-2xl">📊</span>
                Analytics & Actions
              </h3>
              <div className="grid grid-cols-1 gap-3">
                <ActionButton
                  icon={<Zap className="w-6 h-6 text-green-600" />}
                  title="Generate Refreshed Insights"
                  description="Compute stock warnings & recommendations"
                  onClick={() => alert('Insights generation coming soon!')}
                />
                <ActionButton
                  icon={<ExternalLink className="w-6 h-6 text-amber-600" />}
                  title="Connect to Suppliers"
                  description="Link to supplier management system"
                  isExternal={true}
                  onClick={() => alert('Supplier integration coming soon!')}
                />
              </div>
            </div>

            {/* Footer */}
            <div className="pt-4 border-t border-gray-200">
              <p className="text-xs text-gray-500 text-center">
                All uploads are securely stored in Google Cloud Storage
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Target Editor Modal */}
      <TargetEditor
        isOpen={showTargetEditor}
        onClose={() => setShowTargetEditor(false)}
        onSaveSuccess={() => {
          setShowTargetEditor(false);
          onUploadSuccess?.('targets');
        }}
      />
    </>
  );
};

export default UploadPanel;
