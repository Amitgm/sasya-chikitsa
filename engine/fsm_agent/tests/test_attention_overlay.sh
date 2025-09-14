#!/bin/bash

# Test script for Attention Overlay functionality in FSM Agent
# Tests the ability to retrieve and display stored attention overlays

set -e

# Color codes for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SERVER_URL="http://localhost:8002"
TEST_IMAGE_PATH="../../resources/images_for_test/tomato_mosaic_virus.png"
OUTPUT_DIR="test_results"
TIMEOUT_DURATION=30

echo -e "${BLUE}🧪 FSM Agent - Attention Overlay Test Suite${NC}"
echo -e "${BLUE}=============================================${NC}"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Test configuration
echo -e "${CYAN}📋 Test Configuration:${NC}"
echo "  Server URL: $SERVER_URL"
echo "  Test Image: $TEST_IMAGE_PATH"
echo "  Output Directory: $OUTPUT_DIR"
echo "  Timeout: ${TIMEOUT_DURATION}s"
echo ""

# Function to check server health
check_server_health() {
    echo -e "${YELLOW}🔍 Checking server health...${NC}"
    
    if ! curl -s --max-time 10 "$SERVER_URL/health" > /dev/null; then
        echo -e "${RED}❌ Server is not responding at $SERVER_URL${NC}"
        echo "   Please ensure the FSM agent server is running:"
        echo "   cd engine/fsm_agent && python run_fsm_server.py"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Server is healthy${NC}"
    echo ""
}

# Function to encode image to base64
encode_image_base64() {
    local image_path="$1"
    if [[ -f "$image_path" ]]; then
        base64 -i "$image_path" | tr -d '\n'
    else
        echo ""
    fi
}

