# Backend Tests

This directory contains comprehensive test suites for the Lemi backend API.

## Test Files

- **`test_event_features.py`** - Comprehensive event features testing (NEW)
  - CRUD operations, participants, archiving, validation, permissions
  
- **`test_auth.py`** - Authentication system testing (NEW)
  - Registration, login, profiles, invite codes
  
- **`test_event_creation.py`** - Event creation scenarios
  
- **`test_follow_system.py`** - Follow/unfollow functionality

- **`test_api.py`** - Basic API smoke tests

- **`test_cross_midnight.py`** - Cross-midnight event time testing

- **`test_end_time_admin.py`** - End time validation for admin events

- **`test_end_time_http.py`** - End time HTTP endpoint testing

- **`test_mitsu_zine_follow.py`** - Specific follow scenario tests

## Quick Start

```bash
# Run comprehensive event features tests
python3 test_event_features.py --deployed

# Run authentication tests  
python3 test_auth.py --deployed

# Run specific feature tests
python3 test_event_features.py --deployed --feature crud
python3 test_event_features.py --deployed --feature participants

# Test locally (backend must be running on port 8000)
python3 test_event_features.py --local
```

## Test Features

### Event Features Test (`test_event_features.py`)
✅ 30+ test cases covering:
- Create, read, update, delete events
- Join/leave events
- Archive/unarchive events
- Event validation (dates, times, capacity)
- User permissions (host vs admin)
- Public vs private events
- Featured events

### Authentication Test (`test_auth.py`)
✅ 13+ test cases covering:
- User registration
- Login authentication
- Profile management
- Invite code system

## GitHub Actions

All tests run automatically on:
- Push to `main` branch
- Pull requests to `main` branch

See `.github/workflows/test.yml` for configuration.

## Requirements

```bash
pip install requests
```

## Documentation

See `TESTING_DOCUMENTATION.md` in the root directory for complete documentation.

## Test Output

Tests use colored output:
- 🧪 Blue - Test description
- ✅ Green - Test passed
- ❌ Red - Test failed
- ⚠️ Yellow - Warning
- ℹ️ Blue - Information

## Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed

## Adding New Tests

1. Create test file or add to existing suite
2. Follow the test pattern (setup, test, assert, cleanup)
3. Make file executable: `chmod +x test_your_feature.py`
4. Add to GitHub Actions workflow if needed
5. Update documentation
