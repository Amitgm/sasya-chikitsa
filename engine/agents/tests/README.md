# 🧪 Planning Agent Testing Suite

This directory contains comprehensive testing tools for the Planning Agent system, specifically focused on plant disease classification functionality.

## 📁 **Test Files**

### **🚀 Executable Scripts**

#### **`test_classification.sh`** - Complete Test Suite
- **Purpose**: Comprehensive testing of all Planning Agent classification features
- **Features**:
  - Health check validation
  - Basic classification with image data
  - Streaming response testing
  - Session management testing
  - Error handling validation
  - Automatic image data loading from test files
- **Usage**: `./test_classification.sh`
- **Requirements**: Server running on `http://localhost:8001`

#### **`quick_classification_test.sh`** - Quick Test
- **Purpose**: Fast, simple classification test with sample data
- **Features**:
  - Single classification request
  - Pretty-printed JSON output
  - Minimal setup required
- **Usage**: `./quick_classification_test.sh`
- **Requirements**: Server running on `http://localhost:8001`

### **📚 Documentation**

#### **`classification_test_examples.md`** - Testing Guide
- **Purpose**: Complete reference guide for manual testing
- **Contents**:
  - Individual jq request examples
  - curl command templates
  - Response format documentation
  - Error handling examples
  - Step-by-step testing procedures
- **Use Case**: Copy-paste commands for custom testing scenarios

#### **`README.md`** - This File
- Overview of the testing suite
- Usage instructions
- File descriptions

---

## 🚀 **Quick Start**

### **1. Start the Planning Agent Server**
```bash
# From the agents directory
cd /Users/aathalye/dev/sasya-chikitsa/engine/agents
./run_planning_server.sh
```

### **2. Run Tests**
```bash
# Full test suite
cd /Users/aathalye/dev/sasya-chikitsa/engine/agents/tests
./test_classification.sh

# OR quick test
./quick_classification_test.sh
```

### **3. Manual Testing**
```bash
# Use examples from the documentation
cat classification_test_examples.md

# Copy and paste specific jq/curl commands
```

---

## 🎯 **Test Coverage**

### **Endpoints Tested**
- ✅ `GET /health` - Server health check
- ✅ `POST /planning/chat` - Basic classification
- ✅ `POST /planning/chat-stream` - Streaming classification
- ✅ `GET /planning/session/{id}` - Session information
- ✅ `GET /planning/session/{id}/actions` - Available actions
- ✅ `POST /planning/session/{id}/restart` - Session restart

### **Test Scenarios**
- ✅ Text-only classification requests
- ✅ Image-based classification (base64 encoded)
- ✅ Streaming response handling
- ✅ Session state management
- ✅ Error handling and edge cases
- ✅ JSON request/response validation
- ✅ Multiple session handling

### **Data Sources**
- Sample base64 test images
- Real plant leaf images (when available)
- Various crop types and symptoms
- Different context parameters

---

## 📊 **Expected Results**

### **Successful Test Output**
```
🧪 Planning Agent Classification Test
=====================================

✅ Server is running
🏥 Test 1: Health Check - PASSED
🔬 Test 2: Basic Classification - PASSED
🌊 Test 3: Streaming Classification - PASSED
📋 Test 4: Session Information - PASSED
🎮 Test 5: Available Actions - PASSED

✅ All classification tests completed!
```

### **Response Format**
```json
{
  "success": true,
  "response": "Based on the analysis...",
  "current_state": "classification",
  "next_actions": ["get_prescription", "get_vendors"],
  "requires_user_input": false,
  "error_message": null,
  "timestamp": 1694123456.789
}
```

---

## 🔧 **Troubleshooting**

### **Server Not Running**
```bash
❌ Server not running at http://localhost:8001
   Start the server first: ./run_planning_server.sh
```

**Solution**: Start the Planning Agent server before running tests.

### **No Test Images Found**
```bash
❌ No base64 image files found!
```

**Solution**: The tests will use fallback sample images, but for full testing, ensure test image files are available.

### **jq Command Not Found**
```bash
bash: jq: command not found
```

**Solution**: Install jq:
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq
```

### **Permission Denied**
```bash
permission denied: ./test_classification.sh
```

**Solution**: Make scripts executable:
```bash
chmod +x *.sh
```

---

## 🛠 **Development**

### **Adding New Tests**
1. Create new test script or modify existing ones
2. Follow the established pattern of jq request building
3. Add proper error handling and validation
4. Update this README with new test descriptions

### **Modifying Test Data**
- Edit the `IMAGE_DATA` variables in scripts
- Modify `context` objects for different scenarios  
- Update session IDs and request parameters as needed

### **Integration with CI/CD**
The test scripts can be integrated into automated testing pipelines:
```bash
# Example CI command
cd engine/agents/tests && ./test_classification.sh
```

---

## 📈 **Performance Testing**

### **Load Testing** (Future Enhancement)
```bash
# Example load test concept
for i in {1..10}; do
  ./quick_classification_test.sh &
done
wait
```

### **Metrics Collection**
- Response times
- Success rates
- Error frequency
- Server resource usage

---

## 🎯 **Summary**

This testing suite provides **comprehensive validation** of the Planning Agent classification system:

- **🧪 Automated Tests** - Full test coverage with minimal manual intervention
- **🚀 Quick Tests** - Fast validation for development cycles  
- **📚 Manual Examples** - Flexible testing for specific scenarios
- **🔍 Debugging Tools** - Detailed output for troubleshooting

**Ready to validate your plant disease classification AI!** 🌱✨
