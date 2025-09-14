#!/bin/bash

# FSM Agent Performance and Load Test
# Tests concurrent sessions, response times, and resource usage

set -e

# Configuration
SERVER_URL="http://localhost:8002"
CONCURRENT_SESSIONS=5
TEST_DURATION=30  # seconds
LOG_DIR="/tmp/fsm_performance_logs"

echo "⚡ FSM Agent Performance and Load Test"
echo "======================================"
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

# Create log directory
mkdir -p "$LOG_DIR"
rm -f "$LOG_DIR"/*

# Test 1: Response Time Measurement
echo "🧪 Test 1: Response Time Measurement"
echo "===================================="

echo "⏱️  Measuring response times for different operations..."

# Health check response time
echo "📍 Health Check Response Time:"
time curl -s "$SERVER_URL/health" > /dev/null
echo ""

# Basic chat response time
SESSION_ID_TIMING="timing-test-$(date +%s)"

BASIC_REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID_TIMING" \
    --arg message "Hello, I need help with plant disease diagnosis." \
    --argjson context '{"test_mode": true}' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

echo "💬 Basic Chat Response Time:"
time curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$BASIC_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat" > /dev/null
echo ""

# Classification response time (with small image)
SMALL_IMAGE="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQYV2NgAAIAAAUAAarVyFEAAAAASUVORK5CYII="

CLASSIFICATION_REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID_TIMING" \
    --arg message "Please analyze this plant image for diseases." \
    --arg image_b64 "$SMALL_IMAGE" \
    --argjson context '{"test_mode": true}' \
    '{
        session_id: $session_id,
        message: $message,
        image_b64: $image_b64,
        context: $context
    }')

echo "🔬 Classification Response Time:"
time curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$CLASSIFICATION_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat" > /dev/null
echo ""

# Session info response time
echo "📋 Session Info Response Time:"
time curl -s "$SERVER_URL/sasya-chikitsa/session/$SESSION_ID_TIMING" > /dev/null
echo ""

# Clean up timing session
curl -s -X DELETE "$SERVER_URL/sasya-chikitsa/session/$SESSION_ID_TIMING" > /dev/null

# Test 2: Concurrent Session Test
echo "🧪 Test 2: Concurrent Session Test"
echo "=================================="

echo "🔄 Starting $CONCURRENT_SESSIONS concurrent sessions..."

# Function to run a session test
run_concurrent_session() {
    local session_num=$1
    local session_id="concurrent-$session_num-$(date +%s)"
    local log_file="$LOG_DIR/session_${session_num}.log"
    
    echo "Session $session_num started" >> "$log_file"
    
    # Create session request
    local request=$(jq -n \
        --arg session_id "$session_id" \
        --arg message "I have a plant disease problem in location-$session_num. Please help me with diagnosis and treatment." \
        --argjson context '{
            "test_mode": true,
            "session_number": '$session_num',
            "location": "TestLocation-'$session_num'",
            "concurrent_test": true
        }' \
        '{
            session_id: $session_id,
            message: $message,
            context: $context
        }')
    
    # Send initial request
    local start_time=$(date +%s.%N)
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$request" \
        "$SERVER_URL/sasya-chikitsa/chat" >> "$log_file" 2>&1
    local end_time=$(date +%s.%N)
    
    local response_time=$(echo "$end_time - $start_time" | bc)
    echo "Session $session_num: Initial response time: ${response_time}s" >> "$log_file"
    
    # Follow-up request
    local followup_request=$(jq -n \
        --arg session_id "$session_id" \
        --arg message "Can you also show me vendor options?" \
        --argjson context '{"test_mode": true}' \
        '{
            session_id: $session_id,
            message: $message,
            context: $context
        }')
    
    start_time=$(date +%s.%N)
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$followup_request" \
        "$SERVER_URL/sasya-chikitsa/chat" >> "$log_file" 2>&1
    end_time=$(date +%s.%N)
    
    response_time=$(echo "$end_time - $start_time" | bc)
    echo "Session $session_num: Follow-up response time: ${response_time}s" >> "$log_file"
    
    # Get session info
    curl -s "$SERVER_URL/sasya-chikitsa/session/$session_id" >> "$log_file" 2>&1
    
    echo "Session $session_num completed" >> "$log_file"
    echo "$session_id" > "$LOG_DIR/session_${session_num}_id.txt"
}

# Start concurrent sessions
pids=()
for i in $(seq 1 $CONCURRENT_SESSIONS); do
    run_concurrent_session $i &
    pids+=($!)
    echo "  🚀 Started session $i (PID: ${pids[-1]})"
done

echo ""
echo "⏳ Waiting for all concurrent sessions to complete..."

# Wait for all sessions to complete
for pid in "${pids[@]}"; do
    wait $pid
done

echo "✅ All concurrent sessions completed!"
echo ""

# Analyze results
echo "📊 Concurrent Session Results:"
echo "==============================="

total_sessions=0
successful_sessions=0
failed_sessions=0

for i in $(seq 1 $CONCURRENT_SESSIONS); do
    log_file="$LOG_DIR/session_${i}.log"
    if [[ -f "$log_file" ]]; then
        total_sessions=$((total_sessions + 1))
        if grep -q "completed" "$log_file"; then
            successful_sessions=$((successful_sessions + 1))
        else
            failed_sessions=$((failed_sessions + 1))
        fi
        
        # Extract response times
        echo "Session $i:"
        grep "response time" "$log_file" || echo "  No timing data available"
    fi
done

echo ""
echo "📈 Summary:"
echo "- Total Sessions: $total_sessions"
echo "- Successful: $successful_sessions"
echo "- Failed: $failed_sessions"
echo "- Success Rate: $(( successful_sessions * 100 / total_sessions ))%"
echo ""

# Test 3: Memory and Resource Usage
echo "🧪 Test 3: Memory and Resource Usage"
echo "===================================="

echo "💾 Getting initial agent statistics..."
STATS_INITIAL=$(curl -s "$SERVER_URL/sasya-chikitsa/stats")
echo "📊 Initial Stats:"
echo "$STATS_INITIAL" | jq '{active_sessions, total_messages}'
echo ""

echo "🔄 Creating multiple sessions to test memory usage..."

# Create several sessions with different workloads
session_ids=()
for i in $(seq 1 10); do
    session_id="memory-test-$i-$(date +%s)"
    session_ids+=("$session_id")
    
    # Create varied requests
    if [[ $((i % 3)) -eq 0 ]]; then
        # Image classification request
        request=$(jq -n \
            --arg session_id "$session_id" \
            --arg message "Memory test $i: Analyze this image for plant diseases" \
            --arg image_b64 "$SMALL_IMAGE" \
            --argjson context '{"test_mode": true, "memory_test": true}' \
            '{
                session_id: $session_id,
                message: $message,
                image_b64: $image_b64,
                context: $context
            }')
    else
        # Text-only request
        request=$(jq -n \
            --arg session_id "$session_id" \
            --arg message "Memory test $i: I need help with plant disease diagnosis and vendor recommendations" \
            --argjson context '{"test_mode": true, "memory_test": true}' \
            '{
                session_id: $session_id,
                message: $message,
                context: $context
            }')
    fi
    
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$request" \
        "$SERVER_URL/sasya-chikitsa/chat" > /dev/null
    
    echo "  📝 Created session $i: $session_id"
done

echo ""
echo "💾 Getting post-load agent statistics..."
STATS_LOADED=$(curl -s "$SERVER_URL/sasya-chikitsa/stats")
echo "📊 Loaded Stats:"
echo "$STATS_LOADED" | jq '{active_sessions, total_messages}'
echo ""

# Test 4: Streaming Performance
echo "🧪 Test 4: Streaming Performance"
echo "================================"

echo "🌊 Testing streaming response performance..."

STREAM_SESSION="streaming-perf-$(date +%s)"
STREAM_REQUEST=$(jq -n \
    --arg session_id "$STREAM_SESSION" \
    --arg message "Please provide a detailed analysis of plant disease management including classification, prescription, and vendor recommendations. Stream the complete workflow." \
    --argjson context '{
        "test_mode": true,
        "performance_test": true,
        "streaming": true
    }' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

echo "⏱️  Measuring streaming response time..."
start_time=$(date +%s.%N)

curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$STREAM_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat-stream" > "$LOG_DIR/streaming_response.log"

end_time=$(date +%s.%N)
stream_time=$(echo "$end_time - $start_time" | bc)

echo "📊 Streaming Performance Results:"
echo "- Total streaming time: ${stream_time}s"
echo "- Response size: $(wc -c < "$LOG_DIR/streaming_response.log") bytes"
echo "- Line count: $(wc -l < "$LOG_DIR/streaming_response.log") lines"
echo ""

# Test 5: Cleanup Performance
echo "🧪 Test 5: Cleanup Performance"
echo "=============================="

echo "🧹 Testing bulk session cleanup performance..."

cleanup_start=$(date +%s.%N)

# Clean up all test sessions
for session_id in "${session_ids[@]}"; do
    curl -s -X DELETE "$SERVER_URL/sasya-chikitsa/session/$session_id" > /dev/null
done

# Clean up streaming session
curl -s -X DELETE "$SERVER_URL/sasya-chikitsa/session/$STREAM_SESSION" > /dev/null

# Clean up concurrent session IDs
for i in $(seq 1 $CONCURRENT_SESSIONS); do
    id_file="$LOG_DIR/session_${i}_id.txt"
    if [[ -f "$id_file" ]]; then
        session_id=$(cat "$id_file")
        curl -s -X DELETE "$SERVER_URL/sasya-chikitsa/session/$session_id" > /dev/null
        rm -f "$id_file"
    fi
done

cleanup_end=$(date +%s.%N)
cleanup_time=$(echo "$cleanup_end - $cleanup_start" | bc)

echo "📊 Cleanup Performance:"
echo "- Cleanup time: ${cleanup_time}s"
echo "- Sessions cleaned: $((${#session_ids[@]} + CONCURRENT_SESSIONS + 1))"
echo ""

# Final statistics
echo "💾 Final agent statistics..."
STATS_FINAL=$(curl -s "$SERVER_URL/sasya-chikitsa/stats")
echo "📊 Final Stats:"
echo "$STATS_FINAL" | jq '{active_sessions, total_messages}'
echo ""

echo "✅ Performance and load testing completed!"
echo ""
echo "🧪 Test Summary:"
echo "- ✅ Response time measurement"
echo "- ✅ Concurrent session handling ($CONCURRENT_SESSIONS sessions)"
echo "- ✅ Memory and resource usage testing"
echo "- ✅ Streaming performance measurement"
echo "- ✅ Cleanup performance testing"
echo ""
echo "📁 Log files available in: $LOG_DIR"
echo "⚡ Performance testing complete!"

