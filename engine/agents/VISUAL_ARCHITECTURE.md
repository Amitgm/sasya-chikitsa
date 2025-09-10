# 🎯 Planning Agent System - Complete Visual Architecture

## 🏗️ **High-Level System Architecture**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           🌱 SASYA CHIKITSA PLANNING AGENT                      │
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │   📱 MOBILE     │    │   🌐 WEB APP    │    │   🔌 API CLIENTS           │ │
│  │   ANDROID APP   │    │   INTERFACE     │    │   THIRD PARTY               │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────────┘ │
│           │                       │                            │               │
│           └───────────────────────┼────────────────────────────┘               │
│                                   │                                            │
└───────────────────────────────────┼────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────┼────────────────────────────────────────────┐
│                    🚀 FASTAPI APPLICATION LAYER                                │
│                                   │                                            │
│  ┌─────────────────────────────────▼─────────────────────────────────────────┐ │
│  │                        📡 API ENDPOINTS                                    │ │
│  │  /planning/chat          /planning/chat-stream     /planning/session/{}   │ │
│  │  /planning/migrate       /planning/restart         /planning/actions      │ │
│  └─────────────────────────────────┬─────────────────────────────────────────┘ │
└───────────────────────────────────┼────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────┼────────────────────────────────────────────┐
│                    🎯 PLANNING AGENT CORE SYSTEM                              │
│                                   │                                            │
│  ┌─────────────────────────────────▼─────────────────────────────────────────┐ │
│  │                    🎭 PLANNING AGENT ORCHESTRATOR                         │ │
│  │                                                                           │ │
│  │  • Request Analysis & Intent Recognition                                   │ │
│  │  • Component Selection & Execution                                        │ │
│  │  • State Management & Flow Control                                        │ │
│  │  • Response Generation & User Guidance                                    │ │
│  └─────────────────┬─────────────────────────────────┬─────────────────────┘ │
│                    │                                 │                       │
│  ┌─────────────────▼─────────┐    ┌─────────────────▼─────────────────────┐ │
│  │    📊 SESSION MANAGER     │    │        🔀 WORKFLOW CONTROLLER        │ │
│  │                           │    │                                      │ │
│  │  • State Persistence      │    │  • Dynamic State Transitions         │ │
│  │  • Activity Logging       │    │  • Branching Logic Management        │ │
│  │  • History Management     │    │  • Next Step Determination          │ │
│  │  • Context Storage        │    │  • Available Actions Generation     │ │
│  └───────────────────────────┘    └──────────────────────────────────────┘ │
│                    │                                 │                       │
│  ┌─────────────────▼─────────────────────────────────▼─────────────────────┐ │
│  │                    🧩 COMPONENT EXECUTION LAYER                          │ │
│  └─────────────────┬─────────────────────────────────┬─────────────────────┘ │
└───────────────────┼─────────────────────────────────┼───────────────────────┘
                    │                                 │
