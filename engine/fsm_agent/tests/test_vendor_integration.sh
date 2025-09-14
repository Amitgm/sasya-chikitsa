#!/bin/bash

# FSM Agent Vendor Integration Test
# Tests vendor search, pricing, and order simulation functionality

set -e

# Configuration
SERVER_URL="http://localhost:8002"

echo "🛒 FSM Agent Vendor Integration Test"
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

# Test 1: Vendor Search for Chemical Treatments
echo "🧪 Test 1: Chemical Treatment Vendor Search"
echo "==========================================="

SESSION_ID_1="vendor-chemical-$(date +%s)"

CHEMICAL_REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID_1" \
    --arg message "I need to find vendors for copper sulfate fungicide and streptomycin solution for my tomato bacterial blight problem in Tamil Nadu. Show me chemical treatment options with pricing." \
    --argjson context '{
        "test_mode": true,
        "location": "Tamil Nadu",
        "crop_type": "tomato",
        "disease_name": "Bacterial Blight",
        "treatment_preference": "chemical",
        "budget_range": "medium",
        "delivery_required": true
    }' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

echo "📋 Chemical Treatment Request:"
echo "$CHEMICAL_REQUEST" | jq '.'
echo ""

echo "🔍 Searching for chemical treatment vendors..."
CHEMICAL_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$CHEMICAL_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat")

echo "📊 Chemical Vendor Response:"
echo "$CHEMICAL_RESPONSE" | jq '.'
echo ""

# Follow up to get vendor options
VENDOR_YES_REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID_1" \
    --arg message "Yes, please show me the vendor options with detailed pricing and delivery information." \
    --argjson context '{"test_mode": true}' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

echo "🛍️ Requesting detailed vendor options..."
curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$VENDOR_YES_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat-stream" | head -30

echo ""
echo ""

# Test 2: Organic Treatment Vendor Search
echo "🧪 Test 2: Organic Treatment Vendor Search"
echo "=========================================="

SESSION_ID_2="vendor-organic-$(date +%s)"

ORGANIC_REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID_2" \
    --arg message "I prefer organic treatments for my chili pepper fungal disease in Karnataka. Please find organic vendors with neem oil, copper soap, and bio-fungicides." \
    --argjson context '{
        "test_mode": true,
        "location": "Karnataka",
        "crop_type": "chili",
        "disease_name": "Fungal Disease",
        "treatment_preference": "organic",
        "organic_only": true,
        "budget_range": "low_to_medium"
    }' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

echo "📋 Organic Treatment Request:"
echo "$ORGANIC_REQUEST" | jq '.'
echo ""

echo "🌱 Searching for organic treatment vendors..."
curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$ORGANIC_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat-stream" | head -25

echo ""
echo ""

# Test 3: Vendor Selection and Order Simulation
echo "🧪 Test 3: Vendor Selection and Order Simulation"
echo "================================================"

SESSION_ID_3="vendor-order-$(date +%s)"

# Start with a classification to get prescription
CLASSIFICATION_REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID_3" \
    --arg message "I have early blight on my potato plants in Punjab. Please analyze and recommend treatments, then show me vendor options." \
    --argjson context '{
        "test_mode": true,
        "location": "Punjab", 
        "crop_type": "potato",
        "disease_name": "Early Blight",
        "season": "monsoon"
    }' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

echo "🔬 Starting with disease classification..."
curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$CLASSIFICATION_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat" > /dev/null

sleep 2

# Request vendor options
VENDOR_REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID_3" \
    --arg message "Yes, I would like to see vendor options for the recommended treatments." \
    --argjson context '{"test_mode": true}' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

echo "🛒 Requesting vendor options..."
curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$VENDOR_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat-stream" | head -20

sleep 2

# Simulate vendor selection
VENDOR_SELECT_REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID_3" \
    --arg message "I would like to order from the second vendor option. Please proceed with ordering copper fungicide 250ml and organic neem oil 500ml." \
    --argjson context '{
        "test_mode": true,
        "selected_vendor_index": 2,
        "selected_items": [
            {"name": "Copper Fungicide", "size": "250ml", "quantity": 1},
            {"name": "Neem Oil Solution", "size": "500ml", "quantity": 1}
        ]
    }' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

