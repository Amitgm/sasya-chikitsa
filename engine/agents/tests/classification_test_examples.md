# 🧪 Planning Agent Classification Test Examples

## 📋 **Individual jq Requests and curl Commands**

### **1. Health Check**

**jq Command (optional - for pretty output):**
```bash
curl -s "http://localhost:8001/health" | jq '.'
```

**Simple curl:**
```bash
curl -X GET "http://localhost:8001/health"
```

---

### **2. Basic Classification Request**

**jq Request Builder:**
```bash
# Set your test image (base64 encoded)
IMAGE_DATA="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

# Create JSON request with jq
CLASSIFICATION_REQUEST=$(jq -n \
    --arg session_id "test-session-$(date +%s)" \
    --arg message "Please analyze this plant leaf image for disease detection. What condition do you see?" \
    --arg image_b64 "$IMAGE_DATA" \
    --argjson context '{"test_mode": true, "crop_type": "tomato", "location": "test"}' \
    '{
        session_id: $session_id,
        message: $message,
        image_b64: $image_b64,
        context: $context,
        workflow_action: null
    }')

# Display the formatted request
echo "$CLASSIFICATION_REQUEST" | jq '.'
```

**curl Command:**
```bash
curl -X POST "http://localhost:8001/planning/chat" \
    -H "Content-Type: application/json" \
    -d "$CLASSIFICATION_REQUEST" | jq '.'
```

---

### **3. Streaming Classification Request**

**jq Request Builder:**
```bash
# Create streaming request with jq
STREAM_REQUEST=$(jq -n \
    --arg session_id "stream-test-$(date +%s)" \
    --arg message "Analyze this leaf for plant diseases with detailed progress updates" \
    --arg image_b64 "$IMAGE_DATA" \
    --argjson context '{"test_mode": true, "streaming": true, "crop_type": "tomato"}' \
    '{
        session_id: $session_id,
        message: $message,
        image_b64: $image_b64,
        context: $context,
        workflow_action: null
    }')

# Display the request
echo "$STREAM_REQUEST" | jq '.'
```

**curl Command for Streaming:**
```bash
curl -X POST "http://localhost:8001/planning/chat-stream" \
    -H "Content-Type: application/json" \
    -d "$STREAM_REQUEST"
```

---

### **4. Text-Only Classification Request** 

**jq Request Builder:**
```bash
# Text-only request (no image)
TEXT_REQUEST=$(jq -n \
    --arg session_id "text-test-$(date +%s)" \
    --arg message "My tomato plant leaves have brown spots with yellow halos. What disease could this be?" \
    --argjson context '{"crop_type": "tomato", "symptoms": "brown spots, yellow halos", "season": "summer"}' \
    '{
        session_id: $session_id,
        message: $message,
        image_b64: null,
        context: $context,
        workflow_action: null
    }')

echo "$TEXT_REQUEST" | jq '.'
```

**curl Command:**
```bash
curl -X POST "http://localhost:8001/planning/chat" \
    -H "Content-Type: application/json" \
    -d "$TEXT_REQUEST" | jq '.'
```

---

### **5. Session Management**

**Get Session Information:**
```bash
# Replace with actual session ID from previous requests
SESSION_ID="test-session-1694123456"

curl -X GET "http://localhost:8001/planning/session/$SESSION_ID" | jq '.'
```

**Get Available Actions:**
```bash
curl -X GET "http://localhost:8001/planning/session/$SESSION_ID/actions" | jq '.'
```

**Restart Session:**
```bash
curl -X POST "http://localhost:8001/planning/session/$SESSION_ID/restart" | jq '.'
```

---

### **6. Complete Classification Test with Real Image**

**Step 1: Load Real Image Data**
```bash
# Load base64 image from test files
if [[ -f "../../../engine/resources/images_for_test/leaf_base64.txt" ]]; then
    IMAGE_DATA=$(head -c 5000 "../../../engine/resources/images_for_test/leaf_base64.txt")
elif [[ -f "/Users/aathalye/dev/sasya-chikitsa/resources/images_for_test/image_103_base64.txt" ]]; then
    IMAGE_DATA=$(head -c 5000 "/Users/aathalye/dev/sasya-chikitsa/resources/images_for_test/image_103_base64.txt")
else
    # Fallback: 1x1 pixel test image
    IMAGE_DATA="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
fi

echo "📸 Using image data (first 100 chars): ${IMAGE_DATA:0:100}..."
```

