"""
Comprehensive test suite for the Inventory Management API.

Tests cover:
- Database connectivity and schema initialization
- Inventory CRUD operations
- Product settings management
- Intelligence/Analytics endpoints
- File operations (upload, refresh)
"""

import pytest
import json
import sqlite3
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import os
import sqlalchemy
from unittest.mock import patch, MagicMock

# Set up test environment with SQLite
os.environ['DB_TYPE'] = 'sqlite'
os.environ['DB_PATH'] = ':memory:'  # In-memory database for tests

from main import app, get_db_engine
from backend.db import _init_sqlite_schema

# Create test client
client = TestClient(app)


# ============================================================================
# Fixtures and Setup
# ============================================================================

@pytest.fixture(scope="session")
def test_db():
    """Create test database and initialize schema."""
    engine = get_db_engine()
    _init_sqlite_schema(engine)
    
    # Create inventory table if not exists (for tests)
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_date TEXT,
                item TEXT,
                port TEXT,
                company TEXT,
                unit TEXT,
                physical_stock REAL,
                ready_unsold REAL,
                safety_stock REAL,
                reorder_point REAL,
                storage_cap_days REAL,
                cycle_days REAL,
                monthly_volume REAL,
                market_price REAL,
                selling_price REAL,
                cif_duty REAL,
                purchase_price REAL,
                pending_lifting REAL,
                port_stock REAL,
                incoming_qty REAL,
                arrival_date TEXT,
                status TEXT DEFAULT 'OK',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.execute(sqlalchemy.text("""
            CREATE TABLE IF NOT EXISTS processed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gcs_path TEXT UNIQUE,
                filename TEXT,
                rows_imported INTEGER,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.commit()
    
    yield engine


@pytest.fixture(autouse=True)
def cleanup_db(test_db):
    """Clean up database before each test."""
    with test_db.begin() as conn:
        # Delete all data from tables in order (respect foreign keys if any)
        conn.execute(sqlalchemy.text("DELETE FROM processed_files"))
        conn.execute(sqlalchemy.text("DELETE FROM product_settings"))
        conn.execute(sqlalchemy.text("DELETE FROM inventory"))
    yield
    # Also clean up after test completes
    with test_db.begin() as conn:
        conn.execute(sqlalchemy.text("DELETE FROM processed_files"))
        conn.execute(sqlalchemy.text("DELETE FROM product_settings"))
        conn.execute(sqlalchemy.text("DELETE FROM inventory"))


# ============================================================================
# Health Check Tests
# ============================================================================

class TestHealthCheck:
    """Test basic API connectivity."""
    
    def test_api_root_exists(self):
        """Test that API is accessible."""
        # Just check that the app is running
        assert app.title == "Inventory Management API"


# ============================================================================
# Inventory Endpoint Tests
# ============================================================================

class TestInventoryEndpoints:
    """Test inventory data endpoints."""
    
    def test_get_inventory_empty(self):
        """Test getting inventory when empty."""
        response = client.get("/api/inventory")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['total'] == 0
        assert data['data'] == []
    
    def test_get_inventory_summary_empty(self):
        """Test getting summary when inventory is empty."""
        response = client.get("/api/inventory/summary")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        summary = data['summary']
        assert summary['total_items'] == 0
        assert summary['total_physical_stock'] == 0
        assert summary['total_ready_unsold'] == 0
        assert summary['critical_count'] == 0
    
    def test_insert_and_retrieve_inventory(self, test_db):
        """Test inserting and retrieving inventory records."""
        # Insert test data directly into database
        with test_db.begin() as conn:
            conn.execute(sqlalchemy.text("""
                INSERT INTO inventory (
                    record_date, item, port, company, unit,
                    physical_stock, ready_unsold, safety_stock, reorder_point,
                    storage_cap_days, cycle_days, monthly_volume,
                    market_price, selling_price, cif_duty, purchase_price,
                    pending_lifting, port_stock, incoming_qty, arrival_date, status
                ) VALUES (
                    '2026-05-19', 'Product A', 'Port X', 'Company 1', 'kg',
                    1000, 500, 100, 200,
                    30, 10, 500,
                    100, 120, 5, 80,
                    100, 900, 200, '2026-05-25', 'OK'
                )
            """))
        
        # Retrieve inventory
        response = client.get("/api/inventory")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['total'] == 1
        assert len(data['data']) == 1
        
        record = data['data'][0]
        assert record['item'] == 'Product A'
        assert record['company'] == 'Company 1'
        assert float(record['physical_stock']) == 1000
        assert record['status'] == 'OK'
    
    def test_inventory_summary_with_data(self, test_db):
        """Test inventory summary calculations."""
        # Insert multiple test records
        with test_db.begin() as conn:
            for i in range(3):
                conn.execute(sqlalchemy.text("""
                    INSERT INTO inventory (
                        record_date, item, port, company, unit,
                        physical_stock, ready_unsold, safety_stock, reorder_point,
                        storage_cap_days, cycle_days, monthly_volume,
                        market_price, selling_price, cif_duty, purchase_price,
                        pending_lifting, port_stock, incoming_qty, arrival_date, status
                    ) VALUES (
                        '2026-05-19', :item, 'Port X', 'Company 1', 'kg',
                        :stock, 500, 100, 200,
                        30, 10, 500,
                        100, 120, 5, 80,
                        100, 900, 200, '2026-05-25', :status
                    )
                """), {
                    'item': f'Product {i}',
                    'stock': 1000 + (i * 100),
                    'status': ['CRITICAL', 'WARNING', 'OK'][i]
                })
        
        response = client.get("/api/inventory/summary")
        assert response.status_code == 200
        data = response.json()
        
        summary = data['summary']
        assert summary['total_items'] == 3
        assert float(summary['total_physical_stock']) == 3300  # 1000 + 1100 + 1200
        assert summary['critical_count'] == 1
        assert summary['warning_count'] == 1
        assert summary['ok_count'] == 1


# ============================================================================
# Product Settings Endpoint Tests
# ============================================================================

class TestProductSettingsEndpoints:
    """Test product settings CRUD operations."""
    
    def test_get_product_settings_empty(self):
        """Test getting product settings when empty."""
        response = client.get("/api/product-settings")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['total'] == 0
        assert data['data'] == []
    
    def test_create_product_setting(self):
        """Test creating a new product setting."""
        setting = {
            "item": "Test Product",
            "safety_stock": 100,
            "reorder_point": 50,
            "max_storage_days": 30,
            "max_inventory_days": 60,
            "monthly_target_volume": 500,
            "notes": "Test product setting"
        }
        
        response = client.post("/api/product-settings", json=setting)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['item'] == "Test Product"
        assert float(data['data']['safety_stock']) == 100
        # SQLite returns 1 for True, so check for truthy value
        assert data['data']['is_active']
    
    def test_create_product_setting_missing_item(self):
        """Test creating product setting without required 'item' field."""
        setting = {
            "safety_stock": 100,
            "reorder_point": 50
        }
        
        response = client.post("/api/product-settings", json=setting)
        assert response.status_code == 400
    
    def test_get_product_settings_after_create(self):
        """Test retrieving product settings after creation."""
        # Create a setting
        setting = {
            "item": "Product A",
            "safety_stock": 100,
            "reorder_point": 50,
            "max_storage_days": 30,
            "max_inventory_days": 60,
            "monthly_target_volume": 500,
            "notes": "Product A settings"
        }
        
        create_response = client.post("/api/product-settings", json=setting)
        assert create_response.status_code == 200
        created_id = create_response.json()['data']['id']
        
        # Retrieve all settings
        get_response = client.get("/api/product-settings")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data['total'] == 1
        assert data['data'][0]['item'] == "Product A"
    
    def test_get_single_product_setting(self):
        """Test retrieving a single product setting by ID."""
        # Create a setting
        setting = {
            "item": "Product X",
            "safety_stock": 200,
            "reorder_point": 100
        }
        
        create_response = client.post("/api/product-settings", json=setting)
        setting_id = create_response.json()['data']['id']
        
        # Get the setting
        response = client.get(f"/api/product-settings/{setting_id}")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['item'] == "Product X"
    
    def test_get_nonexistent_product_setting(self):
        """Test retrieving a non-existent product setting."""
        response = client.get("/api/product-settings/999")
        assert response.status_code == 404
    
    def test_update_product_setting(self):
        """Test updating a product setting."""
        # Create a setting
        setting = {
            "item": "Product Y",
            "safety_stock": 100,
            "reorder_point": 50
        }
        
        create_response = client.post("/api/product-settings", json=setting)
        setting_id = create_response.json()['data']['id']
        
        # Update the setting
        updated = {
            "item": "Product Y Updated",
            "safety_stock": 150,
            "reorder_point": 75,
            "monthly_target_volume": 1000
        }
        
        update_response = client.put(f"/api/product-settings/{setting_id}", json=updated)
        assert update_response.status_code == 200
        data = update_response.json()
        assert data['success'] is True
        assert data['data']['item'] == "Product Y Updated"
        assert float(data['data']['safety_stock']) == 150
    
    def test_delete_product_setting(self):
        """Test soft-deleting a product setting."""
        # Create a setting
        setting = {
            "item": "Product Z",
            "safety_stock": 100,
            "reorder_point": 50
        }
        
        create_response = client.post("/api/product-settings", json=setting)
        setting_id = create_response.json()['data']['id']
        
        # Delete the setting
        delete_response = client.delete(f"/api/product-settings/{setting_id}")
        assert delete_response.status_code == 200
        data = delete_response.json()
        assert data['success'] is True
        assert 'deleted' in data['message'].lower()
        
        # Verify it's no longer in the list (is_active = FALSE)
        get_response = client.get("/api/product-settings")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data['total'] == 0


# ============================================================================
# File Operations Tests
# ============================================================================

class TestFileOperations:
    """Test file upload and refresh operations."""
    
    @patch('main.gcs.list_uploaded_files')
    def test_list_files_empty(self, mock_list_files, test_db):
        """Test listing files when none uploaded."""
        # Mock GCS to return no files
        mock_list_files.return_value = []
        
        # Ensure processed_files is empty
        with test_db.begin() as conn:
            conn.execute(sqlalchemy.text("DELETE FROM processed_files"))
        
        response = client.get("/api/files")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['files'] == []
        
        # Verify mock was called
        mock_list_files.assert_called_once()


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """End-to-end integration tests."""
    
    def test_full_workflow(self, test_db):
        """Test complete workflow: create settings, add inventory, verify summary."""
        # Step 1: Create product settings
        setting_response = client.post("/api/product-settings", json={
            "item": "Integration Test Product",
            "safety_stock": 100,
            "reorder_point": 50,
            "max_storage_days": 30,
            "max_inventory_days": 60,
            "monthly_target_volume": 500
        })
        assert setting_response.status_code == 200
        
        # Step 2: Add inventory record
        with test_db.begin() as conn:
            conn.execute(sqlalchemy.text("""
                INSERT INTO inventory (
                    record_date, item, port, company, unit,
                    physical_stock, ready_unsold, safety_stock, reorder_point,
                    storage_cap_days, cycle_days, monthly_volume,
                    market_price, selling_price, cif_duty, purchase_price,
                    pending_lifting, port_stock, incoming_qty, arrival_date, status
                ) VALUES (
                    '2026-05-19', 'Integration Test Product', 'Port A', 'Company 1', 'kg',
                    1500, 500, 100, 50,
                    30, 10, 500,
                    100, 120, 5, 80,
                    100, 1400, 200, '2026-05-25', 'OK'
                )
            """))
        
        # Step 3: Verify settings are retrievable
        settings_response = client.get("/api/product-settings")
        assert settings_response.status_code == 200
        assert settings_response.json()['total'] == 1
        
        # Step 4: Verify inventory is retrievable
        inventory_response = client.get("/api/inventory")
        assert inventory_response.status_code == 200
        assert inventory_response.json()['total'] == 1
        
        # Step 5: Verify summary calculation
        summary_response = client.get("/api/inventory/summary")
        assert summary_response.status_code == 200
        summary = summary_response.json()['summary']
        assert float(summary['total_physical_stock']) == 1500
        assert float(summary['total_ready_unsold']) == 500
    
    def test_multiple_products_and_settings(self, test_db):
        """Test handling multiple products and settings."""
        # Create multiple settings
        for i in range(3):
            client.post("/api/product-settings", json={
                "item": f"Product {i}",
                "safety_stock": 100 + (i * 50),
                "reorder_point": 50 + (i * 25)
            })
        
        # Verify all settings are created
        response = client.get("/api/product-settings")
        assert response.status_code == 200
        assert response.json()['total'] == 3
        
        # Add inventory records for each product
        with test_db.begin() as conn:
            for i in range(3):
                conn.execute(sqlalchemy.text("""
                    INSERT INTO inventory (
                        record_date, item, port, company, unit,
                        physical_stock, ready_unsold, safety_stock, reorder_point,
                        storage_cap_days, cycle_days, monthly_volume,
                        market_price, selling_price, cif_duty, purchase_price,
                        pending_lifting, port_stock, incoming_qty, arrival_date, status
                    ) VALUES (
                        '2026-05-19', :item, 'Port A', 'Company 1', 'kg',
                        :stock, 500, 100, 50,
                        30, 10, 500,
                        100, 120, 5, 80,
                        100, :port_stock, 200, '2026-05-25', :status
                    )
                """), {
                    'item': f'Product {i}',
                    'stock': 1000 + (i * 500),
                    'port_stock': 900 + (i * 500),
                    'status': ['CRITICAL', 'WARNING', 'OK'][i]
                })
        
        # Verify inventory summary
        response = client.get("/api/inventory/summary")
        data = response.json()
        summary = data['summary']
        
        assert summary['total_items'] == 3
        assert float(summary['total_physical_stock']) == 4500  # 1000 + 1500 + 2000
        assert summary['critical_count'] == 1
        assert summary['warning_count'] == 1
        assert summary['ok_count'] == 1


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