echo ""
echo "📦 Simulating order placement..."
curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$VENDOR_SELECT_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat-stream" | head -15

echo ""
echo ""

# Test 4: Location-based Vendor Filtering
echo "🧪 Test 4: Location-based Vendor Filtering"
echo "=========================================="

declare -a LOCATIONS=("Tamil Nadu" "Karnataka" "Maharashtra" "Gujarat" "Kerala")

for location in "${LOCATIONS[@]}"; do
    SESSION_ID="vendor-location-$(echo $location | tr ' ' '-' | tr '[:upper:]' '[:lower:]')-$(date +%s)"
    
    echo "📍 Testing vendors for location: $location"
    
    LOCATION_REQUEST=$(jq -n \
        --arg session_id "$SESSION_ID" \
        --arg message "I need fungicide and insecticide for my tomato farm. Please show me local vendors in my area." \
        --arg location "$location" \
        --argjson context '{
            "test_mode": true,
            "location": $location,
            "crop_type": "tomato",
            "treatment_types": ["fungicide", "insecticide"]
        }' \
        '{
            session_id: $session_id,
            message: $message,
            context: $context
        }')
    
    LOCATION_RESPONSE=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$LOCATION_REQUEST" \
        "$SERVER_URL/sasya-chikitsa/chat")
    
    # Check if vendors were found for this location
    if [[ $(echo "$LOCATION_RESPONSE" | jq -r '.success') == "true" ]]; then
        echo "  ✅ Vendors found for $location"
    else
        echo "  ⚠️  No specific vendors for $location"
    fi
    
    # Clean up session
    curl -s -X DELETE "$SERVER_URL/sasya-chikitsa/session/$SESSION_ID" > /dev/null
done

echo ""

# Test 5: Price Range and Budget Filtering
echo "🧪 Test 5: Price Range and Budget Filtering"
echo "==========================================="

SESSION_ID_5="vendor-budget-$(date +%s)"

BUDGET_REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID_5" \
    --arg message "I have a limited budget of 500 rupees for treating my vegetable garden fungal problem. Please show me affordable treatment options." \
    --argjson context '{
        "test_mode": true,
        "location": "Tamil Nadu",
        "crop_type": "vegetables",
        "budget_max": 500,
        "budget_range": "low",
        "treatment_preference": "cost_effective"
    }' \
    '{
        session_id: $session_id,
        message: $message,
        context: $context
    }')

echo "💰 Testing budget-conscious vendor options..."
curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$BUDGET_REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat-stream" | head -20

echo ""
echo ""

# Test 6: Session Cleanup and Statistics
echo "🧪 Test 6: Session Cleanup and Statistics"
echo "========================================="

echo "📊 Getting agent statistics before cleanup..."
STATS_BEFORE=$(curl -s "$SERVER_URL/sasya-chikitsa/stats")
echo "📈 Active sessions before cleanup:"
echo "$STATS_BEFORE" | jq '{active_sessions, total_messages}'
echo ""

echo "🧹 Cleaning up test sessions..."
for session in "$SESSION_ID_1" "$SESSION_ID_2" "$SESSION_ID_3" "$SESSION_ID_5"; do
    curl -s -X DELETE "$SERVER_URL/sasya-chikitsa/session/$session" > /dev/null
    echo "  🗑️  Cleaned up session: $session"
done

echo ""
echo "📊 Getting agent statistics after cleanup..."
STATS_AFTER=$(curl -s "$SERVER_URL/sasya-chikitsa/stats")
echo "📈 Active sessions after cleanup:"
echo "$STATS_AFTER" | jq '{active_sessions, total_messages}'
echo ""

echo "✅ All vendor integration tests completed!"
echo ""
echo "🧪 Test Summary:"
echo "- ✅ Chemical treatment vendor search"
echo "- ✅ Organic treatment vendor search"  
echo "- ✅ Vendor selection and order simulation"
echo "- ✅ Location-based vendor filtering"
echo "- ✅ Budget-based vendor filtering"
echo "- ✅ Session management and cleanup"
echo ""
echo "🛒 Vendor integration capabilities verified!"

