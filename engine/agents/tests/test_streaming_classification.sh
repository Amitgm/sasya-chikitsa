# Test 3: Streaming Classification
echo "🌊 Test 3: Streaming Classification"
echo "----------------------------------"

STREAM_REQUEST=$(jq -n \
    --arg session_id "test-stream-$(date +%s)" \
    --arg message "Analyze this leaf for plant diseases with detailed progress updates" \
    --arg image_b64 "$IMAGE_DATA" \
    --argjson context '{"test_mode": true, "streaming": true}' \
    '{
        session_id: $session_id,
        message: $message,
        image_b64: $image_b64,
        context: $context
    }')

echo "📋 Streaming Request (jq formatted):"
echo "$STREAM_REQUEST" | jq '.'
echo ""

echo "🌊 Streaming Response (first 20 lines):"
#timeout 15s curl -s -X POST \
#    -H "Content-Type: application/json" \
#    -d "$STREAM_REQUEST" \
#    "$BASE_URL/planning/chat-stream" | head -20 || echo "⏱️  Streaming test completed (timeout after 15s)"

curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$STREAM_REQUEST" \
    "$BASE_URL/planning/chat-stream" | head -20 || echo "⏱️  Streaming test completed (timeout after 15s)"

echo ""
echo ""