┌───────────────────┼─────────────────────────────────┼───────────────────────┐
│                   │       🎮 COMPONENT HANDLERS      │                       │
│                   │                                 │                       │
│  ┌────────────────▼──┐  ┌──────────┐  ┌──────────┐  ▼──────────────────────┐ │
│  │ 📋 Intent Capture │  │ 💬 LLM   │  │ 🔬 Class │  │ 💊 Prescription     │ │
│  │ • Image Process   │  │ Clarify  │  │ ification│  │ • RAG Treatment     │ │
│  │ • Intent Analysis │  │ • Smart  │  │ • CNN    │  │ • Personalized     │ │
│  │ • Context Extract │  │   Questions│  │ • Attention│ │ • Multi-option    │ │
│  └───────────────────┘  └──────────┘  └──────────┘  └─────────────────────┘ │
│                                                                             │
│  ┌─────────────────────┐  ┌──────────────┐  ┌─────────────────────────────┐ │
│  │ ⚙️ Constraint       │  │ 🏪 Vendor    │  │ 🔄 Iterative Follow-up     │ │
│  │ Gathering           │  │ Recommend    │  │ • Corrections & Feedback    │ │
│  │ • User Preferences  │  │ • Local      │  │ • Alternative Options      │ │
│  │ • Budget & Organic  │  │   Suppliers  │  │ • Recursive Improvements   │ │
│  └─────────────────────┘  └──────────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────┼────────────────────────────────────────────┐
│                    🛠️ EXTERNAL INTEGRATIONS                                   │
│                                   │                                            │
│  ┌─────────────┐  ┌─────────────┐ ┌▼──────────┐  ┌─────────────────────────┐ │
│  │ 🧠 CNN      │  │ 🤖 OLLAMA   │ │ 📚 RAG    │  │ 🗄️ KNOWLEDGE BASE      │ │
│  │ Classifier  │  │ LLM         │ │ System    │  │ • Treatment Guidelines  │ │
│  │ • Disease   │  │ • Smart     │ │ • Context │  │ • Disease Database      │ │
│  │   Detection │  │   Questions │ │ • Treatment│ │ • Regional Information  │ │
│  │ • Attention │  │ • Reasoning │ │ • Retrieval│ │ • Vendor Database       │ │
│  └─────────────┘  └─────────────┘ └───────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 **Dynamic Workflow State Machine**

```
                          🌱 USER JOURNEY WORKFLOW

┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│    👤 USER STARTS                                                              │
│         │                                                                       │
│    ┌────▼────┐                                                                 │
│    │ INITIAL │ ──── New Session Created                                        │
│    └────┬────┘                                                                 │
│         │                                                                       │
│         ▼                                                                       │
│  ┌─────────────────┐     📸 Image + Intent                                     │
│  │ INTENT_CAPTURE  │ ◄── User uploads leaf image                               │
│  │                 │ ◄── "What's wrong with my plant?"                        │
│  │ 📋 Process:     │                                                           │
│  │ • Analyze image │     ✅ Clear Intent & Complete Info                       │
│  │ • Extract intent│ ────────────────────────┐                                │
│  │ • Parse context │                         │                                │
│  │ • Identify gaps │     ❓ Missing Info     │                                │
│  └─────────┬───────┘ ────────────────┐       │                                │
│            │                         │       │                                │
│            ▼                         ▼       ▼                                │
│    ┌─────────────────┐        ┌─────────────────┐                             │
│    │ CLARIFICATION   │        │ CLASSIFICATION  │                             │
│    │                 │        │                 │                             │
│    │ 💬 LLM Asks:    │        │ 🔬 Process:     │                             │
│    │ • "Crop type?"  │        │ • CNN Analysis  │                             │
│    │ • "Location?"   │        │ • Attention Map │                             │
│    │ • "Season?"     │        │ • Confidence    │                             │
│    │ • "Symptoms?"   │        │ • Validation    │                             │
│    └─────────┬───────┘        └─────────┬───────┘                             │
│              │                          │                                     │
│              ▼                          ▼                                     │
│      ❓ Still Missing? ────No───► 🔬 Classification Ready                     │
│              │                          │                                     │
│              Yes                        ▼                                     │
│              │                  ┌─────────────────┐                          │
│              │                  │ PRESCRIPTION    │                          │
│              │                  │                 │                          │
│              └──────────────────►│ 💊 Generate:   │                          │
│                                 │ • RAG Query     │                          │
│                                 │ • Treatment     │                          │
│                                 │ • Personalize   │                          │
│                                 │ • Multi-option  │                          │
│                                 └─────────┬───────┘                          │
│                                           │                                   │
│                    ┌──────────────────────┼──────────────────────┐            │
│                    │                      │                      │            │
│                    ▼                      ▼                      ▼            │
│         ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    │
│         │CONSTRAINT_      │    │VENDOR_          │    │FOLLOW_UP        │    │
│         │GATHERING        │    │RECOMMENDATION   │    │                 │    │
│         │                 │    │                 │    │ 🔄 Handle:      │    │
│         │ ⚙️ Collect:     │    │ 🏪 Suggest:     │    │ • Corrections   │    │
│         │ • Preferences   │    │ • Local shops   │    │ • Alternatives  │    │
│         │ • Budget limits │    │ • Online stores │    │ • New problems  │    │
│         │ • Organic only  │    │ • Cost estimates│    │ • Iterations    │    │
│         └─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘    │
│                   │                      │                      │            │
│                   └──────────────────────┼──────────────────────┘            │
│                                          │                                   │
│                                          ▼                                   │
│                                 ┌─────────────────┐                          │
│                                 │   COMPLETED     │                          │
│                                 │                 │                          │
│                                 │ ✅ Journey:     │                          │
│                                 │ • Diagnosis ✓   │                          │
│                                 │ • Treatment ✓   │                          │
│                                 │ • Vendors ✓     │                          │
│                                 │ • Support ✓     │                          │
│                                 └─────────────────┘                          │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────────┘

🔄 ITERATIVE LOOPS:
   • Any state can return to FOLLOW_UP for corrections
   • FOLLOW_UP can branch to: RECLASSIFICATION, ALTERNATIVE_PRESCRIPTION, NEW_PROBLEM
   • USER FEEDBACK continuously improves accuracy
```