**Step 2: Create and Send Request**
```bash
# Create complete classification request
FULL_REQUEST=$(jq -n \
    --arg session_id "full-test-$(date +%s)" \
    --arg message "Please perform a complete disease analysis of this plant leaf. I need diagnosis, treatment recommendations, and vendor suggestions." \
    --arg image_b64 "$IMAGE_DATA" \
    --argjson context '{
        "test_mode": true,
        "crop_type": "tomato",
        "location": "California, USA",
        "season": "summer",
        "growth_stage": "vegetative",
        "previous_treatments": [],
        "organic_preferred": true
    }' \
    '{
        session_id: $session_id,
        message: $message,
        image_b64: $image_b64,
        context: $context,
        workflow_action: null
    }')

# Send request and save response
echo "🚀 Sending full classification request..."
RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$FULL_REQUEST" \
    "http://localhost:8001/planning/chat")

# Display formatted response
echo "📊 Classification Response:"
echo "$RESPONSE" | jq '.'

# Extract session ID for follow-up
SESSION_ID=$(echo "$RESPONSE" | jq -r '.session_id // "default"')
echo "📋 Session ID: $SESSION_ID"
```

---

### **7. Error Handling Test**

**Invalid Request Test:**
```bash
# Test with malformed JSON
INVALID_REQUEST='{"session_id": "test", "message": "test", "invalid_field": "should_error"}'

curl -X POST "http://localhost:8001/planning/chat" \
    -H "Content-Type: application/json" \
    -d "$INVALID_REQUEST" | jq '.'
```

**Empty Request Test:**
```bash
# Test with minimal request
MINIMAL_REQUEST=$(jq -n '{
    "session_id": "minimal-test",
    "message": "",
    "image_b64": null,
    "context": {}
}')

curl -X POST "http://localhost:8001/planning/chat" \
    -H "Content-Type: application/json" \
    -d "$MINIMAL_REQUEST" | jq '.'
```

---

## 🔧 **Usage Examples**

### **Quick Test:**
```bash
# 1. Start the server
cd /Users/aathalye/dev/sasya-chikitsa/engine/agents
./run_planning_server.sh

# 2. In another terminal, run quick test
cd /Users/aathalye/dev/sasya-chikitsa
./test_classification.sh
```

### **Manual Testing:**
```bash
# 1. Set variables
SERVER_URL="http://localhost:8001"
SESSION_ID="manual-test-$(date +%s)"

# 2. Create request with jq
REQUEST=$(jq -n \
    --arg session_id "$SESSION_ID" \
    --arg message "Test classification" \
    '{ session_id: $session_id, message: $message, image_b64: null, context: {} }')

# 3. Send request
curl -X POST "$SERVER_URL/planning/chat" \
    -H "Content-Type: application/json" \
    -d "$REQUEST" | jq '.'
```

### **Debug Mode:**
```bash
# Enable verbose curl output for debugging
curl -v -X POST "http://localhost:8001/planning/chat" \
    -H "Content-Type: application/json" \
    -d "$REQUEST" | jq '.'
```

---

## 📊 **Expected Response Format**

**Successful Response:**
```json
{
  "success": true,
  "response": "Based on the image analysis...",
  "current_state": "classification",
  "next_actions": ["get_prescription", "get_vendors"],
  "requires_user_input": false,
  "error_message": null,
  "timestamp": 1694123456.789
}
```

**Error Response:**
```json
{
  "detail": "Processing error: description of what went wrong"
}
```

**Streaming Response:**
```
data: 🚀 Starting analysis...

data: 📸 Processing uploaded image...

data: 🔍 Analyzing plant condition...

data: 🧠 Extracting features and context...

data: Your plant shows signs of early blight disease...

data: [DONE]
```

---

## 🎯 **Testing Checklist**

- [ ] Server health check passes
- [ ] Basic classification with text only
- [ ] Classification with base64 image
- [ ] Streaming response works
- [ ] Session creation and tracking
- [ ] Error handling for invalid requests
- [ ] Response format validation
- [ ] Performance under load

---

**🌱 Ready to test plant disease classification with the Planning Agent!** ✨
