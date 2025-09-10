# Multi-Step Planning Agent System

A comprehensive, LLM-guided planning agent system for plant disease diagnosis that breaks down complex workflows into manageable, dynamic steps.

## 🎯 Overview

This system replaces the rigid, fixed-flow approach with an intelligent, adaptive workflow that guides users through plant disease diagnosis using 8 core components:

1. **Leaf Upload & Intent Capture** - Process images and understand user objectives
2. **LLM-Guided Clarification** - Intelligently gather missing context
3. **Classification Step** - CNN-based disease identification with attention visualization
4. **Prescription via RAG** - Personalized treatment recommendations
5. **Display & Constraint Gathering** - User preference collection
6. **Vendor Recommendation Branch** - Local supplier suggestions
7. **Iterative Follow-Up** - Dynamic conversation management
8. **Session Logging and State Tracking** - Comprehensive session management

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│           PlanningAgent                  │
│         (Main Orchestrator)             │
└─────────────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
┌───▼───┐    ┌─────▼─────┐    ┌───▼────┐
│Session│    │ Workflow  │    │Component│
│Manager│    │Controller │    │Handlers │
└───────┘    └───────────┘    └────────┘
     │              │              │
     │              │              │
┌────▼────┐    ┌────▼────┐    ┌────▼────┐
│ State   │    │ Flow    │    │8 Core   │
│Tracking │    │ Logic   │    │Steps    │
└─────────┘    └─────────┘    └─────────┘
```

## 📋 Component Breakdown

### Core Components

- **`PlanningAgent`** - Main orchestrator that coordinates the entire workflow
- **`SessionManager`** - Handles state persistence and activity logging  
- **`WorkflowController`** - Manages dynamic flow transitions and branching logic

### Component Handlers

Each component handles one workflow step:

- **`IntentCaptureComponent`** - Processes image uploads and captures user intent
- **`LLMClarificationComponent`** - Uses Ollama LLM for intelligent questioning
- **`ClassificationComponent`** - CNN disease classification with attention maps
- **`PrescriptionComponent`** - RAG-based treatment recommendations
- **`ConstraintGatheringComponent`** - Collects user preferences and constraints
- **`VendorRecommendationComponent`** - Local supplier suggestions
- **`IterativeFollowUpComponent`** - Follow-up conversations and iteration

## 🚀 Quick Start

### Basic Integration

```python
from engine.agents import PlanningAgent
from engine.agents.planning_api import add_planning_agent_to_app

# Add to existing FastAPI app
app = FastAPI()
planning_api = add_planning_agent_to_app(app)

# Use programmatically
planning_agent = PlanningAgent()
result = await planning_agent.process_user_request(
    session_id="user123",
    user_input="What's wrong with my tomato plant?",
    image_data="base64_image_data",
    context={"crop_type": "tomato"}
)
```

### API Endpoints

- **`POST /planning/chat`** - Main chat endpoint
- **`POST /planning/chat-stream`** - Streaming chat with progress updates
- **`GET /planning/session/{session_id}`** - Get session state
- **`POST /planning/session/{session_id}/restart`** - Restart session
- **`GET /planning/session/{session_id}/actions`** - Get available actions

## 🔄 Workflow States

The system transitions through these states dynamically:

```
INITIAL → INTENT_CAPTURE → CLARIFICATION → CLASSIFICATION 
    ↓              ↓              ↓             ↓
PRESCRIPTION → CONSTRAINT_GATHERING → VENDOR_RECOMMENDATION
    ↓                    ↓                     ↓
