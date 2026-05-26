# Test Suite Documentation

This document describes the comprehensive test suite for the Inventory Management Dashboard.

## Overview

The test suite consists of:
- **Backend API Tests** (`test_api.py`) - FastAPI endpoints and business logic
- **Frontend Component Tests** (`frontend/src/tests/components.test.ts`) - React components and UI logic
- **Test Fixtures** (`test_fixtures.py`) - Shared test utilities and sample data

## Running Tests

### Backend Tests

#### Prerequisites
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx
```

#### Run All Backend Tests
```bash
pytest test_api.py -v
```

#### Run Specific Test Class
```bash
pytest test_api.py::TestInventoryEndpoints -v
```

#### Run Specific Test
```bash
pytest test_api.py::TestInventoryEndpoints::test_get_inventory_empty -v
```

#### Run with Coverage Report
```bash
pip install pytest-cov
pytest test_api.py --cov=main --cov-report=html
```

#### Run Tests in Watch Mode (re-run on file changes)
```bash
pip install pytest-watch
ptw test_api.py
```

### Frontend Tests

#### Prerequisites
```bash
cd frontend
npm install --save-dev vitest @vitest/ui @testing-library/react @testing-library/jest-dom
```

#### Run All Frontend Tests
```bash
cd frontend
npm test
```

#### Run Specific Test File
```bash
npm test components.test.ts
```

#### Run Tests in Watch Mode
```bash
npm test -- --watch
```

#### Generate Coverage Report
```bash
npm test -- --coverage
```

#### Run UI Test Dashboard
```bash
npm test -- --ui
```

## Test Structure

### Backend Tests (`test_api.py`)

#### 1. **TestHealthCheck**
- Verifies API is running and accessible
- Checks API configuration

#### 2. **TestInventoryEndpoints**
- **test_get_inventory_empty** - GET /api/inventory with no data
- **test_get_inventory_summary_empty** - GET /api/inventory/summary with no data
- **test_insert_and_retrieve_inventory** - Create and retrieve inventory records
- **test_inventory_summary_with_data** - Summary calculations with multiple records

#### 3. **TestProductSettingsEndpoints**
- **test_get_product_settings_empty** - GET /api/product-settings with no data
- **test_create_product_setting** - POST /api/product-settings
- **test_create_product_setting_missing_item** - Validation test (missing required field)
- **test_get_product_settings_after_create** - Retrieve after creation
- **test_get_single_product_setting** - GET /api/product-settings/{id}
- **test_get_nonexistent_product_setting** - 404 error handling
- **test_update_product_setting** - PUT /api/product-settings/{id}
- **test_delete_product_setting** - DELETE /api/product-settings/{id} (soft delete)

#### 4. **TestFileOperations**
- **test_list_files_empty** - GET /api/files with no uploads

#### 5. **TestIntegration**
- **test_full_workflow** - End-to-end: Create settings → Add inventory → Verify summary
- **test_multiple_products_and_settings** - Handling multiple products and status tracking

### Frontend Tests (`frontend/src/tests/components.test.ts`)

#### 1. **Utility Functions**
- Number formatting (commas, decimals)
- Date formatting (locale-specific)
- Status to color mapping

#### 2. **API Response Handling**
- Successful inventory fetch
- Summary calculations
- Error handling
- CRUD operations for product settings
- Intelligence API responses

#### 3. **Component Logic**
- Tab management (active tab tracking)
- Error state management
- Data transformation and filtering
- Pagination
- Sorting

#### 4. **Form Operations**
- Field validation
- Form reset after submission

#### 5. **User Workflows**
- Complete inventory view workflow
- Product settings management workflow
- Retry on error

## Test Data

### Sample Inventory Records
Located in `test_fixtures.py::SAMPLE_INVENTORY_DATA`:
- Product A: 1000 units (OK status)
- Product B: 50 units (CRITICAL status)
- Product C: 500 units (WARNING status)
- Product D: 2000 units (OK status)

### Sample Product Settings
Located in `test_fixtures.py::SAMPLE_PRODUCT_SETTINGS`:
- Product A: safety_stock=100, reorder_point=50
- Product B: safety_stock=200, reorder_point=100
- Product C: safety_stock=150, reorder_point=75

## Using Fixtures

### Test Database Fixture
```python
def test_something(test_db):
    # test_db is a SQLAlchemy Engine with in-memory SQLite
    with test_db.begin() as conn:
        conn.execute(...)
```

### Cleanup Fixture
```python
# Automatically runs before each test
@pytest.fixture(autouse=True)
def cleanup_db(test_db):
    # Clears all tables before each test
```

### Sample Data Generators
```python
from test_fixtures import generate_inventory_record, insert_inventory_record

record = generate_inventory_record(
    item="Product X",
    company="Company Y",
    physical_stock=5000,
    status="CRITICAL"
)

