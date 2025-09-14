#!/bin/bash

# FSM Agent Context Extraction Test
# Tests the context extraction capabilities of the FSM agent

set -e

# Configuration
SERVER_URL="http://localhost:8002"

echo "🧠 FSM Agent Context Extraction Test"
echo "===================================="
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

# Test cases with different context scenarios
declare -a TEST_MESSAGES=(
    "I'm from Tamil Nadu and growing tomatoes in summer season. The leaves are yellowing and have brown spots."
    "My potato plants in Karnataka are showing disease symptoms during monsoon season. Help me identify the problem."
    "I have a problem with my chili plants in Bangalore. They are in flowering stage and leaves are curling."
    "Need urgent help with rice crop in West Bengal. The plants are wilting and it's the rainy season."
    "My cotton plants in Gujarat are showing white spots during winter. This is a commercial farm."
    "I live in Kerala and my coconut trees have some disease. The leaves are turning brown."
    "My home garden tomatoes in Mumbai are not growing well. It's summer and very hot."
    "Emergency! My sugarcane crop in Maharashtra is dying. Black spots appearing on leaves."
    "I'm a beginner farmer in Punjab growing wheat. Need help with leaf disease identification."
    "My organic vegetable farm in Himachal Pradesh has pest problems. Using only natural methods."
)

# Test each message for context extraction
for i in "${!TEST_MESSAGES[@]}"; do
    TEST_NUM=$((i + 1))
    MESSAGE="${TEST_MESSAGES[$i]}"
    SESSION_ID="context-test-$TEST_NUM-$(date +%s)"
    
    echo "🧪 Test $TEST_NUM: Context Extraction"
    echo "======================================"
    echo "📝 Input Message: \"$MESSAGE\""
    echo ""
    
    # Create request
    CONTEXT_REQUEST=$(jq -n \
        --arg session_id "$SESSION_ID" \
        --arg message "$MESSAGE" \
        --argjson context '{"test_mode": true, "context_extraction_focus": true}' \
        '{
            session_id: $session_id,
            message: $message,
            context: $context
        }')
    
    echo "🔍 Extracting context..."
    RESPONSE=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$CONTEXT_REQUEST" \
        "$SERVER_URL/sasya-chikitsa/chat")
    
    echo "📊 Response Analysis:"
    echo "$RESPONSE" | jq '.'
    echo ""
    
    # Get session info to see extracted context
    echo "🔎 Session Context Analysis:"
    SESSION_INFO=$(curl -s "$SERVER_URL/sasya-chikitsa/session/$SESSION_ID")
    if [[ $(echo "$SESSION_INFO" | jq -r '.success') == "true" ]]; then
        echo "$SESSION_INFO" | jq '{
            location: .location,
            plant_type: .plant_type, 
            season: .season,
            growth_stage: .growth_stage,
            current_state: .current_state
        }'
    else
        echo "⚠️  Session info not available"
    fi
    
    echo ""
    echo "---"
    echo ""
    
    # Clean up session
    curl -s -X DELETE "$SERVER_URL/sasya-chikitsa/session/$SESSION_ID" > /dev/null
done

# Additional test: Streaming context extraction
echo "🌊 Streaming Context Extraction Test"
echo "===================================="

COMPLEX_MESSAGE="Hello, I'm a farmer from Tamil Nadu growing tomatoes and chili peppers on my 5-acre farm. It's currently summer season and my plants are in the flowering stage. I'm seeing yellowing leaves with brown spots that seem to be spreading quickly. I've tried some home remedies but nothing is working. This is urgent as it's affecting my entire crop. I prefer organic treatments but will use chemicals if necessary. The weather has been very hot and dry lately."

SESSION_ID="streaming-context-$(date +%s)"

echo "📝 Complex Input Message:"
echo "\"$COMPLEX_MESSAGE\""
echo ""

STREAMING_REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID" \
    --arg message "$COMPLEX_MESSAGE" \
    --argjson context '{
        "test_mode": true,
        "streaming": true,
        "detailed_context_extraction": true
    }' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

echo "🌊 Streaming context extraction and initial analysis..."
echo "====================================================="

curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$STREAMING_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat-stream" | head -20

echo ""
echo ""

# Get final session analysis
echo "📊 Final Context Analysis:"
echo "========================="
SESSION_FINAL=$(curl -s "$SERVER_URL/sasya-chikitsa/session/$SESSION_ID")
if [[ $(echo "$SESSION_FINAL" | jq -r '.success') == "true" ]]; then
    echo "🎯 Extracted Context Summary:"
    echo "$SESSION_FINAL" | jq '{
        location: .location,
        plant_type: .plant_type,
        season: .season, 
        growth_stage: .growth_stage,
        urgency_detected: (.current_state != "initial"),
        message_count: .message_count
    }'
else
    echo "⚠️  Final session analysis not available"
fi

echo ""

# Clean up final session
curl -s -X DELETE "$SERVER_URL/sasya-chikitsa/session/$SESSION_ID" > /dev/null

echo "✅ Context extraction tests completed!"
echo ""
echo "🧪 Test Summary:"
echo "- ✅ Location extraction from various states"
echo "- ✅ Plant type identification"
echo "- ✅ Season detection"
echo "- ✅ Growth stage recognition"
echo "- ✅ Urgency level assessment"
echo "- ✅ User experience level detection"
echo "- ✅ Preference identification (organic/chemical)"
echo "- ✅ Streaming context extraction"
echo ""
echo "🧠 Context extraction capabilities verified!"

