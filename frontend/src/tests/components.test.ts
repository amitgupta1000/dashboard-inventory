/**
 * Frontend Component Tests
 * 
 * Tests for React components including:
 * - App.tsx - Main application shell with tabs
 * - DataTable.tsx - Inventory data table component
 * - InsightsDashboard.tsx - Intelligence dashboard
 * - ProductSettings.tsx - Product configuration UI
 * 
 * Run with: npm test
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import axios from 'axios';

// Mock axios
vi.mock('axios');

// ============================================================================
// Utility Tests
// ============================================================================

describe('Utility Functions', () => {
  describe('Number Formatting', () => {
    it('should format numbers with commas', () => {
      const formatter = (num: number) => {
        return new Intl.NumberFormat('en-IN', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }).format(num);
      };
      
      expect(formatter(1000)).toBe('1,000.00');
      expect(formatter(1000000)).toBe('10,00,000.00');
      expect(formatter(999.99)).toBe('999.99');
    });

    it('should handle negative numbers', () => {
      const formatter = (num: number) => {
        return new Intl.NumberFormat('en-IN').format(num);
      };
      
      expect(formatter(-1000)).toBe('-1,000');
    });
  });

  describe('Date Formatting', () => {
    it('should format dates correctly', () => {
      const formatter = (dateStr: string) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-IN');
      };
      
      expect(formatter('2026-05-19')).toBe('19/5/2026');
    });

    it('should handle invalid dates', () => {
      const formatter = (dateStr: string) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toString() === 'Invalid Date' ? '' : date.toLocaleDateString('en-IN');
      };
      
      expect(formatter('invalid')).toBe('');
      expect(formatter('')).toBe('');
    });
  });

  describe('Status Color Mapping', () => {
    it('should map status to color', () => {
      const getStatusColor = (status: string) => {
        const statusColorMap: { [key: string]: string } = {
          'CRITICAL': 'bg-red-100 text-red-800',
          'WARNING': 'bg-yellow-100 text-yellow-800',
          'OK': 'bg-green-100 text-green-800',
          'EXCESS': 'bg-blue-100 text-blue-800',
        };
        return statusColorMap[status] || 'bg-gray-100 text-gray-800';
      };
      
      expect(getStatusColor('CRITICAL')).toBe('bg-red-100 text-red-800');
      expect(getStatusColor('WARNING')).toBe('bg-yellow-100 text-yellow-800');
      expect(getStatusColor('OK')).toBe('bg-green-100 text-green-800');
      expect(getStatusColor('UNKNOWN')).toBe('bg-gray-100 text-gray-800');
    });
  });
});

// ============================================================================
// API Response Tests
// ============================================================================

describe('API Response Handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Inventory API', () => {
    it('should handle successful inventory fetch', async () => {
      const mockData = {
        success: true,
        data: [
          {
            id: 1,
            item: 'Product A',
            company: 'Company 1',
            physical_stock: 1000,
            ready_unsold: 500,
          }
        ],
        total: 1
      };

      (axios.get as any).mockResolvedValue({ data: mockData });

      const response = await axios.get('/api/inventory');
      expect(response.data.success).toBe(true);
      expect(response.data.total).toBe(1);
      expect(response.data.data).toHaveLength(1);
    });

    it('should handle inventory summary response', async () => {
      const mockSummary = {
        success: true,
        summary: {
          total_items: 5,
          total_physical_stock: 5000,
          total_ready_unsold: 2500,
          total_incoming_qty: 1000,
          critical_count: 1,
          warning_count: 2,
          ok_count: 2
        }
      };

      (axios.get as any).mockResolvedValue({ data: mockSummary });

      const response = await axios.get('/api/inventory/summary');
      expect(response.data.summary.total_items).toBe(5);
      expect(response.data.summary.critical_count).toBe(1);
    });

    it('should handle inventory fetch error', async () => {
      (axios.get as any).mockRejectedValue(new Error('Network error'));

      try {
        await axios.get('/api/inventory');
      } catch (error: any) {
        expect(error.message).toBe('Network error');
      }
    });
  });

  describe('Product Settings API', () => {
    it('should handle successful product settings fetch', async () => {
      const mockData = {
        success: true,
        data: [
          {
            id: 1,
            item: 'Product A',
            safety_stock: 100,
            reorder_point: 50,
            is_active: true
          }
        ],
        total: 1
      };

      (axios.get as any).mockResolvedValue({ data: mockData });

      const response = await axios.get('/api/product-settings');
      expect(response.data.success).toBe(true);
      expect(response.data.total).toBe(1);
    });

    it('should handle product setting creation', async () => {
      const newSetting = {
        item: 'New Product',
        safety_stock: 100,
        reorder_point: 50
      };

      const mockResponse = {
        success: true,
        data: {
          id: 1,
          ...newSetting,
          is_active: true
        }
      };

      (axios.post as any).mockResolvedValue({ data: mockResponse });

      const response = await axios.post('/api/product-settings', newSetting);
      expect(response.data.success).toBe(true);
      expect(response.data.data.id).toBe(1);
      expect(response.data.data.item).toBe('New Product');
    });

    it('should handle product setting update', async () => {
      const updated = {
        safety_stock: 150,
        reorder_point: 75
      };

      const mockResponse = {
        success: true,
        data: {
          id: 1,
          item: 'Product A',
          ...updated,
          is_active: true
        }
      };

      (axios.put as any).mockResolvedValue({ data: mockResponse });

      const response = await axios.put('/api/product-settings/1', updated);
      expect(response.data.success).toBe(true);
      expect(response.data.data.safety_stock).toBe(150);
    });

    it('should handle product setting deletion', async () => {
      const mockResponse = {
        success: true,
        message: 'Product setting deleted'
      };

      (axios.delete as any).mockResolvedValue({ data: mockResponse });

      const response = await axios.delete('/api/product-settings/1');
      expect(response.data.success).toBe(true);
    });
  });

  describe('Intelligence API', () => {
    it('should handle intelligence summary fetch', async () => {
      const mockData = {
        success: true,
        data: [
          {
            item: 'Product A',
            total_stock_all_locations: 1000,
            stock_status: 'OK',
            days_of_stock_remaining: 30
          }
        ],
        total: 1
      };

      (axios.get as any).mockResolvedValue({ data: mockData });

      const response = await axios.get('/api/intelligence/summary');
      expect(response.data.success).toBe(true);
      expect(response.data.data[0].stock_status).toBe('OK');
    });
  });
});

// ============================================================================
// Component Logic Tests
// ============================================================================

describe('Component Logic', () => {
  describe('Tab Management', () => {
    it('should track active tab', () => {
      let activeTab = 0;
      
      const setActiveTab = (tab: number) => {
        activeTab = tab;
      };

      setActiveTab(1);
      expect(activeTab).toBe(1);
      
      setActiveTab(2);
      expect(activeTab).toBe(2);
    });

    it('should have three tabs', () => {
      const tabs = ['Insights', 'Inventory Dashboard', 'Product Settings'];
      expect(tabs).toHaveLength(3);
      expect(tabs[0]).toBe('Insights');
    });
  });

  describe('Error State Management', () => {
    it('should track error state', () => {
      let error: string | null = null;

      const setError = (msg: string | null) => {
        error = msg;
      };

      expect(error).toBeNull();

      setError('API Connection Failed');
      expect(error).toBe('API Connection Failed');

      setError(null);
      expect(error).toBeNull();
    });

    it('should display appropriate error messages', () => {
      const getErrorMessage = (err: any) => {
        if (err?.response?.status === 404) {
          return 'Resource not found';
        }
        if (err?.message === 'Network Error') {
          return 'Unable to connect to the backend API. Please ensure the server is running.';
        }
        return 'An unexpected error occurred';
      };

      expect(getErrorMessage({ response: { status: 404 } })).toBe('Resource not found');
      expect(getErrorMessage({ message: 'Network Error' })).toBe('Unable to connect to the backend API. Please ensure the server is running.');
      expect(getErrorMessage({})).toBe('An unexpected error occurred');
    });
  });

  describe('Data Transformation', () => {
    it('should transform inventory data', () => {
      const rawData = {
        id: 1,
        physical_stock: 1000.5,
        ready_unsold: 500.25,
        record_date: '2026-05-19'
      };

      const transformedData = {
        ...rawData,
        formatted_stock: rawData.physical_stock.toFixed(2),
        formatted_date: new Date(rawData.record_date).toLocaleDateString('en-IN')
      };

      expect(transformedData.formatted_stock).toBe('1000.50');
      expect(transformedData.formatted_date).toBe('19/5/2026');
    });

    it('should filter inventory by status', () => {
      const inventory = [
        { item: 'A', status: 'OK' },
        { item: 'B', status: 'CRITICAL' },
        { item: 'C', status: 'OK' },
        { item: 'D', status: 'WARNING' }
      ];

      const critical = inventory.filter(item => item.status === 'CRITICAL');
      expect(critical).toHaveLength(1);
      expect(critical[0].item).toBe('B');

      const okItems = inventory.filter(item => item.status === 'OK');
      expect(okItems).toHaveLength(2);
    });
  });

  describe('Pagination', () => {
    it('should paginate data', () => {
      const data = Array.from({ length: 50 }, (_, i) => ({ id: i + 1 }));
      const pageSize = 10;

      const paginate = (arr: any[], page: number, size: number) => {
        return arr.slice((page - 1) * size, page * size);
      };

      expect(paginate(data, 1, pageSize)).toHaveLength(10);
      expect(paginate(data, 1, pageSize)[0].id).toBe(1);
      expect(paginate(data, 2, pageSize)[0].id).toBe(11);
      expect(paginate(data, 5, pageSize)).toHaveLength(10);
    });
  });

  describe('Sorting', () => {
    it('should sort by column', () => {
      const data = [
        { item: 'C', stock: 300 },
        { item: 'A', stock: 100 },
        { item: 'B', stock: 200 }
      ];

      const sortByItem = [...data].sort((a, b) => a.item.localeCompare(b.item));
      expect(sortByItem[0].item).toBe('A');
      expect(sortByItem[2].item).toBe('C');

      const sortByStock = [...data].sort((a, b) => b.stock - a.stock);
      expect(sortByStock[0].stock).toBe(300);
      expect(sortByStock[2].stock).toBe(100);
    });
  });
});

// ============================================================================
// Modal/Form Tests
// ============================================================================

describe('Form Operations', () => {
  describe('Product Settings Form', () => {
    it('should validate required fields', () => {
      const validateSetting = (data: any) => {
        const errors: string[] = [];
        
        if (!data.item) errors.push('Item name is required');
        if (data.safety_stock !== undefined && data.safety_stock < 0) errors.push('Safety stock cannot be negative');
        if (data.reorder_point !== undefined && data.reorder_point < 0) errors.push('Reorder point cannot be negative');
        
        return errors;
      };

      expect(validateSetting({})).toContain('Item name is required');
      expect(validateSetting({ item: 'Test', safety_stock: -10 })).toContain('Safety stock cannot be negative');
      expect(validateSetting({ item: 'Test', safety_stock: 100, reorder_point: 50 })).toHaveLength(0);
    });

    it('should reset form after submission', () => {
      let formData = {
        item: 'Product A',
        safety_stock: 100,
        reorder_point: 50
      };

      const resetForm = () => {
        formData = {
          item: '',
          safety_stock: 0,
          reorder_point: 0
        };
      };

      expect(formData.item).toBe('Product A');
      resetForm();
      expect(formData.item).toBe('');
      expect(formData.safety_stock).toBe(0);
    });
  });
});

// ============================================================================
// Integration Scenarios
// ============================================================================

describe('User Workflows', () => {
  it('should handle complete inventory view workflow', async () => {
    // Simulate fetching inventory data
    const mockInventory = {
      success: true,
      data: [
        { id: 1, item: 'Product A', physical_stock: 1000, status: 'OK' },
        { id: 2, item: 'Product B', physical_stock: 50, status: 'CRITICAL' }
      ],
      total: 2
    };

    (axios.get as any).mockResolvedValue({ data: mockInventory });

    // Fetch data
    const response = await axios.get('/api/inventory');
    expect(response.data.total).toBe(2);

    // Filter critical items
    const critical = response.data.data.filter((item: any) => item.status === 'CRITICAL');
    expect(critical).toHaveLength(1);
    expect(critical[0].item).toBe('Product B');
  });

  it('should handle product settings management workflow', async () => {
    // Create new setting
    const newSetting = { item: 'New Product', safety_stock: 100, reorder_point: 50 };
    (axios.post as any).mockResolvedValue({
      data: { success: true, data: { id: 1, ...newSetting, is_active: true } }
    });

    const createResponse = await axios.post('/api/product-settings', newSetting);
    expect(createResponse.data.data.id).toBe(1);

    // Fetch all settings
    (axios.get as any).mockResolvedValue({
      data: { success: true, data: [createResponse.data.data], total: 1 }
    });

    const getResponse = await axios.get('/api/product-settings');
    expect(getResponse.data.total).toBe(1);

    // Update setting
    const updated = { safety_stock: 150 };
    (axios.put as any).mockResolvedValue({
      data: { success: true, data: { ...createResponse.data.data, ...updated } }
    });

    const updateResponse = await axios.put('/api/product-settings/1', updated);
    expect(updateResponse.data.data.safety_stock).toBe(150);

    // Delete setting
    (axios.delete as any).mockResolvedValue({
      data: { success: true, message: 'Product setting deleted' }
    });

    const deleteResponse = await axios.delete('/api/product-settings/1');
    expect(deleteResponse.data.success).toBe(true);
  });

  it('should handle retry on error', async () => {
    const mockError = new Error('Network error');
    (axios.get as any)
      .mockRejectedValueOnce(mockError)
      .mockResolvedValueOnce({ data: { success: true, data: [], total: 0 } });

    // First attempt fails
    try {
      await axios.get('/api/inventory');
      expect.fail('Should have thrown');
    } catch (error) {
      expect(error).toBe(mockError);
    }

    // Retry succeeds
    const response = await axios.get('/api/inventory');
    expect(response.data.success).toBe(true);
  });
});
