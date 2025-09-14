# FSM Agent Test Suite 🧪

Comprehensive test suite for the LangGraph-based FSM (Finite State Machine) Agent for plant disease diagnosis and prescription.

## 📋 Test Overview

This test suite validates all aspects of the FSM agent functionality including:

- **Classification**: CNN-based disease detection
- **Context Extraction**: NLP-based user input parsing
- **Vendor Integration**: Local vendor search and ordering
- **Streaming Workflow**: Real-time response delivery
- **Performance & Load**: Concurrent sessions and response times
- **Error Handling**: Edge cases and recovery mechanisms

## 🚀 Quick Start

### Prerequisites

1. **Start the FSM Agent Server:**
   ```bash
   cd engine/fsm_agent
   python run_fsm_server.py --port 8002
   ```

2. **Ensure Dependencies are Available:**
   - Ollama server running (for LLM functionality)
   - Base64 image test files (optional, fallback samples provided)
   - Required Python packages installed

### Run All Tests

```bash
# Run the complete test suite
./run_all_tests.sh
```

### Run Individual Tests

```bash
# Classification and basic functionality
./test_fsm_classification.sh

# Context extraction capabilities
./test_context_extraction.sh

# Vendor integration features
./test_vendor_integration.sh

# Complete streaming workflow
./test_streaming_workflow.sh

# Performance and load testing
./test_performance_load.sh

# Error handling and edge cases
./test_error_handling.sh
```

## 📊 Test Scripts Description

| Script | Purpose | Duration | Key Features |
|--------|---------|----------|--------------|
| `test_fsm_classification.sh` | Disease classification with images | ~2 min | CNN integration, attention visualization |
| `test_context_extraction.sh` | NLP context parsing | ~3 min | Location, plant type, season extraction |
| `test_vendor_integration.sh` | Vendor search and ordering | ~4 min | Price filtering, location-based search |
| `test_streaming_workflow.sh` | End-to-end streaming workflow | ~5 min | Complete diagnosis-to-order flow |
| `test_performance_load.sh` | Performance and concurrency | ~3 min | Response times, concurrent sessions |
| `test_error_handling.sh` | Error conditions and recovery | ~2 min | Invalid inputs, edge cases |

## 🔧 Test Configuration

### Server Configuration
- **Default URL**: `http://localhost:8002`
- **API Prefix**: `/sasya-chikitsa/`
- **Timeout**: 300 seconds per test
- **Log Directory**: `/tmp/fsm_test_results/`

### Test Data
- **Image Files**: Various base64 encoded plant leaf images
- **Fallback Images**: 1x1 PNG samples when test images unavailable
- **Test Contexts**: Multiple location/crop/season combinations
- **Error Cases**: Invalid inputs, malformed JSON, large payloads

## 📈 Test Results

### Output Formats
- **Console Output**: Real-time test progress and results
- **Log Files**: Detailed logs for each test in `/tmp/fsm_test_results/`
- **Test Report**: Comprehensive markdown report with summary

### Success Criteria
- ✅ **Pass**: Test completes successfully within timeout
- ❌ **Fail**: Test encounters errors or times out
- ⚠️ **Skip**: Test script not found or prerequisites missing

### Example Results
```
🎯 Test Suite Completed!
========================

📊 Final Results:
   Total Tests: 6
   Passed: ✅ 6
   Failed: ❌ 0
   Skipped: ⚠️ 0
   Success Rate: 100%
```

## 🧪 Individual Test Details

### 1. Classification Test (`test_fsm_classification.sh`)

**Purpose**: Tests CNN-based disease classification and basic agent functionality.

**Test Cases**:
- Health check validation
- Basic classification with image input
- Streaming classification with progress updates
- Session information retrieval
- Classification results extraction
- Prescription data generation
- Agent statistics monitoring

**Expected Results**:
- Disease classification with confidence scores
- Attention visualization (base64 overlay)
- Treatment recommendations
- Valid session state management

### 2. Context Extraction Test (`test_context_extraction.sh`)

**Purpose**: Validates NLP-based context extraction from user messages.

**Test Cases**:
- Location extraction (Indian states/cities)
- Plant type identification (vegetables, fruits, cereals)
- Season detection (summer, monsoon, winter)
- Growth stage recognition (seedling, flowering, fruiting)
- Urgency level assessment
- User experience level detection
- Treatment preference identification

**Expected Results**:
- Accurate location parsing from natural language
- Correct plant type identification
- Proper seasonal context extraction
- Valid urgency and preference detection

### 3. Vendor Integration Test (`test_vendor_integration.sh`)

**Purpose**: Tests vendor search, pricing, and order simulation functionality.

**Test Cases**:
- Chemical treatment vendor search
- Organic treatment vendor search
- Vendor selection and order simulation
- Location-based vendor filtering
- Price range and budget filtering
- Session cleanup and statistics

