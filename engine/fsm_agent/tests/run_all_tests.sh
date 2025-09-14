#!/bin/bash

# FSM Agent Comprehensive Test Suite Runner
# Runs all test scripts in sequence with proper setup and reporting

set -e

# Configuration
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_URL="http://localhost:8002"
LOG_DIR="/tmp/fsm_test_results"
REPORT_FILE="$LOG_DIR/test_report.md"

echo "🚀 FSM Agent Comprehensive Test Suite"
echo "====================================="
echo ""

# Create log directory
mkdir -p "$LOG_DIR"
rm -f "$LOG_DIR"/*

# Test configuration
declare -a TEST_SCRIPTS=(
    "test_fsm_classification.sh"
    "test_context_extraction.sh"
    "test_vendor_integration.sh"
    "test_attention_overlay.sh"
    "test_fsm_streaming_with_image.sh"
    "test_streaming_workflow.sh"
    "test_performance_load.sh"
    "test_error_handling.sh"
)

# Check if server is running
echo "📡 Pre-flight check: Server availability..."
if ! curl -s "$SERVER_URL/health" > /dev/null 2>&1; then
    echo "❌ Server not running at $SERVER_URL"
    echo ""
    echo "🚀 Please start the server first:"
    echo "   cd engine/fsm_agent"
    echo "   python run_fsm_server.py --port 8002"
    echo ""
    echo "⏳ Or run in development mode:"
    echo "   python run_fsm_server.py --port 8002 --log-level debug --reload"
    echo ""
    exit 1
fi
echo "✅ Server is running and healthy"
echo ""

# Get initial server stats
echo "📊 Initial server statistics..."
INITIAL_STATS=$(curl -s "$SERVER_URL/sasya-chikitsa/stats")
echo "$INITIAL_STATS" | jq '.'
echo ""

# Initialize report
cat > "$REPORT_FILE" << EOF
# FSM Agent Test Report

**Test Run Date:** $(date)
**Server URL:** $SERVER_URL
**Test Suite Version:** 1.0

## Initial Server State
\`\`\`json
$INITIAL_STATS
\`\`\`

## Test Results

EOF

# Variables for tracking
TOTAL_TESTS=${#TEST_SCRIPTS[@]}
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

echo "🧪 Starting comprehensive test suite..."
echo "   Total tests to run: $TOTAL_TESTS"
echo "   Test results will be saved to: $LOG_DIR"
echo ""

# Run each test script
for i in "${!TEST_SCRIPTS[@]}"; do
    TEST_NUM=$((i + 1))
    TEST_SCRIPT="${TEST_SCRIPTS[$i]}"
    TEST_PATH="$TEST_DIR/$TEST_SCRIPT"
    TEST_LOG="$LOG_DIR/test_${TEST_NUM}_$(basename "$TEST_SCRIPT" .sh).log"
    
    echo "🧪 Running Test $TEST_NUM/$TOTAL_TESTS: $TEST_SCRIPT"
    echo "=================================================="
    
    if [[ ! -f "$TEST_PATH" ]]; then
        echo "❌ Test script not found: $TEST_PATH"
        SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
        
        cat >> "$REPORT_FILE" << EOF
### Test $TEST_NUM: $TEST_SCRIPT
**Status:** ❌ SKIPPED (Script not found)
**Log:** N/A

EOF
        continue
    fi
    
    # Make sure script is executable
    chmod +x "$TEST_PATH"
    
    # Run test with timeout and capture output
    TEST_START=$(date +%s)
    if timeout 300s bash "$TEST_PATH" > "$TEST_LOG" 2>&1; then
        TEST_END=$(date +%s)
        TEST_DURATION=$((TEST_END - TEST_START))
        
        echo "✅ Test $TEST_NUM completed successfully in ${TEST_DURATION}s"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        
        # Add to report
        cat >> "$REPORT_FILE" << EOF
### Test $TEST_NUM: $TEST_SCRIPT
**Status:** ✅ PASSED
**Duration:** ${TEST_DURATION}s
**Log:** [\`test_${TEST_NUM}_$(basename "$TEST_SCRIPT" .sh).log\`](./test_${TEST_NUM}_$(basename "$TEST_SCRIPT" .sh).log)

EOF
    else
        TEST_END=$(date +%s)
        TEST_DURATION=$((TEST_END - TEST_START))
        
        echo "❌ Test $TEST_NUM failed or timed out after ${TEST_DURATION}s"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        
        # Show last few lines of error log
        echo "📋 Last 10 lines of error log:"
        tail -10 "$TEST_LOG" || echo "   (No log content available)"
        
        # Add to report
        cat >> "$REPORT_FILE" << EOF
### Test $TEST_NUM: $TEST_SCRIPT
**Status:** ❌ FAILED
**Duration:** ${TEST_DURATION}s
**Log:** [\`test_${TEST_NUM}_$(basename "$TEST_SCRIPT" .sh).log\`](./test_${TEST_NUM}_$(basename "$TEST_SCRIPT" .sh).log)

**Error Summary:**
\`\`\`
$(tail -10 "$TEST_LOG" 2>/dev/null || echo "No log content available")
\`\`\`

EOF
    fi
    
    echo ""
    
    # Brief pause between tests
    sleep 2
done

# Get final server stats
echo "📊 Final server statistics..."
FINAL_STATS=$(curl -s "$SERVER_URL/sasya-chikitsa/stats")
echo "$FINAL_STATS" | jq '.'
echo ""

# Calculate success rate
SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))

# Complete the report
cat >> "$REPORT_FILE" << EOF

## Final Server State
\`\`\`json
$FINAL_STATS
\`\`\`

## Summary

| Metric | Value |
|--------|--------|
| Total Tests | $TOTAL_TESTS |
| Passed | ✅ $PASSED_TESTS |
| Failed | ❌ $FAILED_TESTS |
| Skipped | ⚠️ $SKIPPED_TESTS |
| Success Rate | $SUCCESS_RATE% |

## Test Categories Covered

1. **Classification Testing** - CNN model integration and image analysis
2. **Context Extraction** - NLP-based context parsing from user messages
3. **Vendor Integration** - Vendor search, filtering, and order simulation
4. **Attention Overlay** - Attention visualization retrieval and display functionality
5. **FSM Streaming with Image** - Comprehensive streaming test with real image data and workflow validation
6. **Streaming Workflow** - End-to-end workflow with streaming responses
7. **Performance & Load** - Concurrent sessions and response time testing
8. **Error Handling** - Edge cases, invalid inputs, and recovery mechanisms

## Recommendations

EOF

if [[ $FAILED_TESTS -eq 0 ]]; then
    cat >> "$REPORT_FILE" << EOF
✅ **All tests passed successfully!** The FSM agent is ready for production use.

- Consider running performance tests with higher load
- Monitor resource usage in production environment
- Set up automated testing pipeline
EOF
else
    cat >> "$REPORT_FILE" << EOF
⚠️ **Some tests failed.** Review the failed test logs and address the issues:

- Check failed test logs for specific error details
- Ensure all dependencies are properly installed
- Verify server configuration and resource availability
- Run individual tests for more detailed debugging
EOF
fi

cat >> "$REPORT_FILE" << EOF

---
*Generated by FSM Agent Test Suite v1.0*
EOF

# Display final results
echo "🎯 Test Suite Completed!"
echo "========================"
echo ""
echo "📊 Final Results:"
echo "   Total Tests: $TOTAL_TESTS"
echo "   Passed: ✅ $PASSED_TESTS"
echo "   Failed: ❌ $FAILED_TESTS"
echo "   Skipped: ⚠️ $SKIPPED_TESTS"
echo "   Success Rate: $SUCCESS_RATE%"
echo ""
echo "📁 Detailed Results:"
echo "   Test Logs: $LOG_DIR"
echo "   Test Report: $REPORT_FILE"
echo ""

# Show report location
if [[ -f "$REPORT_FILE" ]]; then
    echo "📋 Detailed test report generated:"
    echo "   File: $REPORT_FILE"
    echo "   View with: cat $REPORT_FILE"
    echo ""
fi

# Test list for reference
echo "📚 Individual Test Scripts:"
for i in "${!TEST_SCRIPTS[@]}"; do
    TEST_NUM=$((i + 1))
    TEST_SCRIPT="${TEST_SCRIPTS[$i]}"
    echo "   $TEST_NUM. $TEST_SCRIPT"
done
echo ""

# Cleanup recommendation
echo "🧹 Cleanup:"
echo "   Test logs are preserved in $LOG_DIR"
echo "   Server sessions should be automatically cleaned up"
echo "   Manual cleanup: curl -X POST $SERVER_URL/sasya-chikitsa/cleanup"
echo ""

# Exit with appropriate code
if [[ $FAILED_TESTS -eq 0 ]]; then
    echo "🎉 All tests passed! FSM Agent is functioning correctly."
    exit 0
else
    echo "⚠️ Some tests failed. Please review the logs and fix the issues."
    exit 1
fi
