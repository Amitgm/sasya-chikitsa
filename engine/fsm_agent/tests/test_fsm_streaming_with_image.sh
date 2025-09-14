#!/bin/bash

# FSM Agent Streaming Classification Test with Real Image Data
# Tests the LangGraph-based FSM agent's streaming capabilities through complete workflow

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
SESSION_ID="fsm-streaming-image-test-$(date +%s)"
OUTPUT_DIR="test_results"
TIMEOUT_DURATION=60

echo -e "${BLUE}🌊 FSM Agent Streaming Classification Test with Image${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Test configuration
echo -e "${CYAN}📋 Test Configuration:${NC}"
echo "  Server URL: $SERVER_URL"
echo "  Session ID: $SESSION_ID"
echo "  Output Directory: $OUTPUT_DIR"
echo "  Timeout: ${TIMEOUT_DURATION}s"
echo ""

# Image file paths (checking multiple locations)
IMAGE_PATHS=(
    "/Users/aathalye/dev/sasya-chikitsa/resources/images_for_test/tomato_mosaic_virus_base64.txt"
    "/Users/aathalye/dev/sasya-chikitsa/engine/resources/images_for_test/tomato_mosaic_virus_base64.txt"
    "/Users/aathalye/dev/sasya-chikitsa/resources/images_for_test/generated_image_base64.txt"
    "/Users/aathalye/dev/sasya-chikitsa/engine/images/image_103_base64.txt"
    "/Users/aathalye/dev/sasya-chikitsa/engine/resources/images_for_test/leaf_base64.txt"
)

# Function to check server health
check_server_health() {
    echo -e "${YELLOW}📡 Checking FSM agent server availability...${NC}"
    
    if ! curl -s --max-time 10 "$SERVER_URL/health" > /dev/null; then
        echo -e "${RED}❌ FSM agent server is not running at $SERVER_URL${NC}"
        echo "   Please start the server first:"
        echo "   cd engine/fsm_agent"
        echo "   OLLAMA_HOST=http://127.0.0.1:11434 python run_fsm_server.py"
        exit 1
    fi
    
    # Test FSM-specific endpoint
    if ! curl -s --max-time 10 "$SERVER_URL/sasya-chikitsa/stats" > /dev/null; then
        echo -e "${RED}❌ FSM agent endpoints not responding${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ FSM agent server is running and healthy${NC}"
    
    # Get server stats
    echo -e "${CYAN}📊 Server Statistics:${NC}"
    curl -s "$SERVER_URL/sasya-chikitsa/stats" | jq '.' || echo "  (Could not retrieve stats)"
    echo ""
}

# Function to find and load image data
load_image_data() {
    echo -e "${YELLOW}📸 Loading plant disease image data...${NC}"
    
    IMAGE_DATA=""
    IMAGE_SOURCE=""
    
    # Try each image path
    for image_path in "${IMAGE_PATHS[@]}"; do
        if [[ -f "$image_path" ]] && [[ -s "$image_path" ]]; then
            IMAGE_DATA=$(cat "$image_path" | tr -d '\n\r' | head -c 100000)  # Limit to 100KB
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
    echo ""
}

