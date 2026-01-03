# Testing Guide

## Overview
This directory contains comprehensive test suites for the backend API. Each feature has its own test file that can test both local and deployed environments.

## Test Files

### 1. `test_event_creation.py` - Event Creation Testing
Tests all aspects of event creation including:
- Basic event creation with minimal fields
- Complete event creation with all fields
- Cross-midnight events (e.g., 23:00 - 02:00)
- Invalid time ranges (should fail)
- Events with special characters and emojis
- Private events
- Events with capacity limits
- Events with targeting parameters
- Long descriptions
- Edge cases

**Usage:**
```bash
# Test local environment only
python3 test_event_creation.py --local

# Test deployed environment only
python3 test_event_creation.py --deployed

# Test both environments
python3 test_event_creation.py --all

# Test without cleanup (leave test events in database)
python3 test_event_creation.py --all --no-cleanup
```

### 2. `test_follow_system.py` - Follow System Testing
Tests the follow/unfollow functionality:
- Follow requests
- Accept/decline follow requests
- Unfollow (unidirectional)
- Follow counts
- Edge cases

**Usage:**
```bash
python3 test_follow_system.py
```

### 3. `test_mitsu_zine_follow.py` - Specific User Scenario
Tests a specific follow scenario between two users.

**Usage:**
```bash
python3 test_mitsu_zine_follow.py
```

## Test Structure

Each test file follows this pattern:

1. **Test Case Definition**: Define test cases with expected inputs and outcomes
2. **API Calls**: Make HTTP requests to the backend
3. **Validation**: Verify responses match expectations
4. **Cleanup**: Remove test data (optional)
5. **Reporting**: Generate colored terminal output with pass/fail results

## Environment Configuration

### Local Testing
- Backend: `http://localhost:8000`
- Requires local backend to be running:
  ```bash
  cd backend
  python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
  ```

### Deployed Testing
- Backend: `https://fast-api-backend-qlyb.onrender.com`
- Tests against production environment
- **⚠️ Use with caution** - creates real data

## Creating New Tests

To create a new test file:

1. **Copy the structure** from `test_event_creation.py`
2. **Define test cases** for your feature
3. **Create a tester class** with methods:
   - API call methods
   - Verification methods
   - Cleanup methods
4. **Add test cases** covering:
   - Happy path (normal usage)
   - Edge cases
   - Invalid inputs (should fail)
   - Boundary conditions
5. **Make it executable**: `chmod +x test_your_feature.py`

### Example Test Case Structure

```python
class YourFeatureTestCase:
    def __init__(self, name: str, input_data: Dict, 
                 should_succeed: bool = True, 
                 expected_error: Optional[str] = None):
        self.name = name
        self.input_data = input_data
        self.should_succeed = should_succeed
        self.expected_error = expected_error

class YourFeatureTester:
    def __init__(self, api_url: str, env_name: str):
        self.api_url = api_url
        self.env_name = env_name
        self.test_cases = []
        self.passed = 0
        self.failed = 0
    
    def test_feature(self, data: Dict) -> Dict:
        # Make API call
        response = requests.post(f"{self.api_url}/api/endpoint", json=data)
        return response.json()
    
    def run_test_case(self, test_case):
        # Run individual test
        # Validate results
        # Return success/failure
        pass
    
    def run_all_tests(self):
        # Run all test cases
        # Print summary
        pass
```

## Best Practices

1. **Always clean up test data** unless debugging
2. **Use descriptive test names** that explain what's being tested
3. **Test both success and failure cases**
4. **Verify side effects** (e.g., database state, counts)
5. **Use realistic test data** that mimics production usage
6. **Test edge cases** (empty strings, nulls, max lengths, etc.)
7. **Make tests idempotent** - they should work regardless of database state
8. **Add color coding** for easy visual scanning of results

## Continuous Integration

For automated testing, you can run all tests with:

```bash
# Run all test suites
for test_file in test_*.py; do
    echo "Running $test_file..."
    python3 "$test_file" --all
done
```

## Test Output

Tests produce colored terminal output:
- 🟢 **Green** - Passed tests
- 🔴 **Red** - Failed tests
- 🟡 **Yellow** - Warnings
- 🔵 **Blue** - Info messages

Example output:
```
======================================================================
Testing Event Creation: LOCAL (localhost:8000)
API: http://localhost:8000
======================================================================

  📋 Test: Basic Event Creation
     Event: Test Event - Basic
     ✅ Event created successfully (ID: 123)

  📋 Test: Same Start/End Time (Should Fail)
     Event: Test Event - Invalid Times
     ✅ Failed as expected: cannot be the same

======================================================================
Test Summary - LOCAL (localhost:8000)
======================================================================
Total Tests:  10
Passed:       10
Failed:       0
Success Rate: 100.0%
======================================================================
```

## Troubleshooting

### "Connection refused" error
- Make sure the backend is running
- Check the port number (8000 for local, 443 for deployed)

### Tests fail on deployed but pass locally
- Check for database differences (SQLite vs PostgreSQL)
- Verify environment variables
- Check CORS settings

### Cleanup fails
- Manually delete test events from database
- Or use `--no-cleanup` flag and clean up manually later

## Future Enhancements

Potential additions to the test suite:
- [ ] User profile testing
- [ ] Event joining/leaving testing
- [ ] Chat/messaging testing
- [ ] Notification testing
- [ ] Points system testing
- [ ] Admin functionality testing
- [ ] Image upload testing
- [ ] Search/filter testing
- [ ] Performance testing (load tests)
- [ ] Security testing (authentication, authorization)
