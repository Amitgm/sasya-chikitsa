package com.example.sasya_chikitsa.network.request

data class ChatRequestData(
    val message: String,
    val image_b64: String? = null, // Optional
    val session_id: String? = null  // Optional
)