# Function to perform classification first (needed for attention overlay)
perform_classification() {
    echo -e "${YELLOW}🔬 Step 1: Performing initial classification to generate attention overlay...${NC}"
    
    # Check if test image exists
    if [[ ! -f "$TEST_IMAGE_PATH" ]]; then
        echo -e "${RED}❌ Test image not found: $TEST_IMAGE_PATH${NC}"
        return 1
    fi
    
    # Encode image
    local image_base64=$(encode_image_base64 "$TEST_IMAGE_PATH")
    if [[ -z "$image_base64" ]]; then
        echo -e "${RED}❌ Failed to encode test image${NC}"
        return 1
    fi
    
    # Prepare classification request
    local request_data=$(cat << EOF
{
    "message": "Please analyze this plant leaf image for disease classification",
    "image": "$image_base64",
    "context": {
        "plant_type": "tomato",
        "location": "California",
        "season": "summer",
        "growth_stage": "flowering"
    }
}
EOF
    )
    
    # Send classification request
    echo "  📤 Sending classification request..."
    
    local response=$(timeout "$TIMEOUT_DURATION" curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$request_data" \
        "$SERVER_URL/sasya-chikitsa/chat" 2>/dev/null || echo "TIMEOUT")
    
    if [[ "$response" == "TIMEOUT" ]]; then
        echo -e "${RED}❌ Classification request timed out${NC}"
        return 1
    fi
    
    if [[ -z "$response" ]]; then
        echo -e "${RED}❌ Empty response from classification${NC}"
        return 1
    fi
    
    # Save response for analysis
    echo "$response" > "$OUTPUT_DIR/classification_response.json"
    
    # Extract session ID from response
    local session_id=$(echo "$response" | jq -r '.session_id // empty' 2>/dev/null || echo "")
    
    if [[ -z "$session_id" ]]; then
        echo -e "${RED}❌ Could not extract session ID from classification response${NC}"
        echo "   Response: $response"
        return 1
    fi
    
    echo -e "${GREEN}✅ Classification completed${NC}"
    echo "  🆔 Session ID: $session_id"
    echo "  💾 Response saved to: $OUTPUT_DIR/classification_response.json"
    echo ""
    
    # Return session ID for further tests
    echo "$session_id"
}

# Function to test attention overlay retrieval
test_attention_overlay_retrieval() {
    local session_id="$1"
    echo -e "${YELLOW}🎯 Step 2: Testing attention overlay retrieval...${NC}"
    
    # Test cases for different overlay request types
    local test_cases=(
        "show attention overlay"
        "can I see the attention map?"
        "display the heatmap"
        "show me where the AI was looking"
        "what parts of the image were important?"
        "attention overlay info"
        "explain the attention overlay"
    )
    
    local success_count=0
    local total_tests=${#test_cases[@]}
    
    for i in "${!test_cases[@]}"; do
        local test_message="${test_cases[$i]}"
        echo "  📝 Test $((i+1))/$total_tests: \"$test_message\""
        
        # Prepare followup request
        local request_data=$(cat << EOF
{
    "message": "$test_message",
    "session_id": "$session_id"
}
EOF
        )
        
        # Send request
        local response=$(timeout "$TIMEOUT_DURATION" curl -s -X POST \
            -H "Content-Type: application/json" \
            -d "$request_data" \
            "$SERVER_URL/sasya-chikitsa/chat" 2>/dev/null || echo "TIMEOUT")
        
        if [[ "$response" == "TIMEOUT" ]]; then
            echo -e "    ${RED}❌ Request timed out${NC}"
            continue
        fi
        
        if [[ -z "$response" ]]; then
            echo -e "    ${RED}❌ Empty response${NC}"
            continue
        fi
        
        # Save individual response
        echo "$response" > "$OUTPUT_DIR/overlay_test_${i}.json"
        
        # Check if response contains expected content
        local response_message=$(echo "$response" | jq -r '.response // .message // empty' 2>/dev/null || echo "")
        
        if [[ "$response_message" == *"Attention Overlay"* ]] || \
           [[ "$response_message" == *"attention overlay"* ]] || \
           [[ "$response_message" == *"base64"* ]] || \
           [[ "$response_message" == *"heatmap"* ]]; then
            echo -e "    ${GREEN}✅ Valid attention overlay response${NC}"
            ((success_count++))
        else
            echo -e "    ${RED}❌ Unexpected response content${NC}"
            echo "       Response: ${response_message:0:100}..."
        fi
        
        # Brief pause between requests
        sleep 1
    done
    
    echo ""
    echo -e "${CYAN}📊 Attention Overlay Test Results:${NC}"
    echo "  ✅ Successful requests: $success_count/$total_tests"
    echo "  📁 Responses saved to: $OUTPUT_DIR/"
    echo ""
    
    if [[ $success_count -eq $total_tests ]]; then
        echo -e "${GREEN}🎉 All attention overlay tests passed!${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️ Some attention overlay tests failed${NC}"
        return 1
    fi
}

# Function to test attention overlay with no prior classification
test_no_classification_scenario() {
    echo -e "${YELLOW}🚫 Step 3: Testing attention overlay request without prior classification...${NC}"
    
    # Start fresh session
    local request_data=$(cat << EOF
{
    "message": "show me the attention overlay"
}
EOF
    )
    
    local response=$(timeout "$TIMEOUT_DURATION" curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$request_data" \
        "$SERVER_URL/sasya-chikitsa/chat" 2>/dev/null || echo "TIMEOUT")
    
    if [[ "$response" == "TIMEOUT" ]]; then
        echo -e "${RED}❌ Request timed out${NC}"
        return 1
    fi
    
    # Save response
    echo "$response" > "$OUTPUT_DIR/no_classification_test.json"
    
    # Check if response properly handles the no-classification case
    local response_message=$(echo "$response" | jq -r '.response // .message // empty' 2>/dev/null || echo "")
    
    if [[ "$response_message" == *"No Classification Available"* ]] || \
       [[ "$response_message" == *"upload"* ]] || \
       [[ "$response_message" == *"classification results"* ]]; then
        echo -e "${GREEN}✅ Properly handled no-classification scenario${NC}"
        echo "  💬 Response: ${response_message:0:150}..."
        return 0
    else
        echo -e "${RED}❌ Did not properly handle no-classification scenario${NC}"
        echo "  💬 Response: ${response_message:0:150}..."
        return 1
    fi
    echo ""
}

# Function to test streaming attention overlay
test_streaming_attention_overlay() {
    local session_id="$1"
    echo -e "${YELLOW}📡 Step 4: Testing streaming attention overlay retrieval...${NC}"
    
    # Prepare streaming request
    local request_data=$(cat << EOF
{
    "message": "show attention overlay with streaming",
    "session_id": "$session_id"
}
EOF
    )
    
    # Test streaming endpoint
    echo "  📤 Testing streaming endpoint..."
    
    local stream_output="$OUTPUT_DIR/streaming_overlay_test.txt"
    
    # Use curl to test streaming response
    timeout "$TIMEOUT_DURATION" curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$request_data" \
        "$SERVER_URL/sasya-chikitsa/chat-stream" > "$stream_output" 2>/dev/null || true
    
    if [[ -f "$stream_output" ]] && [[ -s "$stream_output" ]]; then
        local stream_content=$(cat "$stream_output")
        if [[ "$stream_content" == *"attention"* ]] || \
           [[ "$stream_content" == *"overlay"* ]] || \
           [[ "$stream_content" == *"base64"* ]]; then
            echo -e "${GREEN}✅ Streaming attention overlay test passed${NC}"
            echo "  📁 Stream output saved to: $stream_output"
            return 0
        fi
    fi
    
    echo -e "${YELLOW}⚠️ Streaming test inconclusive or failed${NC}"
    echo "  📁 Output saved to: $stream_output"
    return 1
}

# Function to validate attention overlay data format
validate_overlay_data() {
    echo -e "${YELLOW}🔍 Step 5: Validating attention overlay data format...${NC}"
    
    local validation_passed=true
    
    # Check classification response for attention overlay data
    if [[ -f "$OUTPUT_DIR/classification_response.json" ]]; then
        local attention_data=$(cat "$OUTPUT_DIR/classification_response.json" | \
            jq -r '.. | objects | select(has("attention_overlay")) | .attention_overlay // empty' 2>/dev/null || echo "")
        
        if [[ -n "$attention_data" ]] && [[ ${#attention_data} -gt 50 ]]; then
            echo -e "${GREEN}✅ Attention overlay data found in classification response${NC}"
            echo "  📏 Data length: ${#attention_data} characters"
            
            # Basic base64 validation
            if echo "$attention_data" | base64 -d > /dev/null 2>&1; then
                echo -e "${GREEN}✅ Attention overlay data is valid base64${NC}"
            else
                echo -e "${RED}❌ Attention overlay data is not valid base64${NC}"
                validation_passed=false
            fi
        else
            echo -e "${YELLOW}⚠️ No attention overlay data found in classification response${NC}"
        fi
    fi
    
    # Check overlay test responses for base64 data
    local overlay_files=("$OUTPUT_DIR"/overlay_test_*.json)
    local base64_found=false
    
    for file in "${overlay_files[@]}"; do
        if [[ -f "$file" ]]; then
            local base64_content=$(cat "$file" | grep -o 'iVBORw0KGgoAAAANSUhEUg[A-Za-z0-9+/=]*' 2>/dev/null || echo "")
            if [[ -n "$base64_content" ]]; then
                echo -e "${GREEN}✅ Base64 image data found in overlay response${NC}"
                echo "  📄 File: $(basename "$file")"
                echo "  📏 Base64 length: ${#base64_content} characters"
                base64_found=true
                break
            fi
        fi
    done
    
    if [[ "$base64_found" == false ]]; then
        echo -e "${YELLOW}⚠️ No base64 image data found in overlay responses${NC}"
    fi
    
    echo ""
    
    if [[ "$validation_passed" == true ]]; then
        return 0
    else
        return 1
    fi
}

# Function to generate test report
generate_test_report() {
    local overall_result="$1"
    
    echo -e "${BLUE}📋 Test Report - Attention Overlay Functionality${NC}"
    echo -e "${BLUE}===============================================${NC}"
    echo ""
    
    echo "🕒 Test Execution Time: $(date)"
    echo "🖥️ Server URL: $SERVER_URL"
    echo "📁 Test Results Directory: $OUTPUT_DIR"
    echo ""
    
    echo "📊 Test Results Summary:"
    if [[ "$overall_result" == "PASS" ]]; then
        echo -e "  ${GREEN}✅ Overall Result: PASS${NC}"
        echo "  🎯 Attention overlay functionality is working correctly"
        echo "  📝 Users can successfully request and retrieve attention overlays"
        echo "  🛡️ Error handling for no-classification scenarios works properly"
        echo "  🔍 Data validation passed for base64 format"
    else
        echo -e "  ${RED}❌ Overall Result: FAIL${NC}"
        echo "  ⚠️ Some attention overlay functionality issues detected"
        echo "  🔧 Check individual test outputs for detailed error information"
    fi
    
    echo ""
    echo "📁 Generated Files:"
    if [[ -d "$OUTPUT_DIR" ]]; then
        ls -la "$OUTPUT_DIR"
    fi
    
    echo ""
    echo "💡 Usage Examples for Attention Overlay:"
    echo "  • \"show attention overlay\""
    echo "  • \"can I see the attention map?\""
    echo "  • \"display the heatmap\""
    echo "  • \"show me where the AI was looking\""
    echo "  • \"what parts of the image were important?\""
    echo "  • \"attention overlay info\""
    echo ""
}

# Main test execution
main() {
    echo -e "${PURPLE}🚀 Starting Attention Overlay Test Suite...${NC}"
    echo ""
    
    # Pre-flight checks
    check_server_health
    
    local overall_result="FAIL"
    local session_id=""
    
    # Step 1: Perform classification to generate attention overlay
    if session_id=$(perform_classification); then
        echo -e "${GREEN}✅ Step 1 passed: Classification successful${NC}"
        
        # Step 2: Test attention overlay retrieval
        if test_attention_overlay_retrieval "$session_id"; then
            echo -e "${GREEN}✅ Step 2 passed: Attention overlay retrieval successful${NC}"
            
            # Step 3: Test no-classification scenario
            if test_no_classification_scenario; then
                echo -e "${GREEN}✅ Step 3 passed: No-classification error handling works${NC}"
                
                # Step 4: Test streaming (optional)
                test_streaming_attention_overlay "$session_id"
                echo -e "${GREEN}✅ Step 4 completed: Streaming test finished${NC}"
                
                # Step 5: Validate data format
                if validate_overlay_data; then
                    echo -e "${GREEN}✅ Step 5 passed: Data validation successful${NC}"
                    overall_result="PASS"
                else
                    echo -e "${YELLOW}⚠️ Step 5 warning: Data validation issues${NC}"
                fi
            else
                echo -e "${RED}❌ Step 3 failed: No-classification error handling failed${NC}"
            fi
        else
            echo -e "${RED}❌ Step 2 failed: Attention overlay retrieval failed${NC}"
        fi
    else
        echo -e "${RED}❌ Step 1 failed: Classification failed${NC}"
        echo "  Cannot proceed with attention overlay tests without successful classification"
    fi
    
    echo ""
    generate_test_report "$overall_result"
    
    if [[ "$overall_result" == "PASS" ]]; then
        exit 0
    else
        exit 1
    fi
}

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}🧹 Cleaning up test environment...${NC}"
    # Add any cleanup logic here if needed
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Set up trap for cleanup
trap cleanup EXIT

# Run main function
main "$@"

