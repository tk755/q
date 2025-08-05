# Q Library Test Suite

Comprehensive test suite for the modularized Q package, ensuring quality, performance, and backward compatibility.

## Test Structure

### Core Test Modules

- **`test_text_generator.py`** - TextGenerator class functionality, conversation management, provider integration
- **`test_image_generator.py`** - ImageGenerator class functionality, file handling, provider integration  
- **`test_openai_provider.py`** - OpenAI provider implementation, authentication, API calls
- **`test_command_registry.py`** - Command registration, discovery, execution
- **`test_processing.py`** - Response processing, markdown handling, formatting
- **`test_cli.py`** - CLI argument parsing, help text, command routing

### Integration Tests

- **`test_integration_comprehensive.py`** - End-to-end workflows, cross-component integration
- **`test_backward_compatibility.py`** - Exact behavioral compatibility with original q.py

### Quality & Performance Tests

- **`test_performance_security.py`** - Performance benchmarks and security validation

### Test Infrastructure

- **`conftest.py`** - Pytest configuration, fixtures, and test utilities
- **`pytest.ini`** - Pytest configuration and test markers
- **`requirements.txt`** - Testing dependencies

## Test Categories

### Unit Tests (`pytest -m unit`)
- Individual component testing
- Mock external dependencies
- Fast execution (< 1s per test)
- High coverage of code paths

### Integration Tests (`pytest -m integration`)
- Cross-component workflows
- End-to-end scenarios
- Provider-generator-CLI integration
- Real-world usage patterns

### Backward Compatibility Tests (`pytest -m backward_compatibility`)
- CLI interface compatibility
- Configuration format preservation
- Output format matching
- Error message consistency

### Performance Tests (`pytest -m performance`)
- Response time benchmarks
- Memory usage monitoring  
- Throughput testing
- Concurrent access safety

### Security Tests (`pytest -m security`)
- Input validation and sanitization
- File path security
- Resource usage limits
- Error information disclosure prevention

## Running Tests

### Quick Test Run
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=q --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m backward_compatibility
```

### Comprehensive Test Run
```bash
# Full test suite with coverage
pytest --cov=q --cov-report=html --cov-report=term-missing --cov-fail-under=90

# Performance benchmarking
pytest -m performance --benchmark-only

# Extended stress testing
pytest -m slow
```

### Development Testing
```bash
# Watch mode for development
pytest --looponfail

# Parallel execution
pytest -n auto

# Verbose output
pytest -v --tb=short

# Test specific functionality
pytest tests/test_text_generator.py::TestTextGenerator::test_basic_generation
```

## Test Fixtures and Utilities

### Key Fixtures
- `mock_provider` - Mock LLM provider for testing
- `mock_config_manager` - Test configuration manager
- `temp_config_file` - Temporary configuration file
- `sample_messages` - Test message history
- `capture_output` - Capture stdout/stderr

### Test Utilities
- `MockProvider` - Configurable mock provider class
- `create_test_image_data()` - Generate test image data
- `assert_response_format()` - Validate response format
- `assert_valid_image_data()` - Validate image data

## Quality Standards

### Coverage Requirements
- **≥90% line coverage** across all modules
- **≥85% branch coverage** for critical paths
- **100% coverage** for public APIs

### Performance Benchmarks
- **API Response**: p95 < 200ms (mocked)
- **Test Execution**: < 5 minutes total
- **Memory Usage**: < 100MB peak
- **Concurrent Safety**: 10 threads, no race conditions

### Compatibility Standards
- **CLI Interface**: 100% argument compatibility
- **Configuration**: Exact file format match
- **Output Format**: Identical text processing
- **Error Messages**: Same error codes and messages

## CI/CD Integration

The test suite integrates with GitHub Actions for:

- **Multi-platform testing** (Ubuntu, Windows, macOS)
- **Multi-version testing** (Python 3.8-3.12)
- **Automated coverage reporting**
- **Performance regression detection**
- **Security vulnerability scanning**
- **Code quality enforcement**

### Workflow Jobs
- `test` - Core test execution across matrix
- `extended-tests` - Performance and stress testing
- `code-quality` - Linting, formatting, security
- `compatibility` - Installation and CLI testing
- `release-readiness` - Full validation for releases

## Test Data and Mocking

### Mock Strategies
- **External APIs**: Mock OpenAI client responses
- **File System**: Mock file operations for safety
- **Network**: No real network calls in tests
- **Time**: Controllable time for consistent testing

### Test Data
- **Sample Prompts**: Variety of input scenarios
- **Expected Responses**: Known good outputs
- **Edge Cases**: Empty, large, malformed inputs
- **Error Scenarios**: Network failures, invalid keys

## Troubleshooting

### Common Issues
- **Import Errors**: Ensure package is installed in editable mode (`pip install -e .`)
- **Slow Tests**: Use `-m "not slow"` to skip extended tests
- **Permission Errors**: Run with appropriate permissions for file tests
- **Memory Issues**: Increase available memory or skip memory tests

### Debug Mode
```bash
# Run with debug output
pytest --log-cli-level=DEBUG

# Drop into debugger on failure
pytest --pdb

# Show local variables on failure
pytest --tb=long --showlocals
```

## Contributing to Tests

### Test Development Guidelines
1. **Naming**: Use descriptive test names explaining the scenario
2. **Structure**: Follow Arrange-Act-Assert pattern
3. **Isolation**: Each test should be independent
4. **Speed**: Keep unit tests fast, mark slow tests appropriately
5. **Coverage**: Aim for comprehensive path coverage

### Adding New Tests
1. Choose appropriate test module or create new one
2. Use existing fixtures and utilities where possible
3. Add appropriate markers (`@pytest.mark.unit`, etc.)
4. Include both positive and negative test cases
5. Document any special setup requirements

### Test Maintenance
- **Update mocks** when implementation changes
- **Maintain fixtures** as interfaces evolve
- **Review coverage** to identify gaps
- **Performance baselines** may need adjustment
- **Backward compatibility** tests are critical - handle with care

## Performance Baselines

Current performance expectations (with mock providers):

| Operation | Baseline | Maximum |
|-----------|----------|---------|
| Text Generation | 50ms | 200ms |
| Image Generation | 100ms | 500ms |
| History Export | 10ms | 50ms |
| Configuration Load | 5ms | 20ms |
| CLI Startup | 100ms | 300ms |

These baselines are updated as the system evolves and should reflect realistic expectations for production usage.