## 🎮 **User Interaction Flow**

```
                    🎯 CONVERSATION FLOW EXAMPLES

┌─────────────────────────────────────────────────────────────────────────────────┐
│                            SCENARIO 1: NEW USER WITH IMAGE                     │
│                                                                                 │
│  👤 User: [uploads tomato leaf image] "What's wrong with my plant?"            │
│      │                                                                         │
│  🎯 INTENT_CAPTURE:                                                            │
│      ├─ Detects: Disease classification intent                                 │
│      ├─ Processes: Tomato leaf image (quality: good)                          │
│      ├─ Extracts: Crop type = "tomato", Problem = "disease inquiry"           │
│      └─ Missing: Location, Season                                              │
│      │                                                                         │
│  🤖 System: "I can see you've uploaded a tomato leaf image for disease        │
│             identification. I've noted your crop type: tomato.                 │
│             What's your location (district/state) for region-specific advice?" │
│      │                                                                         │
│  👤 User: "I'm in Punjab, India. It's monsoon season."                        │
│      │                                                                         │
│  💬 CLARIFICATION:                                                             │
│      ├─ Extracts: Location = "Punjab, India", Season = "monsoon"              │
│      ├─ Validates: All required info present                                   │
│      └─ Decision: Proceed to classification                                     │
│      │                                                                         │
│  🤖 System: "Perfect! I have enough information. I'll now analyze your        │
│             tomato leaf image to identify any diseases."                       │
│      │                                                                         │
│  🔬 CLASSIFICATION:                                                            │
│      ├─ CNN Analysis: Early Blight detected (89% confidence)                  │
│      ├─ Attention Map: Generated focus areas visualization                     │
│      └─ Quality: High confidence diagnosis                                     │
│      │                                                                         │
│  🤖 System: "🔬 Disease Classification Results                                │
│             Diagnosis: Early Blight                                            │
│             Confidence: 89% (high)                                             │
│             🎯 I've generated a visualization showing focus areas.             │
│             I'm confident in this diagnosis. Ready for treatment?"             │
│      │                                                                         │
│  👤 User: "Yes, please provide treatment options."                            │
│      │                                                                         │
│  💊 PRESCRIPTION:                                                              │
│      ├─ RAG Query: "Early blight treatment tomato Punjab monsoon"             │
│      ├─ Personalization: Location + season + crop specific                    │
│      └─ Multi-options: Chemical, organic, preventive                          │
│      │                                                                         │
│  🤖 System: "💊 Treatment Prescription for Early Blight                       │
│             Chemical: Copper sulfate spray (2g/L), weekly                     │
│             Organic: Neem oil + proper spacing                                 │
│             Prevention: Crop rotation, drip irrigation                         │
│             🏪 Would you like local vendor suggestions?"                       │
│      │                                                                         │
│  👤 User: "Yes, I prefer organic. Show me vendors."                           │
│      │                                                                         │
│  🏪 VENDOR_RECOMMENDATION:                                                     │
│      ├─ Location filter: Punjab suppliers                                     │
│      ├─ Preference filter: Organic products                                   │
│      └─ Cost estimation: ₹150-250 range                                       │
│      │                                                                         │
│  🤖 System: "🏪 Organic Vendors in Punjab:                                    │
│             • Green Valley Agri (2.5km) - Neem oil specialist                 │
│             • Farmers Choice (5.1km) - Organic certified                      │
│             💰 Estimated cost: ₹150-250                                       │
│             Need any other help?"                                              │
│      │                                                                         │
│  👤 User: "Perfect, thank you!"                                               │
│      │                                                                         │
│  ✅ COMPLETED                                                                  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                      SCENARIO 2: CORRECTION & ITERATION                        │
│                                                                                 │
│  👤 User: [after classification] "I think it's late blight, not early blight" │
│      │                                                                         │
│  🔄 ITERATIVE_FOLLOWUP:                                                        │
│      ├─ Detects: Correction feedback                                           │
│      ├─ Extracts: Disease = "late blight"                                     │
│      └─ Action: Update diagnosis with user input                               │
│      │                                                                         │
│  🤖 System: "I understand the classification may not be accurate.             │
│             You're suggesting it might be late blight.                         │
│             Let me update the diagnosis. Shall I proceed with this correction?" │
│      │                                                                         │
│  👤 User: "Yes, and I need urgent treatment options."                         │
│      │                                                                         │
│  🔄 Flow branches back to PRESCRIPTION with updated data:                     │
│      ├─ Disease: Late Blight (user-corrected)                                │
│      ├─ Urgency: High priority                                                │
│      └─ Confidence: 80% (user-provided)                                       │
│      │                                                                         │
│  💊 Updated prescription generated for Late Blight + urgent treatment...      │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🧠 **Component Interaction Diagram**

```
                        🧩 COMPONENT COLLABORATION

┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│                          📥 USER REQUEST ARRIVES                               │
│                                    │                                           │
│                                    ▼                                           │
│            ┌─────────────────────────────────────────────────┐                │
│            │         🎭 PLANNING AGENT ORCHESTRATOR          │                │
│            │                                                 │                │
│            │  1️⃣ Analyze request type and context           │                │
│            │  2️⃣ Determine current workflow state            │                │
│            │  3️⃣ Select appropriate component handler        │                │
│            │  4️⃣ Execute component with session context      │                │
│            │  5️⃣ Process results and update session          │                │
│            │  6️⃣ Determine next steps via WorkflowController │                │
│            └─────────────┬───────────────────────────────────┘                │
│                          │                                                     │
│                          ▼                                                     │
│    ┌─────────────────────────────────────────────────────────────────────┐   │
│    │                    🔧 COMPONENT EXECUTION                           │   │
│    │                                                                     │   │
│    │     ┌─────────────┐     📋 BaseComponent Interface:                 │   │
│    │     │   SESSION   │ ◄── • validate_inputs()                        │   │
│    │  ┌──┤   MANAGER   │ ◄── • execute() - main logic                   │   │
│    │  │  │             │ ◄── • create_success_result()                   │   │
│    │  │  └─────────────┘ ◄── • create_error_result()                     │   │
│    │  │                                                                  │   │
│    │  │  ┌─────────────────────────────────────────────────────────────┐ │   │
│    │  │  │                COMPONENT HANDLERS                           │ │   │
│    │  │  │                                                             │ │   │
│    │  │  │  📋 IntentCapture    💬 LLMClarification   🔬 Classification │ │   │
│    │  │  │  ┌─────────────┐    ┌─────────────┐      ┌─────────────┐   │ │   │
│    │  └──┼──┤• Image proc │    │• LLM queries│      │• CNN model  │   │ │   │
│    │     │  │• Intent rec │    │• Smart ?s   │      │• Attention  │   │ │   │
│    │     │  │• Context    │    │• Info gap   │      │• Confidence │   │ │   │
│    │     │  └─────────────┘    └─────────────┘      └─────────────┘   │ │   │
│    │     │                                                            │ │   │
│    │     │  💊 Prescription     ⚙️ ConstraintGather  🏪 VendorRecom   │ │   │
│    │     │  ┌─────────────┐    ┌─────────────┐      ┌─────────────┐   │ │   │
│    │     └──┤• RAG query  │    │• Preferences│      │• Location   │   │ │   │
│    │        │• Treatment  │    │• Budgets    │      │• Suppliers  │   │ │   │
│    │        │• Personalize│    │• Organic    │      │• Costs      │   │ │   │
│    │        └─────────────┘    └─────────────┘      └─────────────┘   │ │   │
│    │                                                                  │ │   │
│    │        🔄 IterativeFollowup                                      │ │   │
│    │        ┌─────────────┐                                           │ │   │
│    │        │• Corrections│                                           │ │   │
│    │        │• Iterations │                                           │ │   │
│    │        │• Branching  │                                           │ │   │
│    │        └─────────────┘                                           │ │   │
│    └─────────────────────────────────────────────────────────────────────┘   │
│                          │                                                     │
│                          ▼                                                     │
│            ┌─────────────────────────────────────────────────┐                │
│            │         🔀 WORKFLOW CONTROLLER                  │                │
│            │                                                 │                │
│            │  🎯 Responsibilities:                           │                │
│            │  • Analyze component results                    │                │
│            │  • Determine next workflow state                │                │
│            │  • Handle branching logic                       │                │
│            │  • Generate available actions                   │                │
│            │  • Manage state transitions                     │                │
│            └─────────────┬───────────────────────────────────┘                │
│                          │                                                     │
│                          ▼                                                     │
│                    📊 SESSION UPDATE                                           │
│                          │                                                     │
│                          ▼                                                     │
│                    📤 RESPONSE TO USER                                         │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 💾 **Data Flow & Session Management**