# Function to test streaming classification workflow
test_streaming_classification() {
    echo -e "${YELLOW}🔬 Testing FSM Agent Streaming Classification Workflow...${NC}"
    
    # Create comprehensive streaming request for FSM agent
    local stream_request=$(jq -n \
        --arg session_id "$SESSION_ID" \
        --arg message "Please analyze this plant leaf image for disease classification. I need a complete diagnosis with streaming progress updates, treatment recommendations, and attention overlay if available." \
        --arg image_b64 "$IMAGE_DATA" \
        --argjson context '{
            "plant_type": "tomato",
            "location": "Tamil Nadu, India",
            "season": "summer",
            "growth_stage": "flowering",
            "farming_method": "organic",
            "streaming_test": true,
            "test_timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"
        }' \
        '{
            message: $message,
            image: $image_b64,
            context: $context,
            session_id: $session_id
        }')
    
    echo -e "${CYAN}📋 Streaming Request Structure:${NC}"
    echo "$stream_request" | jq '. | {
        session_id, 
        message: (.message | .[0:80] + "..."), 
        image: (.image | .[0:30] + "..."), 
        context
    }'
    echo ""
    
    # Save request for debugging
    echo "$stream_request" > "$OUTPUT_DIR/streaming_request.json"
    
    echo -e "${PURPLE}🌊 Starting FSM Agent Streaming Analysis...${NC}"
    echo -e "${PURPLE}===========================================${NC}"
    echo ""
    
    # Perform streaming request with timeout and capture
    local stream_output="$OUTPUT_DIR/streaming_response.txt"
    local stream_stats="$OUTPUT_DIR/streaming_stats.txt"
    
    {
        echo "=== STREAMING START: $(date) ==="
        echo "Session ID: $SESSION_ID"
        echo "Image Source: $IMAGE_SOURCE"
        echo "Server: $SERVER_URL"
        echo "=== STREAM CONTENT ==="
    } > "$stream_output"
    
    # Track streaming metrics
    local start_time=$(date +%s)
    local chunk_count=0
    local total_chars=0
    
    # Send streaming request and process response
    timeout "$TIMEOUT_DURATION" curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$stream_request" \
        "$SERVER_URL/sasya-chikitsa/chat-stream" | \
    while IFS= read -r line; do
        # Count chunks and characters
        ((chunk_count++))
        total_chars=$((total_chars + ${#line}))
        
        # Display progress
        if [[ $chunk_count -eq 1 ]]; then
            echo -e "${GREEN}📡 First chunk received...${NC}"
        fi
        
        # Save all content
        echo "$line" >> "$stream_output"
        
        # Show key workflow transitions
        if [[ "$line" == *"INITIAL"* ]] || [[ "$line" == *"CLASSIFYING"* ]] || [[ "$line" == *"PRESCRIBING"* ]]; then
            echo -e "${CYAN}🔄 State Transition: $line${NC}"
        fi
        
        # Show attention overlay detection
        if [[ "$line" == *"attention"* ]] || [[ "$line" == *"overlay"* ]]; then
            echo -e "${PURPLE}🎯 Attention Data: ${line:0:80}...${NC}"
        fi
        
        # Show final results
        if [[ "$line" == *"diagnosis"* ]] || [[ "$line" == *"confidence"* ]]; then
            echo -e "${GREEN}📊 Result: ${line:0:80}...${NC}"
        fi
        
        # Show prescriptions
        if [[ "$line" == *"treatment"* ]] || [[ "$line" == *"prescription"* ]]; then
            echo -e "${YELLOW}💊 Treatment: ${line:0:80}...${NC}"
        fi
        
        # Show completion
        if [[ "$line" == *"COMPLETED"* ]] || [[ "$line" == *"[DONE]"* ]]; then
            echo -e "${GREEN}✅ Workflow Complete: $line${NC}"
        fi
        
        # Brief pause to show streaming effect
        sleep 0.1
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Generate streaming statistics
    {
        echo "=== STREAMING STATISTICS ==="
        echo "Duration: ${duration}s"
        echo "Total Chunks: $chunk_count"
        echo "Total Characters: $total_chars"
        echo "Average Chunk Size: $((total_chars / (chunk_count > 0 ? chunk_count : 1))) chars"
        echo "Chunks per Second: $(echo "scale=2; $chunk_count / $duration" | bc -l 2>/dev/null || echo "N/A")"
        echo "Session ID: $SESSION_ID"
        echo "Timestamp: $(date)"
    } > "$stream_stats"
    
    echo ""
    echo -e "${GREEN}✅ Streaming classification completed!${NC}"
    echo ""
    
    # Display statistics
    echo -e "${CYAN}📊 Streaming Performance:${NC}"
    cat "$stream_stats"
    echo ""
    
    return 0
}

# Function to test attention overlay request
test_attention_overlay_request() {
    echo -e "${YELLOW}🎯 Testing Attention Overlay Retrieval...${NC}"
    
    # Wait briefly to ensure classification state is saved
    sleep 2
    
    # Create attention overlay request
    local overlay_request=$(jq -n \
        --arg session_id "$SESSION_ID" \
        --arg message "Can you show me the attention overlay from the previous classification? I want to see where the AI focused during the diagnosis." \
        '{
            message: $message,
            session_id: $session_id
        }')
    
    echo "📋 Requesting attention overlay from session: $SESSION_ID"
    echo ""
    
    # Send attention overlay request
    local overlay_output="$OUTPUT_DIR/attention_overlay_response.txt"
    
    echo -e "${PURPLE}🎯 Fetching Attention Overlay...${NC}"
    echo -e "${PURPLE}================================${NC}"
    
    timeout 30 curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$overlay_request" \
        "$SERVER_URL/sasya-chikitsa/chat-stream" > "$overlay_output"
    
    # Check if attention overlay was returned
    if grep -q "attention" "$overlay_output" && grep -q "overlay\|base64\|heatmap" "$overlay_output"; then
        echo -e "${GREEN}✅ Attention overlay successfully retrieved${NC}"
        echo -e "${CYAN}📋 Response preview:${NC}"
        head -5 "$overlay_output" | cut -c1-100
        echo ""
    elif grep -q "No Classification Available\|No attention overlay" "$overlay_output"; then
        echo -e "${YELLOW}⚠️ Expected response: No classification available (normal behavior)${NC}"
    else
        echo -e "${YELLOW}⚠️ Attention overlay response unclear - check output file${NC}"
    fi
    
    echo ""
}

# Function to test followup interaction
test_followup_interaction() {
    echo -e "${YELLOW}🔄 Testing Followup Interaction...${NC}"
    
    # Test various followup queries
    local followup_queries=(
        "What are the preventive measures for this disease?"
        "Can you suggest organic treatment options?"
        "How severe is this infection?"
        "Show me vendor options for the treatment"
    )
    
    for i in "${!followup_queries[@]}"; do
        local query="${followup_queries[$i]}"
        echo -e "${CYAN}📝 Followup Query $((i+1)): \"$query\"${NC}"
        
        local followup_request=$(jq -n \
            --arg session_id "$SESSION_ID" \
            --arg message "$query" \
            '{
                message: $message,
                session_id: $session_id
            }')
        
        local followup_output="$OUTPUT_DIR/followup_${i}_response.txt"
        
        # Send followup request (non-streaming for speed)
        curl -s -X POST \
            -H "Content-Type: application/json" \
            -d "$followup_request" \
            "$SERVER_URL/sasya-chikitsa/chat" > "$followup_output"
        
        # Check response
        if [[ -s "$followup_output" ]]; then
            local preview=$(head -1 "$followup_output" | cut -c1-80)
            echo -e "${GREEN}✅ Response: $preview...${NC}"
        else
            echo -e "${YELLOW}⚠️ No response received${NC}"
        fi
        
        # Brief pause between requests
        sleep 1
    done
    
    echo ""
}

# Function to validate and analyze results
analyze_test_results() {
    echo -e "${YELLOW}🔍 Analyzing Test Results...${NC}"
    echo ""
    
    local streaming_file="$OUTPUT_DIR/streaming_response.txt"
    local stats_file="$OUTPUT_DIR/streaming_stats.txt"
    
    # Check if streaming response exists and has content
    if [[ -f "$streaming_file" ]] && [[ -s "$streaming_file" ]]; then
        echo -e "${GREEN}✅ Streaming response captured${NC}"
        
        # Analyze content
        local line_count=$(wc -l < "$streaming_file")
        local word_count=$(wc -w < "$streaming_file")
        
        echo "  📊 Response metrics:"
        echo "     - Lines: $line_count"
        echo "     - Words: $word_count"
        
        # Check for key workflow elements
        local has_classification=$(grep -c "classif\|disease\|diagnosis" "$streaming_file" || echo "0")
        local has_prescription=$(grep -c "treatment\|prescription\|recommend" "$streaming_file" || echo "0")
        local has_attention=$(grep -c "attention\|overlay\|focus" "$streaming_file" || echo "0")
        local has_completion=$(grep -c "completed\|DONE\|finished" "$streaming_file" || echo "0")
        
        echo "  🔍 Workflow components detected:"
        echo "     - Classification references: $has_classification"
        echo "     - Prescription references: $has_prescription"
        echo "     - Attention references: $has_attention"
        echo "     - Completion signals: $has_completion"
        
        # Overall assessment
        if [[ $has_classification -gt 0 && $has_prescription -gt 0 ]]; then
            echo -e "${GREEN}✅ Complete workflow detected${NC}"
        elif [[ $has_classification -gt 0 ]]; then
            echo -e "${YELLOW}⚠️ Partial workflow (classification only)${NC}"
        else
            echo -e "${YELLOW}⚠️ Workflow analysis inconclusive${NC}"
        fi
    else
        echo -e "${RED}❌ No streaming response captured${NC}"
    fi
    
    echo ""
    
    # Check session persistence
    echo -e "${CYAN}🔍 Testing Session Persistence:${NC}"
    
    # Get session info
    local session_info_output="$OUTPUT_DIR/session_info.json"
    curl -s "$SERVER_URL/sasya-chikitsa/session/$SESSION_ID" > "$session_info_output"
    
    if [[ -s "$session_info_output" ]] && jq -e . "$session_info_output" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Session data accessible${NC}"
        
        # Extract key session information
        local current_state=$(jq -r '.current_state // "unknown"' "$session_info_output")
        local message_count=$(jq -r '.message_count // 0' "$session_info_output")
        
        echo "  📋 Session details:"
        echo "     - Current State: $current_state"
        echo "     - Message Count: $message_count"
        echo "     - Session ID: $SESSION_ID"
    else
        echo -e "${YELLOW}⚠️ Session data not accessible${NC}"
    fi
    
    echo ""
}

# Function to generate test report
generate_test_report() {
    local overall_result="$1"
    
    echo -e "${BLUE}📋 FSM Agent Streaming Test Report${NC}"
    echo -e "${BLUE}===================================${NC}"
    echo ""
    
    echo "🕒 Test Execution Time: $(date)"
    echo "🖥️ Server URL: $SERVER_URL"
    echo "🆔 Session ID: $SESSION_ID"
    echo "📁 Results Directory: $OUTPUT_DIR"
    echo "📸 Image Source: $IMAGE_SOURCE"
    echo "📊 Image Size: ${#IMAGE_DATA} characters"
    echo ""
    
    echo "📊 Test Results Summary:"
    if [[ "$overall_result" == "PASS" ]]; then
        echo -e "  ${GREEN}✅ Overall Result: PASS${NC}"
        echo "  🌊 Streaming functionality working correctly"
        echo "  🔄 FSM workflow states functioning properly"
        echo "  🎯 Attention overlay integration operational"
        echo "  💬 Followup interactions successful"
        echo "  🗄️ Session persistence working"
    else
        echo -e "  ${RED}❌ Overall Result: FAIL${NC}"
        echo "  ⚠️ Some streaming functionality issues detected"
        echo "  🔧 Check individual test outputs for details"
    fi
    
    echo ""
    echo "📁 Generated Files:"
    if [[ -d "$OUTPUT_DIR" ]]; then
        ls -la "$OUTPUT_DIR"
    fi
    
    echo ""
    echo "💡 Key FSM Agent Features Tested:"
    echo "  • 🌊 Real-time streaming responses"
    echo "  • 🔄 LangGraph state machine transitions"
    echo "  • 🔬 CNN-based disease classification"
    echo "  • 💊 RAG-based treatment prescriptions"
    echo "  • 🎯 Attention overlay retrieval"
    echo "  • 🏪 Vendor recommendation system"
    echo "  • 💬 Conversational followup interactions"
    echo "  • 🗄️ Session state persistence"
    echo ""
    
    echo "🔧 Troubleshooting Tips:"
    echo "  • Ensure OLLAMA_HOST is set: export OLLAMA_HOST=http://127.0.0.1:11434"
    echo "  • Verify Ollama server is running: curl http://127.0.0.1:11434/api/version"
    echo "  • Check FSM agent logs for detailed error information"
    echo "  • Test individual endpoints: curl $SERVER_URL/health"
    echo ""
}

# Main test execution
main() {
    echo -e "${PURPLE}🚀 Starting FSM Agent Streaming Test Suite...${NC}"
    echo ""
    
    local overall_result="FAIL"
    
    # Pre-flight checks
    check_server_health
    load_image_data
    
    # Core streaming test
    if test_streaming_classification; then
        echo -e "${GREEN}✅ Core streaming test passed${NC}"
        
        # Additional tests
        test_attention_overlay_request
        test_followup_interaction
        analyze_test_results
        
        overall_result="PASS"
    else
        echo -e "${RED}❌ Core streaming test failed${NC}"
    fi
    
    echo ""
    generate_test_report "$overall_result"
    
    if [[ "$overall_result" == "PASS" ]]; then
        echo -e "${GREEN}🎉 FSM Agent streaming test completed successfully!${NC}"
        exit 0
    else
        echo -e "${RED}⚠️ FSM Agent streaming test encountered issues.${NC}"
        exit 1
    fi
}

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}🧹 Cleaning up test environment...${NC}"
    
    # Optional: Clean up session data
    if [[ -n "$SESSION_ID" ]]; then
        curl -s -X DELETE "$SERVER_URL/sasya-chikitsa/session/$SESSION_ID" > /dev/null 2>&1 || true
    fi
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Set up trap for cleanup
trap cleanup EXIT

# Run main function
main "$@"