**Expected Results**:
- Relevant vendor options with pricing
- Accurate location-based filtering
- Successful order simulation
- Proper cost calculations and delivery estimates

### 4. Streaming Workflow Test (`test_streaming_workflow.sh`)

**Purpose**: Tests complete end-to-end workflow with streaming responses.

**Test Cases**:
- Initial classification request with streaming
- Vendor information request continuation
- Order processing simulation
- Follow-up question handling
- Session state management across workflow
- Complete conversation history tracking

**Expected Results**:
- Real-time streaming responses
- Smooth state transitions
- Complete workflow from diagnosis to order
- Persistent session data across interactions

### 5. Performance Load Test (`test_performance_load.sh`)

**Purpose**: Measures performance characteristics and concurrent handling.

**Test Cases**:
- Response time measurement for different operations
- Concurrent session handling (5 sessions)
- Memory and resource usage monitoring
- Streaming performance measurement
- Bulk session cleanup performance

**Expected Results**:
- Response times < 2 seconds for basic operations
- Successful concurrent session handling
- Stable memory usage patterns
- Efficient streaming performance

### 6. Error Handling Test (`test_error_handling.sh`)

**Purpose**: Validates error conditions, edge cases, and recovery mechanisms.

**Test Cases**:
- Invalid input handling (empty messages, malformed JSON)
- Session management edge cases (non-existent sessions)
- Large input handling (long messages, large images)
- Concurrent error conditions
- State transition error recovery
- API endpoint edge cases

**Expected Results**:
- Graceful error handling with proper HTTP status codes
- Meaningful error messages
- Session state preservation during errors
- Successful recovery from error conditions

## 🛠️ Troubleshooting

### Common Issues

1. **Server Not Running**
   ```bash
   ❌ Server not running at http://localhost:8002
   ```
   **Solution**: Start the FSM server with `python run_fsm_server.py --port 8002`

2. **Ollama Connection Failed**
   ```bash
   ⚠️ LLM-dependent tests failed (likely due to Ollama not being available)
   ```
   **Solution**: Start Ollama server and ensure model is available

3. **Permission Denied**
   ```bash
   bash: ./test_script.sh: Permission denied
   ```
   **Solution**: Make scripts executable with `chmod +x tests/*.sh`

4. **Test Image Files Missing**
   ```bash
   ⚠️ No image files found, using fallback sample image
   ```
   **Solution**: This is expected behavior; tests use fallback images

### Debug Mode

Run individual tests with debug output:
```bash
bash -x test_fsm_classification.sh
```

### Manual Testing

Test individual endpoints manually:
```bash
# Health check
curl -s http://localhost:8002/health | jq '.'

# Basic chat
curl -X POST http://localhost:8002/sasya-chikitsa/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "manual-test", "message": "Hello", "context": {"test_mode": true}}'
```

## 📁 Log Management

### Log Locations
- **Test Logs**: `/tmp/fsm_test_results/test_*.log`
- **Test Report**: `/tmp/fsm_test_results/test_report.md`
- **Performance Logs**: `/tmp/fsm_performance_logs/`

### Log Cleanup
```bash
# Clean up test logs
rm -rf /tmp/fsm_test_results/
rm -rf /tmp/fsm_performance_logs/

# Clean up server sessions
curl -X POST http://localhost:8002/sasya-chikitsa/cleanup
```

## 🚀 Continuous Integration

### Automated Testing
```bash
# Run in CI/CD pipeline
./run_all_tests.sh || exit 1
```

### Test Reporting
- Results are saved in machine-readable formats
- Markdown reports can be integrated into documentation
- JSON logs available for automated analysis

### Performance Monitoring
- Response time tracking
- Memory usage monitoring
- Concurrent session limits testing
- Error rate measurement

## 🔄 Adding New Tests

### Test Script Template
```bash
#!/bin/bash
# New Test Script Template

set -e

SERVER_URL="http://localhost:8002"

echo "🧪 My New Test"
echo "=============="

# Server availability check
if ! curl -s "$SERVER_URL/health" > /dev/null 2>&1; then
    echo "❌ Server not running"
    exit 1
fi

# Test implementation here
echo "✅ Test completed!"
```

### Integration Steps
1. Create new test script in `tests/` directory
2. Make it executable: `chmod +x new_test.sh`
3. Add to `TEST_SCRIPTS` array in `run_all_tests.sh`
4. Update this README with test description

## 📝 Contributing

When adding new tests:
1. Follow the existing naming convention
2. Include proper error handling
3. Clean up created sessions
4. Add descriptive output messages
5. Update documentation

## 🏆 Test Quality Standards

- **Reliability**: Tests should pass consistently
- **Independence**: Tests should not depend on each other
- **Cleanup**: Tests should clean up resources
- **Documentation**: Tests should be self-documenting
- **Performance**: Tests should complete within reasonable time

---

*FSM Agent Test Suite - Ensuring reliability and quality for plant disease diagnosis! 🌱🤖*