```
                          📊 SESSION DATA LIFECYCLE

┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  🆕 NEW SESSION CREATED                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ SessionData {                                                           │   │
│  │   session_id: "user_123",                                              │   │
│  │   created_at: "2024-01-15T10:30:00Z",                                  │   │
│  │   workflow_state: "initial",                                           │   │
│  │   user_profile: {},                                                    │   │
│  │   diagnosis_results: {},                                               │   │
│  │   prescriptions: [],                                                   │   │
│  │   vendor_choices: [],                                                  │   │
│  │   activities: []                                                       │   │
│  │ }                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                           │
│                                    ▼                                           │
│  📋 INTENT CAPTURE UPDATES                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ user_profile: {                                                        │   │
│  │   primary_intent: "disease_classification",                            │   │
│  │   crop_type: "tomato",                                                 │   │
│  │   has_image: true,                                                     │   │
│  │   problem_description: "brown spots on leaves"                        │   │
│  │ },                                                                     │   │
│  │ workflow_state: "clarification",                                       │   │
│  │ activities: [                                                          │   │
│  │   {timestamp: "...", state: "intent_capture", user_input: "..."}       │   │
│  │ ]                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                           │
│                                    ▼                                           │
│  💬 CLARIFICATION ADDS                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ user_profile: {                                                        │   │
│  │   ...existing...,                                                      │   │
│  │   location: "Punjab, India",                                           │   │
│  │   season: "monsoon",                                                   │   │
│  │   clarification_complete: true                                         │   │
│  │ },                                                                     │   │
│  │ workflow_state: "classification"                                       │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                           │
│                                    ▼                                           │
│  🔬 CLASSIFICATION RESULTS                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ diagnosis_results: {                                                   │   │
│  │   disease_name: "early_blight",                                        │   │
│  │   friendly_disease_name: "Early Blight",                               │   │
│  │   confidence: 0.89,                                                    │   │
│  │   confidence_level: "high",                                            │   │
│  │   attention_overlay: "base64_image_data...",                           │   │
│  │   severity_assessment: "Confident diagnosis - treatment recommended"   │   │
│  │ },                                                                     │   │
│  │ workflow_state: "prescription"                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                           │
│                                    ▼                                           │
│  💊 PRESCRIPTION GENERATED                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ prescriptions: [                                                       │   │
│  │   {                                                                    │   │
│  │     timestamp: "2024-01-15T10:35:00Z",                                 │   │
│  │     prescription: {                                                    │   │
│  │       disease: "early_blight",                                         │   │
│  │       treatment_options: {                                             │   │
│  │         chemical: "Copper sulfate spray (2g/L)",                      │   │
│  │         organic: "Neem oil + plant spacing",                          │   │
│  │         prevention: "Crop rotation, drip irrigation"                  │   │
│  │       }                                                                │   │
│  │     }                                                                  │   │
│  │   }                                                                    │   │
│  │ ],                                                                     │   │
│  │ workflow_state: "vendor_recommendation"                                │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                           │
│                                    ▼                                           │
│  🏪 VENDOR CHOICES LOGGED                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ vendor_choices: [                                                      │   │
│  │   {                                                                    │   │
│  │     timestamp: "2024-01-15T10:37:00Z",                                 │   │
│  │     choice: {                                                          │   │
│  │       preferred_vendor: "Green Valley Agri",                          │   │
│  │       treatment_type: "organic",                                       │   │
│  │       estimated_cost: "₹180"                                           │   │
│  │     }                                                                  │   │
│  │   }                                                                    │   │
│  │ ],                                                                     │   │
│  │ workflow_state: "completed"                                            │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  💾 COMPLETE SESSION SUMMARY:                                                  │
│  • Total Duration: 7 minutes                                                   │
│  • Interactions: 6 user inputs, 8 system responses                             │
│  • Success Metrics: Diagnosis ✓, Treatment ✓, Vendor ✓                        │
│  • User Satisfaction: High (no corrections needed)                             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🚀 **API Integration Points**

```
                           🔌 API ENDPOINT ARCHITECTURE