FOLLOW_UP ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←← COMPLETED
```

### State Descriptions

- **`INITIAL`** - Fresh session start
- **`INTENT_CAPTURE`** - Processing image and understanding intent
- **`CLARIFICATION`** - Gathering missing information via LLM
- **`CLASSIFICATION`** - Running CNN disease classification
- **`PRESCRIPTION`** - Generating RAG-based treatment recommendations
- **`CONSTRAINT_GATHERING`** - Collecting user preferences
- **`VENDOR_RECOMMENDATION`** - Suggesting local suppliers
- **`FOLLOW_UP`** - Handling iterations and follow-up questions
- **`COMPLETED`** - Workflow finished

## 💾 Session Management

The system maintains comprehensive session state:

```python
{
    "session_info": {
        "session_id": "user123",
        "created_at": "2024-01-15T10:30:00Z",
        "current_state": "prescription"
    },
    "user_profile": {
        "crop_type": "tomato",
        "location": "Punjab, India",
        "season": "kharif"
    },
    "diagnosis_results": {
        "disease_name": "early_blight",
        "confidence": 0.89,
        "attention_overlay": "base64_visualization"
    },
    "prescriptions": [...],
    "activities": [...]
}
```

## 🎮 Usage Examples

### Example 1: Complete Diagnosis Flow

```python
# Step 1: User uploads image
result1 = await planning_agent.process_user_request(
    session_id="farm001",
    user_input="My tomato leaves have brown spots",
    image_data="base64_leaf_image"
)
# State: INTENT_CAPTURE → CLARIFICATION

# Step 2: Provide location
result2 = await planning_agent.process_user_request(
    session_id="farm001",
    user_input="I'm in Maharashtra, it's monsoon season"
)
# State: CLARIFICATION → CLASSIFICATION

# Step 3: System classifies disease
# State: CLASSIFICATION → PRESCRIPTION

# Step 4: User requests vendors
result3 = await planning_agent.process_user_request(
    session_id="farm001",
    user_input="Yes, please suggest local vendors"
)
# State: PRESCRIPTION → VENDOR_RECOMMENDATION
```

### Example 2: Iterative Improvement

```python
# User disagrees with classification
result = await planning_agent.process_user_request(
    session_id="farm001",
    user_input="I think it's late blight, not early blight"
)
# System updates diagnosis and provides new prescription

# User requests alternative treatment
result = await planning_agent.process_user_request(
    session_id="farm001",
    user_input="Do you have organic alternatives?"
)
# System provides organic treatment options
```

## 🔧 Integration with Existing System

### Hybrid Setup

The planning agent can work alongside the existing agent system:

```python
from engine.agents.integration_example import HybridAgentSystem

# Create hybrid system
app = FastAPI()
hybrid_system = HybridAgentSystem(app)

# Intelligent routing based on request type
# - Complex workflows → Planning Agent  
# - Simple questions → Legacy Agent
```

### Migration Support

Migrate existing sessions to the planning system:

```python
from engine.agents.integration_example import migrate_legacy_session_to_planning

await migrate_legacy_session_to_planning(
    session_id="existing_session",
    legacy_agent=agent_core,
    planning_agent=planning_agent
)
```

## 📊 Key Benefits

1. **🎯 Dynamic Flow** - Adapts based on user needs and context
2. **🧠 LLM-Guided** - Intelligent questioning and clarification
3. **📈 Modular** - Easy to extend with new components
4. **💾 Persistent** - Comprehensive session management
5. **🔄 Iterative** - Supports corrections and improvements
6. **🎮 User-Centric** - Natural conversation flow
7. **⚡ Performance** - Efficient state management and caching
8. **🔍 Observable** - Detailed logging and debugging

## 🛠️ Development

### Adding New Components

1. Inherit from `BaseComponent`
2. Implement `execute()` method
3. Add to component registry in `PlanningAgent`
4. Update workflow transitions in `WorkflowController`

```python
class MyNewComponent(BaseComponent):
    async def execute(self, session_id, user_input, image_data, session_data, context):
        # Your component logic here
        return self.create_success_result(
            response="Component response",
            session_data={"new_data": "value"},
            requires_user_input=True
        )
```

### Testing

Each component can be tested independently:

```python
component = IntentCaptureComponent()
result = await component.execute(
    session_id="test",
    user_input="My plant is sick",
    image_data=None,
    session_data={},
    context={}
)
assert result.success == True
```

## 🚦 Status

- ✅ Core architecture implemented
- ✅ All 8 components created
- ✅ Session management system
- ✅ API integration layer
- ✅ Workflow control logic
- ⏳ Testing and validation needed
- ⏳ Performance optimization
- ⏳ Integration testing with existing system

## 🤝 Contributing

1. Components should follow the `BaseComponent` interface
2. All components must handle errors gracefully
3. Session data updates should be atomic
4. Add logging for debugging and monitoring
5. Test each component independently before integration

---

This planning agent system provides the foundation for an intelligent, adaptive plant disease diagnosis platform that guides users through complex workflows naturally and efficiently! 🌱
