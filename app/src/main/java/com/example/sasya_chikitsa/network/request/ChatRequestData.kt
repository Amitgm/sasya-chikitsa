package com.example.sasya_chikitsa.network.request

data class ChatRequestData(
    val message: String,
    val image_b64: String? = null, // Optional
    val session_id: String? = null, // Optional
    val context: Map<String, Any>? = null, // Optional context for planning agent
    val workflow_action: String? = null // Optional workflow action for planning agent
)