┌─────────────────────────────────────────────────────────────────────────────────┐
│                            EXISTING SYSTEM INTEGRATION                         │
│                                                                                 │
│  📱 MOBILE APP (Android/iOS)                 🌐 WEB INTERFACE                   │
│  ┌─────────────────────┐                    ┌─────────────────────┐            │
│  │ Current Endpoints:  │                    │ Current Endpoints:  │            │
│  │ • POST /chat        │                    │ • POST /chat        │            │
│  │ • POST /chat-stream │ ◄──────────────────┤ • POST /chat-stream │            │
│  │ • GET /session/{}   │                    │ • GET /session/{}   │            │
│  └─────────────────────┘                    └─────────────────────┘            │
│            │                                          │                        │
│            └──────────────────┬───────────────────────┘                        │
│                               │                                                │
│                               ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                     🚀 FASTAPI ROUTER                                  │  │
│  │                                                                         │  │
│  │  🔄 HYBRID ROUTING LOGIC:                                              │  │
│  │                                                                         │  │
│  │  if (request.has_image || request.guided_mode):                        │  │
│  │      → route_to_planning_agent()                                       │  │
│  │  else:                                                                  │  │
│  │      → route_to_legacy_agent()                                         │  │
│  └─────────────┬─────────────────────────────┬─────────────────────────────┘  │
│                │                             │                                │
│                ▼                             ▼                                │
│  ┌─────────────────────────┐    ┌─────────────────────────────────────────┐   │
│  │   🆕 PLANNING AGENT     │    │      ⚡ LEGACY AGENT                   │   │
│  │   API ENDPOINTS         │    │      (Existing System)                 │   │
│  │                         │    │                                         │   │
│  │ POST /planning/chat     │    │ POST /chat                              │   │
│  │ POST /planning/stream   │    │ POST /chat-stream                       │   │
│  │ GET  /planning/session  │    │ GET  /session-history/{id}              │   │
│  │ POST /planning/restart  │    │ POST /summarize_response                │   │
│  │ GET  /planning/actions  │    │                                         │   │
│  │ POST /planning/migrate  │    │                                         │   │
│  └─────────┬───────────────┘    └─────────────────────────────────────────┘   │
│            │                                                                  │
│            ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                    🎯 PLANNING AGENT SYSTEM                             │  │
│  │                                                                         │  │
│  │  📊 Request Processing:                                                 │  │
│  │  1. Parse incoming request (PlanningChatRequest)                       │  │
│  │  2. Extract session_id, message, image_data, context                   │  │
│  │  3. Route to PlanningAgent.process_user_request()                      │  │
│  │  4. Execute appropriate component based on session state               │  │
│  │  5. Update session data and determine next steps                       │  │
│  │  6. Return structured response with next actions                       │  │
│  │                                                                         │  │
│  │  🌊 Streaming Support:                                                  │  │
│  │  • Progress updates during image processing                             │  │
│  │  • Real-time CNN classification feedback                               │  │
│  │  • Component execution status                                          │  │
│  │  • Attention visualization streaming                                   │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

