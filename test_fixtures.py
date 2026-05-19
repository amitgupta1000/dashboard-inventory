"""
Test Configuration and Fixtures for Backend Tests

This module provides shared test utilities and fixtures for the inventory API tests.
"""

import pytest
import os
import tempfile
from pathlib import Path
import sqlalchemy

# Configure test environment to use in-memory SQLite
os.environ['DB_TYPE'] = 'sqlite'
os.environ['DB_PATH'] = ':memory:'


# ============================================================================
# Sample Data Generators
# ============================================================================

def generate_inventory_record(
    item: str = "Test Product",
    company: str = "Test Company",
    port: str = "Test Port",
    physical_stock: float = 1000,
    ready_unsold: float = 500,
    status: str = "OK",
    record_date: str = "2026-05-19"
) -> dict:
    """Generate a test inventory record."""
    return {
        'record_date': record_date,
        'item': item,
        'port': port,
        'company': company,
        'unit': 'kg',
        'physical_stock': physical_stock,
        'ready_unsold': ready_unsold,
        'safety_stock': 100,
        'reorder_point': 50,
        'storage_cap_days': 30,
        'cycle_days': 10,
        'monthly_volume': 500,
        'market_price': 100,
        'selling_price': 120,
        'cif_duty': 5,
        'purchase_price': 80,
        'pending_lifting': 100,
        'port_stock': physical_stock - 100,
        'incoming_qty': 200,
        'arrival_date': '2026-05-25',
        'status': status,
    }


def generate_product_setting(
    item: str = "Test Product",
    safety_stock: float = 100,
    reorder_point: float = 50
) -> dict:
    """Generate a test product setting."""
    return {
        'item': item,
        'safety_stock': safety_stock,
        'reorder_point': reorder_point,
        'max_storage_days': 30,
        'max_inventory_days': 60,
        'monthly_target_volume': 500,
        'notes': f'Test setting for {item}'
    }


# ============================================================================
# Database Helpers
# ============================================================================

def insert_inventory_record(engine: sqlalchemy.Engine, record: dict) -> int:
    """Insert a test inventory record and return its ID."""
    with engine.begin() as conn:
        result = conn.execute(
            sqlalchemy.text("""
                INSERT INTO inventory (
                    record_date, item, port, company, unit,
                    physical_stock, ready_unsold, safety_stock, reorder_point,
                    storage_cap_days, cycle_days, monthly_volume,
                    market_price, selling_price, cif_duty, purchase_price,
                    pending_lifting, port_stock, incoming_qty, arrival_date, status
                ) VALUES (
                    :record_date, :item, :port, :company, :unit,
                    :physical_stock, :ready_unsold, :safety_stock, :reorder_point,
                    :storage_cap_days, :cycle_days, :monthly_volume,
                    :market_price, :selling_price, :cif_duty, :purchase_price,
                    :pending_lifting, :port_stock, :incoming_qty, :arrival_date, :status
                )
            """),
            record
        )
    return result.lastrowid or 0


def insert_product_setting(engine: sqlalchemy.Engine, setting: dict) -> int:
    """Insert a test product setting and return its ID."""
    with engine.begin() as conn:
        result = conn.execute(
            sqlalchemy.text("""
                INSERT INTO product_settings (
                    item, safety_stock, reorder_point,
                    max_storage_days, max_inventory_days, monthly_target_volume, notes
                ) VALUES (
                    :item, :safety_stock, :reorder_point,
                    :max_storage_days, :max_inventory_days, :monthly_target_volume, :notes
                )
            """),
            setting
        )
    return result.lastrowid or 0


def get_inventory_count(engine: sqlalchemy.Engine) -> int:
    """Get total inventory record count."""
    with engine.connect() as conn:
        result = conn.execute(sqlalchemy.text("SELECT COUNT(*) as count FROM inventory"))
        return result.fetchone()[0]


def get_product_settings_count(engine: sqlalchemy.Engine) -> int:
    """Get total active product settings count."""
    with engine.connect() as conn:
        result = conn.execute(
            sqlalchemy.text("SELECT COUNT(*) as count FROM product_settings WHERE is_active = TRUE")
        )
        return result.fetchone()[0]


# ============================================================================
# Assertion Helpers
# ============================================================================

def assert_api_success(response_data: dict, message: str = "") -> None:
    """Assert that API response indicates success."""
    assert response_data.get('success') is True, f"API response not successful. {message}"


def assert_api_error(response_data: dict, message: str = "") -> None:
    """Assert that API response indicates error."""
    assert response_data.get('success') is False or 'detail' in response_data, \
        f"Expected error response. {message}"


def assert_response_has_field(response_data: dict, field: str) -> None:
    """Assert that response contains a specific field."""
    assert field in response_data, f"Response missing field: {field}"


# ============================================================================
# Test Data Sets
# ============================================================================

SAMPLE_INVENTORY_DATA = [
    generate_inventory_record("Product A", "Company 1", "Port A", 1000, 500, "OK"),
    generate_inventory_record("Product B", "Company 1", "Port B", 50, 10, "CRITICAL"),
    generate_inventory_record("Product C", "Company 2", "Port A", 500, 250, "WARNING"),
    generate_inventory_record("Product D", "Company 2", "Port C", 2000, 1000, "OK"),
]

SAMPLE_PRODUCT_SETTINGS = [
    generate_product_setting("Product A", 100, 50),
    generate_product_setting("Product B", 200, 100),
    generate_product_setting("Product C", 150, 75),
]
