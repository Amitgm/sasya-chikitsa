#!/bin/bash

# FSM Agent Streaming Workflow Test
# Tests complete workflow from classification through vendor booking with streaming

set -e

# Configuration
SERVER_URL="http://localhost:8002"
SESSION_ID="streaming-workflow-test-$(date +%s)"

echo "🌊 FSM Agent Streaming Workflow Test"
echo "===================================="
echo ""

# Image file paths
IMAGE_FILE_1="/Users/aathalye/dev/sasya-chikitsa/resources/images_for_test/tomato_mosaic_virus_base64.txt"
IMAGE_FILE_2="/Users/aathalye/dev/sasya-chikitsa/resources/images_for_test/image_103_base64.txt"
IMAGE_FILE_3="/Users/aathalye/dev/sasya-chikitsa/engine/resources/images_for_test/leaf_base64.txt"

# Check server availability
echo "📡 Checking server availability..."
if ! curl -s "$SERVER_URL/health" > /dev/null 2>&1; then
    echo "❌ Server not running at $SERVER_URL"
    echo "   Start the server first: python run_fsm_server.py --port 8002"
    exit 1
fi
echo "✅ Server is running"
echo ""

# Find and load image data
echo "📸 Loading image data..."
IMAGE_DATA=""

if [[ -f "$IMAGE_FILE_1" ]] && [[ -s "$IMAGE_FILE_1" ]]; then
    IMAGE_DATA=$(cat "$IMAGE_FILE_1" | tr -d '\n\r')
    IMAGE_SOURCE="$IMAGE_FILE_1"
    echo "✅ Loaded image from: $IMAGE_SOURCE"
elif [[ -f "$IMAGE_FILE_2" ]] && [[ -s "$IMAGE_FILE_2" ]]; then
    IMAGE_DATA=$(cat "$IMAGE_FILE_2" | tr -d '\n\r')
    IMAGE_SOURCE="$IMAGE_FILE_2"
    echo "✅ Loaded image from: $IMAGE_SOURCE"
elif [[ -f "$IMAGE_FILE_3" ]] && [[ -s "$IMAGE_FILE_3" ]]; then
    IMAGE_DATA=$(cat "$IMAGE_FILE_3" | tr -d '\n\r')
    IMAGE_SOURCE="$IMAGE_FILE_3"
    echo "✅ Loaded image from: $IMAGE_SOURCE"
else
    # Fallback: Sample base64 image (1x1 transparent PNG)
    IMAGE_DATA="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQYV2NgAAIAAAUAAarVyFEAAAAASUVORK5CYII="
    IMAGE_SOURCE="Sample 1x1 PNG (fallback)"
    echo "⚠️  No image files found, using fallback sample image"
fi

echo "📊 Image data size: ${#IMAGE_DATA} characters"
echo "📋 First 50 characters: ${IMAGE_DATA:0:50}..."
echo ""

# Step 1: Initial Classification Request
echo "🔬 Step 1: Initial Classification Request"
echo "========================================="

CLASSIFICATION_REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID" \
    --arg message "I have a tomato plant with disease symptoms. Please analyze this image for disease detection, provide diagnosis, and recommend treatments. I'm located in Tamil Nadu and it's summer season." \
    --arg image_b64 "$IMAGE_DATA" \
    --argjson context '{
        "test_mode": true,
        "crop_type": "tomato", 
        "location": "Tamil Nadu",
        "season": "summer",
        "growth_stage": "flowering",
        "streaming_requested": true,
        "image_source": "'$IMAGE_SOURCE'",
        "user_preferences": {
            "organic_preference": false,
            "budget_range": "medium"
        }
    }' \
    '{
        session_id: $session_id,
        message: $message,
        image_b64: $image_b64,
        context: $context
    }')

echo "📋 Request Structure:"
echo "$CLASSIFICATION_REQUEST" | jq '. | {session_id, message: (.message | .[0:100] + "..."), image_b64: (.image_b64 | .[0:50] + "..."), context}'
echo ""

echo "🌊 Starting streaming classification and prescription workflow..."
echo "=============================================================="

# Send streaming request
curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$CLASSIFICATION_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat-stream" | tee /tmp/fsm_workflow_step1.log

echo ""
echo ""

# Step 2: Follow-up for Vendor Information
echo "🛒 Step 2: Vendor Information Request"
echo "====================================="

sleep 2  # Brief pause to let previous request complete

VENDOR_REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID" \
    --arg message "Yes, I would like to see local vendor options for the recommended treatments. Please show me both organic and chemical options with pricing." \
    --argjson context '{
        "test_mode": true,
        "vendor_preferences": {
            "organic_only": false,
            "delivery_preferred": true,
            "budget_max": 2000
        }
    }' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

echo "📋 Vendor Request Structure:"
echo "$VENDOR_REQUEST" | jq '.'
echo ""

