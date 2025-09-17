# 🌍 Environment Configuration Guide

## ✅ **Environment Variable Loading - IMPLEMENTED**

The Planning Agent server now **automatically loads environment variables** from `.env` files, including `OLLAMA_HOST` and other configuration settings.

## 🚀 **How to Use**

### **Option 1: Auto-Detection (Recommended)**
The script automatically finds and loads `.env` files in this order:
1. `engine/.env` (main configuration)
2. Project root `.env`
3. Current directory `.env`

```bash
# Simple usage - auto-detects .env file
./run_planning_server.sh

# With development options
./run_planning_server.sh --dev --debug
```

### **Option 2: Specify .env File**
```bash
# Use specific .env file
./run_planning_server.sh --env /path/to/.env

# Use .env from engine directory
./run_planning_server.sh --env ../.env

# Use custom configuration
./run_planning_server.sh --env my-custom.env --dev
```

## 📋 **Environment Variables**

### **Ollama Configuration**
```bash
# Required for local Ollama usage
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

### **OpenAI Configuration** 
```bash
# Alternative to Ollama (comment out Ollama if using OpenAI)
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4
```

### **Other Configuration**
```bash
# Optional settings
DEBUG=true
```

## 🛠️ **Creating .env File**

### **Automatic Creation**
If no `.env` file is found, the script automatically creates an example:

```bash
./run_planning_server.sh
# Output:
# 💡 No .env file found. Creating example .env in current directory...
# 📝 Example .env file created at: .env
# Edit it with your configuration and rerun the script
```

### **Manual Creation**
Create `engine/.env` (recommended location):

```bash
# Planning Agent Environment Configuration

# Ollama Configuration (uncomment and configure for local Ollama)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# OpenAI Configuration (uncomment and add your API key)
#OPENAI_API_KEY=your_openai_api_key_here
#OPENAI_MODEL=gpt-4

# Other Configuration
#DEBUG=true
```

## 📊 **Environment Loading Status**

When the script runs, it shows exactly what's loaded:

```bash
🌍 Loading environment variables from: engine/.env
✅ Environment variables loaded
   🦙 OLLAMA_HOST: http://localhost:11434
   🤖 OLLAMA_MODEL: llama3.1:8b
```

## 🐛 **Troubleshooting**

### **OLLAMA_HOST=None Issue - SOLVED** ✅
**Problem**: Debug output showed `OLLAMA_HOST=None`
**Solution**: Use the updated script with `--env` option or auto-detection

### **Environment Variables Not Loading**
```bash
# Check if .env file exists
ls -la .env

# Test loading manually
source .env && echo "OLLAMA_HOST: $OLLAMA_HOST"

# Use explicit path
./run_planning_server.sh --env /full/path/to/.env
```

### **File Not Found**
```bash
# Check current directory
pwd

# List .env files
find . -name ".env*" -type f

# Use absolute path
./run_planning_server.sh --env /Users/yourusername/project/.env
```

### **Variables Not Exported**
Make sure variables are uncommented and have no spaces around `=`:
```bash
# ✅ Correct
OLLAMA_HOST=http://localhost:11434

# ❌ Wrong (commented out)
#OLLAMA_HOST=http://localhost:11434

# ❌ Wrong (spaces around =)
OLLAMA_HOST = http://localhost:11434
```

## 🎯 **Best Practices**

### **1. Use Main Configuration File**
Place your main `.env` file in the `engine/` directory:
```
engine/.env                    # ← Main configuration (recommended)
engine/agents/run_planning_server.sh
```

### **2. Version Control**
**Never commit** `.env` files with secrets:
```bash
# Add to .gitignore
echo ".env*" >> .gitignore
```

### **3. Environment-Specific Files**
```bash
.env.development    # Development settings
.env.production     # Production settings  
.env.local         # Local overrides
```

### **4. Validation**
Always check that variables loaded correctly:
```bash
./run_planning_server.sh --debug | grep OLLAMA
```

## 📈 **Usage Examples**

### **Local Ollama Setup**
```bash
# 1. Create .env file
cat > engine/.env << 'EOF'
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
EOF

# 2. Start Ollama (in another terminal)
ollama serve

# 3. Start planning agent
./run_planning_server.sh
```

### **OpenAI Setup**
```bash
# 1. Create .env file
cat > engine/.env << 'EOF'
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4
EOF

# 2. Start planning agent
./run_planning_server.sh
```

### **Development Setup**
```bash
# 1. Create development .env
cat > .env.dev << 'EOF'
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
DEBUG=true
EOF

# 2. Start with development settings
./run_planning_server.sh --env .env.dev --dev --debug
```

## 🎉 **Summary**

✅ **Environment variable loading fully implemented**
✅ **Auto-detection of .env files**
✅ **Manual .env file specification** 
✅ **Automatic .env file creation**
✅ **Comprehensive validation and debugging**
✅ **OLLAMA_HOST issue completely resolved**

**The Planning Agent server now properly loads and uses environment variables from .env files!** 🌱

---

### 🔗 **Related Commands**

```bash
# Show help with all options
./run_planning_server.sh --help

# Test environment loading only
./run_planning_server.sh --env .env --debug | head -20

# Start server with environment
./run_planning_server.sh --env ../.env --dev
```
