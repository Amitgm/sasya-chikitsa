# 🚀 Planning Agent Server Setup & Usage

Complete guide for running the standalone Planning Agent FastAPI server.

## 📋 **Quick Start**

### **Option 1: Shell Script (Recommended)**
```bash
cd engine/agents
./run_planning_server.sh
```

### **Option 2: Python Startup Script**
```bash
cd engine/agents  
python3 start_server.py
```

### **Option 3: Direct Server**
```bash
cd engine/agents
python3 planning_server.py
```

### **Option 4: Uvicorn Direct**
```bash
cd engine/agents
uvicorn planning_server:app --host 0.0.0.0 --port 8001 --reload
```

## 🛠️ **Installation & Dependencies**

### **1. Install Requirements**
```bash
cd engine/agents
pip install -r requirements.txt
```

### **2. Core Dependencies**
- `fastapi>=0.104.1` - Web framework
- `uvicorn[standard]>=0.24.0` - ASGI server  
- `pydantic>=2.4.2` - Data validation

### **3. System Dependencies**
The planning agent also requires the existing system components:
- CNN classifier model
- Ollama LLM
- RAG system
- All existing engine dependencies

## ⚙️ **Configuration Options**

### **Command Line Arguments**
```bash
# Basic startup with auto-detected .env file
./run_planning_server.sh

# Development mode with auto-reload
./run_planning_server.sh --dev

# Custom port
./run_planning_server.sh --port 8002

# Debug logging
./run_planning_server.sh --debug

# Specify custom .env file
./run_planning_server.sh --env /path/to/.env

# Combined options
./run_planning_server.sh --dev --debug --port 9000 --env ../.env
```

### **Environment Variables**

The server now **automatically loads environment variables** from `.env` files:

```bash
# Create .env file (auto-detected locations):
# - engine/.env (recommended)  
# - project-root/.env
# - current-directory/.env

# Example .env content:
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
# OR
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4
```

**Manual Environment Setup** (if not using .env):
```bash
export PYTHONPATH="/path/to/sasya-chikitsa/engine:/path/to/sasya-chikitsa"
export HOST="0.0.0.0"
export PORT="8001"
export OLLAMA_HOST="http://localhost:11434"
export OLLAMA_MODEL="llama3.1:8b"
```

📖 **See [ENV_CONFIGURATION.md](ENV_CONFIGURATION.md) for detailed environment setup guide.**

## 🌐 **API Endpoints**

Once the server is running, these endpoints are available:

### **Core Endpoints**
- `GET /` - Server info and endpoint list
- `GET /health` - Health check with component status
- `GET /docs` - Interactive API documentation

### **Planning Agent Endpoints**
- `POST /planning/chat` - Main chat endpoint
- `POST /planning/chat-stream` - Streaming chat with progress
- `GET /planning/session/{session_id}` - Get session info
- `POST /planning/session/{session_id}/restart` - Restart session
- `GET /planning/session/{session_id}/actions` - Available actions
- `DELETE /planning/session/{session_id}` - Delete session

### **Debug Endpoints**
- `GET /planning/debug/sessions` - List all active sessions

## 📡 **API Usage Examples**

### **Basic Chat Request**
```bash
curl -X POST "http://localhost:8001/planning/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user123",
    "message": "What'\''s wrong with my tomato plant?",
    "image_b64": null
  }'
```

### **Chat with Image**
```bash
curl -X POST "http://localhost:8001/planning/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user123", 
    "message": "Diagnose this leaf",
    "image_b64": "'$(base64 -i leaf_image.jpg)'"
  }'
```

### **Streaming Chat**
```bash
curl -N "http://localhost:8001/planning/chat-stream" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user123",
    "message": "Help with plant disease"
  }'
```

### **Get Session Info**
```bash
curl "http://localhost:8001/planning/session/user123"
```

### **Health Check**
```bash
curl "http://localhost:8001/health"
```

## 🐛 **Troubleshooting**

### **Common Issues**

#### **Import Errors**
```
ImportError: No module named 'planning_agent'
```
**Solution:** Make sure PYTHONPATH includes the engine directory:
```bash
export PYTHONPATH="/path/to/sasya-chikitsa/engine:$PYTHONPATH"
```

#### **Missing Dependencies**  
```
ModuleNotFoundError: No module named 'fastapi'
```
**Solution:** Install requirements:
```bash
pip install -r requirements.txt
```

#### **Port Already in Use**
```
OSError: [Errno 48] Address already in use
```
**Solution:** Use a different port:
```bash
./run_planning_server.sh --port 8002
```

#### **Planning Agent Not Available**
```
HTTP 503: Planning agent not available
```  
**Solution:** Check server logs for initialization errors. Ensure all dependencies are installed.

### **Debug Mode**

Run with debug logging to see detailed information:
```bash
./run_planning_server.sh --debug
```

This will show:
- Detailed request/response logging
- Component execution traces  
- Session state changes
- Error stack traces

### **Log Files**

The server creates a log file: `planning_agent.log`
```bash
tail -f planning_agent.log
```

## 🔧 **Development Setup**

### **Development Mode**
```bash
# Auto-reload on code changes
./run_planning_server.sh --dev

# Or with uvicorn directly
uvicorn planning_server:app --reload --host 0.0.0.0 --port 8001
```

### **Testing the Server**
```bash
# Check dependencies only
python3 start_server.py --check-only

# Test basic functionality
curl http://localhost:8001/health

# Test chat endpoint
curl -X POST http://localhost:8001/planning/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "session_id": "test"}'
```

## 🌍 **Production Deployment**

### **Docker Setup** (Future)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python3", "planning_server.py", "--host", "0.0.0.0", "--port", "8001"]
```

### **Systemd Service** (Linux)
```ini
[Unit]
Description=Planning Agent Server
After=network.target

[Service]
Type=simple
User=sasya
WorkingDirectory=/path/to/sasya-chikitsa/engine/agents
Environment=PYTHONPATH=/path/to/sasya-chikitsa/engine
ExecStart=/usr/bin/python3 planning_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### **Reverse Proxy** (Nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /planning/chat-stream {
        proxy_pass http://localhost:8001;
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
    }
}
```

## 📊 **Monitoring & Metrics**

### **Health Monitoring**
```bash
# Basic health check
curl http://localhost:8001/health

# Component status
curl http://localhost:8001/health | jq '.components'
```

### **Session Monitoring**
```bash  
# Active sessions (debug endpoint)
curl http://localhost:8001/planning/debug/sessions
```

## 🔐 **Security Considerations**

⚠️ **Current Implementation Notes:**
- CORS is configured for development (`allow_origins=["*"]`)
- No authentication/authorization implemented
- Debug endpoints exposed

🛡️ **Production Recommendations:**
- Restrict CORS to specific origins
- Implement authentication middleware
- Disable debug endpoints
- Add rate limiting
- Use HTTPS with SSL certificates

---

## 🎯 **Summary**

The Planning Agent server is now a **fully functional, standalone FastAPI application** that can be:

- ✅ **Started easily** with multiple startup options
- ✅ **Configured flexibly** via command line arguments
- ✅ **Monitored effectively** with health checks and logging  
- ✅ **Developed efficiently** with auto-reload and debugging
- ✅ **Deployed reliably** in various environments

**Ready for production use and further development!** 🌱