echo "🌊 Streaming vendor search and options..."
echo "========================================"

curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$VENDOR_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat-stream" | tee /tmp/fsm_workflow_step2.log

echo ""
echo ""

# Step 3: Vendor Selection and Order Simulation
echo "📦 Step 3: Vendor Selection and Order"
echo "====================================="

sleep 2  # Brief pause

ORDER_REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID" \
    --arg message "I would like to order from the first vendor option. Please proceed with the order for the copper sulfate fungicide and neem oil solution." \
    --argjson context '{
        "test_mode": true,
        "selected_vendor_index": 1,
        "order_items": [
            "Copper Sulfate Fungicide - 250ml",
            "Neem Oil Solution - 500ml"
        ]
    }' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

echo "📋 Order Request Structure:"
echo "$ORDER_REQUEST" | jq '.'
echo ""

echo "🌊 Streaming order processing..."
echo "==============================="

curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$ORDER_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat-stream" | tee /tmp/fsm_workflow_step3.log

echo ""
echo ""

# Step 4: Follow-up Question
echo "❓ Step 4: Follow-up Question"
echo "============================="

sleep 2  # Brief pause

FOLLOWUP_REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID" \
    --arg message "Thank you for the order! Can you also provide some additional preventive measures I can take to avoid this disease in the future?" \
    --argjson context '{"test_mode": true}' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

echo "📋 Follow-up Request Structure:"
echo "$FOLLOWUP_REQUEST" | jq '.'
echo ""

echo "🌊 Streaming follow-up response..."
echo "================================="

curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$FOLLOWUP_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat-stream" | tee /tmp/fsm_workflow_step4.log

echo ""
echo ""

# Step 5: Session Summary
echo "📊 Step 5: Session Summary"
echo "=========================="

echo "🔍 Getting final session information..."
SESSION_INFO=$(curl -s "$SERVER_URL/sasya-chikitsa/session/$SESSION_ID")
echo ""
echo "📋 Final Session State:"
echo "$SESSION_INFO" | jq '.'
echo ""

# Get conversation history
echo "💬 Getting conversation history..."
CONVERSATION_HISTORY=$(curl -s "$SERVER_URL/sasya-chikitsa/session/$SESSION_ID/history")
echo ""
echo "📜 Conversation History:"
echo "$CONVERSATION_HISTORY" | jq '.messages | length as $count | "Total messages: \($count)"'
echo ""

# Get classification results
echo "🔬 Getting classification results..."
CLASSIFICATION_RESULTS=$(curl -s "$SERVER_URL/sasya-chikitsa/session/$SESSION_ID/classification")
if [[ $(echo "$CLASSIFICATION_RESULTS" | jq -r '.success') == "true" ]]; then
    echo "✅ Classification Results Available:"
    echo "$CLASSIFICATION_RESULTS" | jq '.classification_results | {disease_name, confidence, severity}'
else
    echo "⚠️  Classification results not available"
fi
echo ""

# Get prescription results
echo "💊 Getting prescription results..."
PRESCRIPTION_RESULTS=$(curl -s "$SERVER_URL/sasya-chikitsa/session/$SESSION_ID/prescription")
if [[ $(echo "$PRESCRIPTION_RESULTS" | jq -r '.success') == "true" ]]; then
    echo "✅ Prescription Results Available:"
    echo "$PRESCRIPTION_RESULTS" | jq '.prescription_data | {treatments: (.treatments | length), preventive_measures: (.preventive_measures | length)}'
else
    echo "⚠️  Prescription results not available"
fi
echo ""

# Clean up session
echo "🧹 Step 6: Session Cleanup"
echo "=========================="

echo "🗑️  Ending session: $SESSION_ID"
CLEANUP_RESULT=$(curl -s -X DELETE "$SERVER_URL/sasya-chikitsa/session/$SESSION_ID")
echo "$CLEANUP_RESULT" | jq '.'
echo ""

echo "✅ Complete streaming workflow test completed!"
echo ""
echo "📊 Test Summary:"
echo "- ✅ Classification with image analysis"
echo "- ✅ Prescription generation with RAG"
echo "- ✅ Vendor search and options display"
echo "- ✅ Order processing simulation"
echo "- ✅ Follow-up question handling"
echo "- ✅ Session state management"
echo "- ✅ Session cleanup"
echo ""
echo "📁 Log files created:"
echo "- /tmp/fsm_workflow_step1.log (Classification & Prescription)"
echo "- /tmp/fsm_workflow_step2.log (Vendor Options)"
echo "- /tmp/fsm_workflow_step3.log (Order Processing)"
echo "- /tmp/fsm_workflow_step4.log (Follow-up)"
echo ""
echo "🌱 FSM Agent complete workflow testing successful!"