📋 REQUEST/RESPONSE EXAMPLES:

┌─────────────────────────────────────────────────────────────────────────────────┐
│                               REQUEST FLOW                                     │
│                                                                                 │
│  📤 CLIENT REQUEST:                                                             │
│  {                                                                              │
│    "session_id": "user_123",                                                   │
│    "message": "What's wrong with my tomato plant?",                            │
│    "image_b64": "iVBORw0KGgoAAAANSUhEUgAAA...",                               │
│    "context": {"crop_type": "tomato"},                                         │
│    "workflow_action": null                                                     │
│  }                                                                              │
│                                                                                 │
│  📥 PLANNING AGENT RESPONSE:                                                    │
│  {                                                                              │
│    "success": true,                                                             │
│    "response": "I can see you've uploaded a tomato leaf image...",             │
│    "current_state": "clarification",                                           │
│    "next_actions": [                                                           │
│      "provide_location",                                                       │
│      "specify_symptoms",                                                       │
│      "proceed_with_classification"                                             │
│    ],                                                                           │
│    "requires_user_input": true,                                                │
│    "error_message": null                                                       │
│  }                                                                              │
│                                                                                 │
│  🌊 STREAMING RESPONSE:                                                         │
│  data: Processing uploaded image...                                            │
│  data: Analyzing plant condition...                                            │
│  data: Running disease classification...                                       │
│  data: Generating attention visualization...                                   │
│  data: I can see you've uploaded a tomato leaf image...                       │
│  data: [DONE]                                                                  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🎯 **Summary: Complete System Visualization**

The Planning Agent system provides:

1. **🏗️ Modular Architecture** - Clean separation between orchestration, components, and flow control
2. **🔄 Dynamic Workflow** - Intelligent state transitions based on user needs and context  
3. **🧠 LLM-Guided Intelligence** - Smart questioning and personalized interactions
4. **💾 Comprehensive State Management** - Full session persistence and activity tracking
5. **🔌 Seamless Integration** - Works alongside existing system with hybrid routing
6. **🎮 Rich User Experience** - Natural conversations with iterative improvements
7. **📊 Observable & Debuggable** - Complete visibility into system behavior

This visual architecture demonstrates how the system transforms rigid workflows into intelligent, user-centric conversations that adapt dynamically to provide the best possible plant disease diagnosis and treatment experience! 🌱
