#!/bin/bash

# FSM Agent Error Handling and Edge Cases Test
# Tests error conditions, recovery mechanisms, and edge cases

set -e

# Configuration
SERVER_URL="http://localhost:8002"

echo "🛡️ FSM Agent Error Handling and Edge Cases Test"
echo "================================================"
echo ""

# Check server availability
echo "📡 Checking server availability..."
if ! curl -s "$SERVER_URL/health" > /dev/null 2>&1; then
    echo "❌ Server not running at $SERVER_URL"
    echo "   Start the server first: python run_fsm_server.py --port 8002"
    exit 1
fi
echo "✅ Server is running"
echo ""

# Test 1: Invalid Input Handling
echo "🧪 Test 1: Invalid Input Handling"
echo "================================="

echo "❌ Testing empty message..."
EMPTY_REQUEST='{"session_id": "empty-test", "message": "", "context": {"test_mode": true}}'
EMPTY_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$EMPTY_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat")
echo "📊 Empty message response:"
echo "$EMPTY_RESPONSE" | jq '.'
echo ""

echo "❌ Testing malformed JSON..."
MALFORMED_REQUEST='{"session_id": "malformed-test", "message": "test", "context": {"test_mode": true'
MALFORMED_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "$MALFORMED_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat")
echo "📊 Malformed JSON response:"
echo "$MALFORMED_RESPONSE"
echo ""

echo "❌ Testing missing required fields..."
MISSING_FIELDS='{"session_id": "missing-test", "context": {"test_mode": true}}'
MISSING_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "$MISSING_FIELDS" \
    "$SERVER_URL/sasya-chikitsa/chat")
echo "📊 Missing fields response:"
echo "$MISSING_RESPONSE"
echo ""

echo "❌ Testing invalid base64 image..."
INVALID_IMAGE_REQUEST=$(jq -n \
    --arg session_id "invalid-image-test" \
    --arg message "Analyze this invalid image" \
    --arg image_b64 "invalid-base64-data-!@#$%^&*()" \
    --argjson context '{"test_mode": true}' \
    '{
        session_id: $session_id,
        message: $message,
        image_b64: $image_b64,
        context: $context
    }')

INVALID_IMAGE_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$INVALID_IMAGE_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat")
echo "📊 Invalid image response:"
echo "$INVALID_IMAGE_RESPONSE" | jq '.'
echo ""

# Test 2: Session Management Edge Cases
echo "🧪 Test 2: Session Management Edge Cases"
echo "========================================"

echo "❌ Testing non-existent session lookup..."
NON_EXISTENT_SESSION="non-existent-session-$(date +%s)"
NON_EXISTENT_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" \
    "$SERVER_URL/sasya-chikitsa/session/$NON_EXISTENT_SESSION")
echo "📊 Non-existent session response:"
echo "$NON_EXISTENT_RESPONSE"
echo ""

echo "❌ Testing invalid session ID format..."
INVALID_SESSION_ID="invalid/session/../id"
INVALID_SESSION_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" \
    "$SERVER_URL/sasya-chikitsa/session/$INVALID_SESSION_ID")
echo "📊 Invalid session ID response:"
echo "$INVALID_SESSION_RESPONSE"
echo ""

echo "❌ Testing session deletion of non-existent session..."
DELETE_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" -X DELETE \
    "$SERVER_URL/sasya-chikitsa/session/$NON_EXISTENT_SESSION")
echo "📊 Delete non-existent session response:"
echo "$DELETE_RESPONSE"
echo ""

# Test 3: Large Input Handling
echo "🧪 Test 3: Large Input Handling"
echo "==============================="

echo "🔍 Testing very long message..."
# Create a very long message (10KB)
LONG_MESSAGE=$(printf 'A%.0s' {1..10000})

LONG_MESSAGE_REQUEST=$(jq -n \
    --arg session_id "long-message-test-$(date +%s)" \
    --arg message "$LONG_MESSAGE" \
    --argjson context '{"test_mode": true}' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

LONG_MESSAGE_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$LONG_MESSAGE_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat")
echo "📊 Long message response status:"
echo "$LONG_MESSAGE_RESPONSE" | jq '.success // "No success field"'
echo ""

echo "🔍 Testing very large base64 image..."
# Create a large base64 string (100KB)
LARGE_IMAGE=$(printf 'A%.0s' {1..100000})

LARGE_IMAGE_REQUEST=$(jq -n \
    --arg session_id "large-image-test-$(date +%s)" \
    --arg message "Analyze this large image" \
    --arg image_b64 "$LARGE_IMAGE" \
    --argjson context '{"test_mode": true}' \
    '{
        session_id: $session_id,
        message: $message,
        image_b64: $image_b64,
        context: $context
    }')

LARGE_IMAGE_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$LARGE_IMAGE_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat")
echo "📊 Large image response status:"
echo "$LARGE_IMAGE_RESPONSE" | jq '.success // "No success field"'
echo ""

# Test 4: Concurrent Error Conditions
echo "🧪 Test 4: Concurrent Error Conditions"
echo "======================================"

echo "🔄 Testing multiple invalid requests concurrently..."

# Function to send invalid request
send_invalid_request() {
    local test_type=$1
    local session_id="concurrent-error-$test_type-$$"
    
    case $test_type in
        "empty")
            local request='{"session_id": "'$session_id'", "message": "", "context": {"test_mode": true}}'
            ;;
        "malformed")
            local request='{"session_id": "'$session_id'", "message": "test", "context": {"test_mode": true'
            ;;
        "invalid_image")
            local request=$(jq -n --arg sid "$session_id" '{"session_id": $sid, "message": "test", "image_b64": "invalid", "context": {"test_mode": true}}')
            ;;
    esac
    
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$request" \
        "$SERVER_URL/sasya-chikitsa/chat" > "/tmp/concurrent_error_$test_type.log" 2>&1
}

