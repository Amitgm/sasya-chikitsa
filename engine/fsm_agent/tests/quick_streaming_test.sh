#!/bin/bash

# Quick FSM Agent Streaming Test
# A simplified version for quick validation of streaming capabilities

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SERVER_URL="http://localhost:8080"

echo -e "${BLUE}🚀 Quick FSM Agent Streaming Test${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""

# Check server
echo -e "${YELLOW}📡 Checking server...${NC}"
if ! curl -s "$SERVER_URL/health" > /dev/null; then
    echo -e "${RED}❌ Server not running. Start with:${NC}"
    echo "   cd engine/fsm_agent"
    echo "   OLLAMA_HOST=http://127.0.0.1:11434 python run_fsm_server.py"
    exit 1
fi
echo -e "${GREEN}✅ Server running${NC}"

# Image file paths (checking multiple locations for real plant disease images)
IMAGE_PATHS=(
    "/Users/aathalye/dev/sasya-chikitsa/resources/images_for_test/tomato_mosaic_virus_base64.txt"
    "/Users/aathalye/dev/sasya-chikitsa/engine/resources/images_for_test/tomato_mosaic_virus_base64.txt"
    "/Users/aathalye/dev/sasya-chikitsa/resources/images_for_test/generated_image_base64.txt"
    "/Users/aathalye/dev/sasya-chikitsa/engine/images/image_103_base64.txt"
    "/Users/aathalye/dev/sasya-chikitsa/engine/resources/images_for_test/leaf_base64.txt"
)

# Find and load real image data
echo -e "${YELLOW}📸 Loading plant disease image data...${NC}"

IMAGE_DATA=""
IMAGE_SOURCE=""

# Try each image path
for image_path in "${IMAGE_PATHS[@]}"; do
    if [[ -f "$image_path" ]] && [[ -s "$image_path" ]]; then
        IMAGE_DATA=$(cat "$image_path" | tr -d '\n\r')  # Limit to 100KB
        IMAGE_SOURCE="$image_path"
        echo -e "${GREEN}✅ Loaded image from: $IMAGE_SOURCE${NC}"
        break
    fi
done

# Fallback to sample image if no real images found
if [[ -z "$IMAGE_DATA" ]]; then
    # Sample base64 image (small tomato leaf sample)
    IMAGE_DATA="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    IMAGE_SOURCE="Sample PNG (fallback)"
    echo -e "${YELLOW}⚠️ No real image files found, using fallback sample image${NC}"
fi

echo "📊 Image data size: ${#IMAGE_DATA} characters"
echo "📋 Source: $IMAGE_SOURCE"
echo "📋 First 50 characters: ${IMAGE_DATA:0:50}..."

# Create request
SESSION_ID="quick-test-$(date +%s)"
REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID" \
    --arg message "Analyze this tomato plant leaf for disease. No need to elaborate on that" \
    --arg image "$IMAGE_DATA" \
    '{
        message: $message,
        image_b64: $image,
        context: {
            plant_type: "tomato",
            location: "Andhra Pradesh",
            season: "summer"
        },
        session_id: $session_id
    }')

echo ""
echo -e "${YELLOW}🌊 Starting streaming test...${NC}"
echo -e "${BLUE}Session ID: $SESSION_ID${NC}"
echo ""

# Send streaming request
curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$REQUEST" \
    "$SERVER_URL/sasya-chikitsa/chat-stream" | while IFS= read -r line; do
    
    # Show key transitions and results
    if [[ "$line" == *"INITIAL"* ]] || [[ "$line" == *"CLASSIFYING"* ]] || [[ "$line" == *"PRESCRIBING"* ]]; then
        echo -e "${BLUE}🔄 $line${NC}"
    elif [[ "$line" == *"diagnosis"* ]] || [[ "$line" == *"confidence"* ]]; then
        echo -e "${GREEN}📊 $line${NC}"
    elif [[ "$line" == *"treatment"* ]] || [[ "$line" == *"prescription"* ]]; then
        echo -e "${YELLOW}💊 $line${NC}"
    elif [[ "$line" == *"COMPLETED"* ]] || [[ "$line" == *"[DONE]"* ]]; then
        echo -e "${GREEN}✅ $line${NC}"
    else
        echo "$line"
    fi
done

echo ""
echo -e "${GREEN}🎉 Quick streaming test completed!${NC}"

# Test attention overlay
#echo ""
#echo -e "${YELLOW}🎯 Testing attention overlay request...${NC}"
#
#OVERLAY_REQUEST=$(jq -n \
#    --arg session_id "$SESSION_ID" \
#    --arg message "Show me the attention overlay" \
#    '{
#        message: $message,
#        session_id: $session_id
#    }')
#
#curl -s -X POST \
#    -H "Content-Type: application/json" \
#    -d "$OVERLAY_REQUEST" \
#    "$SERVER_URL/sasya-chikitsa/chat-stream" | head -3

echo ""
echo -e "${GREEN}✅ Test completed successfully!${NC}"
echo ""
echo -e "${BLUE}📊 Test Summary:${NC}"
echo "Session ID: $SESSION_ID"
echo "Image Source: $IMAGE_SOURCE"
echo "Image Size: ${#IMAGE_DATA} characters"
echo "Server: $SERVER_URL"
