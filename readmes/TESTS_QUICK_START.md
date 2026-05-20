# Tests Quick Reference Guide

## Installation

### Backend (one-time setup)
```bash
pip install pytest httpx
```

### Frontend (one-time setup)
```bash
cd frontend
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom
```

## Running Tests

### ⚡ Quick Commands

**Run all tests:**
```bash
python run_tests.py
```

**Run backend only:**
```bash
pytest test_api.py -v
```

**Run frontend only:**
```bash
cd frontend && npm test
```

### 📊 With Reports

**Backend with coverage:**
```bash
pytest test_api.py --cov=main --cov-report=html
# Opens: htmlcov/index.html
```

**Frontend with coverage:**
```bash
cd frontend && npm test -- --coverage
```

**Run with detailed output:**
```bash
pytest test_api.py -vv
```

### 🔄 Watch Mode (auto-rerun on changes)

**Backend:**
```bash
pip install pytest-watch
ptw test_api.py
```

**Frontend:**
```bash
cd frontend && npm test -- --watch
```

### 🎯 Run Specific Tests

**Single test:**
```bash
pytest test_api.py::TestProductSettingsEndpoints::test_create_product_setting -v
```

**Test class:**
```bash
pytest test_api.py::TestProductSettingsEndpoints -v
```

**By keyword:**
```bash
pytest test_api.py -k "product" -v
```

## Test Files Overview

| File | Tests | Run With |
|------|-------|----------|
| `test_api.py` | 16 backend | `pytest test_api.py -v` |
| `frontend/src/tests/components.test.ts` | 20+ frontend | `cd frontend && npm test` |

## Test Categories

### Backend (`test_api.py`)
- ✅ **Health Check** (1) - API connectivity
- ✅ **Inventory** (4) - GET endpoints, data retrieval
- ✅ **Product Settings** (8) - CRUD operations
- ✅ **File Operations** (1) - File listing
- ✅ **Integration** (2) - End-to-end workflows

### Frontend (`components.test.ts`)
- ✅ **Utilities** (3) - Formatting, mapping
- ✅ **API Responses** (9) - Mocked axios calls
- ✅ **Component Logic** (5) - Tabs, errors, data transforms
- ✅ **Forms** (2) - Validation, reset
- ✅ **Workflows** (3+) - User interactions

## Debugging

**Show print statements:**
```bash
pytest test_api.py -s
```

**Stop on first failure:**
```bash
pytest test_api.py -x
```

**Show locals on failure:**
```bash
pytest test_api.py -l
```

**Open debugger on failure:**
```bash
pytest test_api.py --pdb
```

**Show 10 lines of context:**
```bash
pytest test_api.py --tb=long
```

## Common Issues & Fixes

**Tests fail with "port already in use"**
```bash
# Kill Python processes
pkill -f "python main.py"
# Retry tests
pytest test_api.py -v
```

**Pytest not found**
```bash
pip install pytest
```

**Vitest not found**
```bash
cd frontend
npm install --save-dev vitest
```

**Old test results cached**
```bash
pytest test_api.py --cache-clear
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install pytest httpx
      - run: pytest test_api.py -v
```

## Environment Variables

**Force test database:**
```bash
export DB_TYPE=sqlite
export DB_PATH=:memory:
pytest test_api.py -v
```

**Skip slow tests:**
```bash
pytest test_api.py -m "not slow"
```

## Performance

**Run tests in parallel:**
```bash
pip install pytest-xdist
pytest test_api.py -n auto
```

**Show slowest tests:**
```bash
pytest test_api.py --durations=10
```

## Test Configuration

- Backend: `pytest.ini`
- Frontend: `frontend/vitest.config.ts`
- Setup: `frontend/src/tests/setup.ts`

## Documentation

- **Full Guide:** [TEST_README.md](TEST_README.md)
- **Summary:** [TESTS_SUMMARY.md](TESTS_SUMMARY.md)
- **Fixtures:** [test_fixtures.py](test_fixtures.py)

## API Endpoints Tested

| Endpoint | Method | Test |
|----------|--------|------|
| /api/inventory | GET | ✅ `test_get_inventory_*` |
| /api/inventory/summary | GET | ✅ `test_get_inventory_summary_*` |
| /api/product-settings | GET | ✅ `test_get_product_settings_empty` |
| /api/product-settings | POST | ✅ `test_create_product_setting` |
| /api/product-settings/{id} | GET | ✅ `test_get_single_product_setting` |
| /api/product-settings/{id} | PUT | ✅ `test_update_product_setting` |
| /api/product-settings/{id} | DELETE | ✅ `test_delete_product_setting` |
| /api/files | GET | ✅ `test_list_files_empty` |

## Quick Stats

- **Total Tests:** 36+
- **Backend Tests:** 16 ✅ All Passing
- **Frontend Tests:** 20+ Ready to Run
- **Execution Time:** ~8-10 seconds
- **Database:** In-memory SQLite (fast, no cleanup needed)
- **Mocks:** GCS, axios (no external dependencies)

## Next Steps

1. **Run tests:** `python run_tests.py`
2. **Check coverage:** `pytest test_api.py --cov=main`
3. **Add more tests:** See [TEST_README.md](TEST_README.md) for examples
4. **CI/CD:** Set up GitHub Actions following the example above

---

For detailed information, see [TEST_README.md](TEST_README.md)