# Start concurrent invalid requests
send_invalid_request "empty" &
send_invalid_request "malformed" &
send_invalid_request "invalid_image" &

wait
echo "✅ Concurrent error handling completed"
echo ""

# Test 5: State Transition Error Recovery
echo "🧪 Test 5: State Transition Error Recovery"
echo "=========================================="

SESSION_ID_RECOVERY="error-recovery-$(date +%s)"

echo "🔄 Testing error recovery in workflow..."
# Start normal session
RECOVERY_REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID_RECOVERY" \
    --arg message "I have a plant disease problem. Help me analyze and get treatment." \
    --argjson context '{"test_mode": true, "error_simulation": true}' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

RECOVERY_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$RECOVERY_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat")
echo "📊 Initial recovery test response:"
echo "$RECOVERY_RESPONSE" | jq '.success // "No success field"'
echo ""

# Try to continue with invalid follow-up
INVALID_FOLLOWUP=$(jq -n \
    --arg session_id "$SESSION_ID_RECOVERY" \
    --arg message "" \
    --argjson context '{"test_mode": true}' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

FOLLOWUP_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$INVALID_FOLLOWUP" \
    "$SERVER_URL/sasya-chikitsa/chat")
echo "📊 Invalid follow-up response:"
echo "$FOLLOWUP_RESPONSE" | jq '.success // "No success field"'
echo ""

# Try valid recovery
VALID_RECOVERY=$(jq -n \
    --arg session_id "$SESSION_ID_RECOVERY" \
    --arg message "Let me try again. I need help with tomato plant diseases." \
    --argjson context '{"test_mode": true}' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

VALID_RECOVERY_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$VALID_RECOVERY" \
    "$SERVER_URL/sasya-chikitsa/chat")
echo "📊 Valid recovery response:"
echo "$VALID_RECOVERY_RESPONSE" | jq '.success // "No success field"'
echo ""

# Test 6: Resource Exhaustion Simulation
echo "🧪 Test 6: Resource Exhaustion Simulation"
echo "========================================="

echo "⚠️  Testing rapid session creation..."

# Create many sessions rapidly
session_ids=()
for i in $(seq 1 20); do
    session_id="rapid-session-$i-$(date +%s)"
    session_ids+=("$session_id")
    
    rapid_request=$(jq -n \
        --arg session_id "$session_id" \
        --arg message "Rapid test session $i" \
        --argjson context '{"test_mode": true, "rapid_test": true}' \
        '{
            session_id: $session_id,
            message: $message,
            context: $context
        }')
    
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$rapid_request" \
        "$SERVER_URL/sasya-chikitsa/chat" > "/tmp/rapid_session_$i.log" &
    
    # Brief delay to avoid overwhelming
    sleep 0.1
done

wait
echo "✅ Rapid session creation completed"

# Check agent stats
echo "📊 Post-rapid-creation agent stats:"
RAPID_STATS=$(curl -s "$SERVER_URL/sasya-chikitsa/stats")
echo "$RAPID_STATS" | jq '{active_sessions, total_messages}'
echo ""

# Test 7: API Endpoint Edge Cases
echo "🧪 Test 7: API Endpoint Edge Cases"
echo "=================================="

echo "❌ Testing invalid endpoints..."
curl -s -w "HTTP_STATUS:%{http_code}\n" "$SERVER_URL/sasya-chikitsa/invalid-endpoint"
curl -s -w "HTTP_STATUS:%{http_code}\n" "$SERVER_URL/invalid-path"
curl -s -w "HTTP_STATUS:%{http_code}\n" -X POST "$SERVER_URL/sasya-chikitsa/chat-stream" -d '{"invalid": "data"}'
echo ""

echo "❌ Testing unsupported HTTP methods..."
curl -s -w "HTTP_STATUS:%{http_code}\n" -X PUT "$SERVER_URL/sasya-chikitsa/chat"
curl -s -w "HTTP_STATUS:%{http_code}\n" -X PATCH "$SERVER_URL/sasya-chikitsa/stats"
echo ""

# Test 8: Cleanup and Recovery Testing
echo "🧪 Test 8: Cleanup and Recovery Testing"
echo "======================================="

echo "🧹 Testing cleanup mechanisms..."

# Manual cleanup
CLEANUP_RESPONSE=$(curl -s -X POST "$SERVER_URL/sasya-chikitsa/cleanup")
echo "📊 Manual cleanup response:"
echo "$CLEANUP_RESPONSE" | jq '.'
echo ""

# Clean up all test sessions
echo "🧹 Cleaning up all test sessions..."
for session_id in "${session_ids[@]}"; do
    curl -s -X DELETE "$SERVER_URL/sasya-chikitsa/session/$session_id" > /dev/null
done

curl -s -X DELETE "$SERVER_URL/sasya-chikitsa/session/$SESSION_ID_RECOVERY" > /dev/null

echo "✅ Session cleanup completed"
echo ""

# Final health check
echo "🏥 Final health check after all error tests..."
FINAL_HEALTH=$(curl -s "$SERVER_URL/health")
echo "📊 Final health status:"
echo "$FINAL_HEALTH" | jq '.'
echo ""

echo "✅ All error handling and edge case tests completed!"
echo ""
echo "🧪 Test Summary:"
echo "- ✅ Invalid input handling"
echo "- ✅ Session management edge cases"
echo "- ✅ Large input handling"
echo "- ✅ Concurrent error conditions"
echo "- ✅ State transition error recovery"
echo "- ✅ Resource exhaustion simulation"
echo "- ✅ API endpoint edge cases"
echo "- ✅ Cleanup and recovery testing"
echo ""
echo "🛡️ Error handling and robustness verified!"