record_id = insert_inventory_record(engine, record)
```

## API Endpoint Coverage

### Inventory Management
- ✅ GET /api/inventory - List all inventory
- ✅ GET /api/inventory/summary - Inventory statistics

### Product Settings
- ✅ GET /api/product-settings - List all settings
- ✅ GET /api/product-settings/{id} - Get single setting
- ✅ POST /api/product-settings - Create setting
- ✅ PUT /api/product-settings/{id} - Update setting
- ✅ DELETE /api/product-settings/{id} - Delete setting

### Intelligence/Analytics
- ✅ GET /api/stock-analytics/dates - Available analytics dates
- ✅ GET /api/stock-analytics/summary - Grouped analytics summary
- ✅ GET /api/stock-analytics/drilldown - Vessel-level drilldown
- ✅ GET /api/intelligence/alerts - Derived alerts from analytics
- ✅ GET /api/intelligence/narrative - Derived executive narrative

### File Operations
- ⏳ POST /api/upload - Upload Excel file (GCS integration needed)
- ⏳ GET /api/files - List uploaded files
- ⏳ POST /api/refresh - Import from GCS files

## Component Coverage

### React Components
- ⏳ App.tsx - Tab navigation (basic structure tested)
- ⏳ InsightsDashboard.tsx - Intelligence visualization (API mocked)
- ⏳ ProductSettings.tsx - Settings CRUD (API mocked)
- ⏳ DataTable.tsx - Inventory table display (logic tested)

## Testing Best Practices

### Backend Tests

1. **Use the test_db fixture for database operations**
   ```python
   def test_inventory(test_db):
       with test_db.begin() as conn:
           conn.execute(...)
   ```

2. **Test both success and error paths**
   ```python
   def test_success(self):
       response = client.get("/api/endpoint")
       assert response.status_code == 200
   
   def test_error(self):
       response = client.get("/api/nonexistent")
       assert response.status_code == 404
   ```

3. **Use meaningful test names that describe what is being tested**
   ```python
   def test_create_product_setting_with_valid_data(self):
       # Good: describes what is being tested
   ```

4. **Arrange-Act-Assert pattern**
   ```python
   def test_example(self):
       # Arrange
       test_data = {...}
       
       # Act
       response = client.post("/api/endpoint", json=test_data)
       
       # Assert
       assert response.status_code == 201
   ```

### Frontend Tests

1. **Mock external dependencies (axios)**
   ```typescript
   vi.mock('axios');
   (axios.get as any).mockResolvedValue({...});
   ```

2. **Test both happy path and error cases**
   ```typescript
   it('should handle success', async () => {...});
   it('should handle error', async () => {...});
   ```

3. **Use descriptive test names**
   ```typescript
   it('should format numbers with Indian locale commas', () => {...});
   ```

## Continuous Integration

### GitHub Actions Example

Add to `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt pytest
      - run: pytest test_api.py -v

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
        with:
          node-version: '18'
      - run: cd frontend && npm install
      - run: cd frontend && npm test
```

## Debugging Tests

### View detailed test output
```bash
pytest test_api.py -vv
```

### Stop on first failure
```bash
pytest test_api.py -x
```

### Show print statements
```bash
pytest test_api.py -s
```

### Run tests matching pattern
```bash
pytest test_api.py -k "inventory" -v
```

### Start Python debugger on failure
```bash
pytest test_api.py --pdb
```

## Adding New Tests

### Backend Test Template
```python
class TestNewFeature:
    """Test description."""
    
    def test_scenario_1(self):
        """Test specific scenario."""
        # Arrange
        
        # Act
        response = client.get("/api/endpoint")
        
        # Assert
        assert response.status_code == 200
```

### Frontend Test Template
```typescript
describe('New Feature', () => {
  it('should do something', () => {
    // Arrange
    
    // Act
    const result = someFunction();
    
    // Assert
    expect(result).toBe(expectedValue);
  });
});
```

## Performance Benchmarks

Expected test execution times:
- Backend: ~2-5 seconds (all tests)
- Frontend: ~1-3 seconds (all tests)
- Total: ~5-8 seconds

If tests take significantly longer, consider:
- Using in-memory database (already configured)
- Mocking external services (already done)
- Parallel test execution: `pytest test_api.py -n auto`

## Troubleshooting

### Backend Tests

**Issue**: Tests fail with "port already in use"
```bash
# Kill any existing Python processes
pkill -f "python main.py"
# Then retry tests
```

**Issue**: Database connection errors
```bash
# Ensure SQLite is configured for testing
export DB_TYPE=sqlite
export DB_PATH=":memory:"
```

### Frontend Tests

**Issue**: Vitest not found
```bash
cd frontend
npm install --save-dev vitest
```

**Issue**: Axios mock not working
```typescript
// Ensure mock is before import
vi.mock('axios');
import axios from 'axios';
```

## Next Steps

1. Add more component unit tests (currently mostly testing logic)
2. Add E2E tests with Playwright or Cypress
3. Set up CI/CD pipeline with GitHub Actions
4. Add performance tests for database queries
5. Add stress tests for bulk operations
6. Implement test reporting dashboard

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [HTTP Assertions](https://docs.httpbin.org/)
