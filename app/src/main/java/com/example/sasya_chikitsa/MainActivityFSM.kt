package com.example.sasya_chikitsa

import android.app.Activity
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.ImageDecoder
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.util.Base64
import android.util.Log
import android.view.View
import android.widget.*
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.cardview.widget.CardView
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.sasya_chikitsa.config.ServerConfig
import com.example.sasya_chikitsa.fsm.*
import com.example.sasya_chikitsa.network.RetrofitClient
import com.example.sasya_chikitsa.models.MessageFeedback
import com.example.sasya_chikitsa.models.FeedbackType
import com.example.sasya_chikitsa.models.FeedbackManager
import com.google.android.material.chip.Chip
import com.google.android.material.chip.ChipGroup
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.ResponseBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.ByteArrayOutputStream
import java.util.*

/**
 * Main Activity with integrated FSM Agent for plant diagnosis
 * Features:
 * - Real-time chat with FSM agent
 * - Streaming responses with state updates
 * - Light green follow-up buttons as requested
 * - Compact "Sasya Arogya" header design
 */
class MainActivityFSM : ComponentActivity(), FSMStreamHandler.StreamCallback {
    
    // UI Components
    private lateinit var stateIndicator: TextView
    private lateinit var settingsBtn: ImageButton
    private lateinit var chatRecyclerView: RecyclerView
    private lateinit var followUpContainer: LinearLayout
    private lateinit var followUpChipGroup: ChipGroup
    private lateinit var uploadBtn: ImageButton
    private lateinit var messageInput: EditText
    private lateinit var sendBtn: ImageButton
    private lateinit var uploadSection: CardView
    private lateinit var imagePreview: ImageView
    private lateinit var imageFileName: TextView
    private lateinit var removeImageBtn: ImageButton
    
    // FSM Components
    private lateinit var chatAdapter: ChatAdapter
    private lateinit var streamHandler: FSMStreamHandler
    private var currentSessionState = FSMSessionState()
    
    // Image handling
    private var selectedImageUri: Uri? = null
    private var selectedImageBase64: String? = null
    
    // Thinking indicator
    private var isThinking = false
    private var thinkingAnimation: Runnable? = null
    private var thinkingMessage: ChatMessage? = null
    
    private val TAG = "MainActivityFSM"
    
    // Image picker launcher
    private val imagePickerLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri ->
        uri?.let { handleSelectedImage(it) }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        initializeFSMComponents()
        initializeViews()
        setupClickListeners()
        setupRecyclerView()
        
        // Add welcome message
        addWelcomeMessage()
        
        Log.d(TAG, "FSM Activity initialized")
    }
    
    private fun initializeFSMComponents() {
        // Initialize FSM Retrofit client
        FSMRetrofitClient.initialize(this)
        
        // Initialize stream handler
        streamHandler = FSMStreamHandler()
        
        // Initialize chat adapter
        chatAdapter = ChatAdapter(
            onFollowUpClick = { followUpText ->
            handleFollowUpClick(followUpText)
            },
            onThumbsUpClick = { chatMessage ->
                handleThumbsUpFeedback(chatMessage)
            },
            onThumbsDownClick = { chatMessage ->
                handleThumbsDownFeedback(chatMessage)
            }
        )
        
        Log.d(TAG, "FSM components initialized")
    }
    
    private fun initializeViews() {
        // Header components
        stateIndicator = findViewById(R.id.stateIndicator)
        settingsBtn = findViewById(R.id.settingsBtn)
        
        // Chat components
        chatRecyclerView = findViewById(R.id.chatRecyclerView)
        followUpContainer = findViewById(R.id.followUpContainer)
        followUpChipGroup = findViewById(R.id.followUpChipGroup)
        
        // Input components
        uploadBtn = findViewById(R.id.uploadBtn)
        messageInput = findViewById(R.id.messageInput)
        sendBtn = findViewById(R.id.sendBtn)
        uploadSection = findViewById(R.id.uploadSection)
        imagePreview = findViewById(R.id.imagePreview)
        imageFileName = findViewById(R.id.imageFileName)
        removeImageBtn = findViewById(R.id.removeImageBtn)
        
        // Initialize server status display
        updateServerStatusDisplay()
    }
    
    private fun setupClickListeners() {
        uploadBtn.setOnClickListener { openImagePicker() }
        sendBtn.setOnClickListener { sendMessage() }
        removeImageBtn.setOnClickListener { clearSelectedImage() }
        settingsBtn.setOnClickListener { showServerSettings() }
        
        // Enter key to send message
        messageInput.setOnKeyListener { _, keyCode, event ->
            if (keyCode == android.view.KeyEvent.KEYCODE_ENTER && event.action == android.view.KeyEvent.ACTION_DOWN) {
                sendMessage()
                true
            } else false
        }
    }
    
    private fun setupRecyclerView() {
        val layoutManager = LinearLayoutManager(this)
        layoutManager.stackFromEnd = true
        chatRecyclerView.layoutManager = layoutManager
        chatRecyclerView.adapter = chatAdapter
    }
    
    private fun addWelcomeMessage() {
        val welcomeMessage = ChatMessage(
            text = "🌿 Welcome to Sasya Arogya! I'm your intelligent plant health assistant.\n\nI can help you:\n• Diagnose plant diseases from images\n• Recommend treatments and medicines\n• Connect you with local vendors\n• Provide seasonal care advice\n\nHow can I help you today?",
            isUser = false,
            state = "Ready"
        )
        
        chatAdapter.addMessage(welcomeMessage)
        currentSessionState.messages.add(welcomeMessage)
        scrollToBottom()
    }
    
    private fun openImagePicker() {
        try {
            imagePickerLauncher.launch("image/*")
        } catch (e: Exception) {
            Log.e(TAG, "Error opening image picker", e)
            showError("Failed to open image picker: ${e.message}")
        }
    }
    
    private fun handleSelectedImage(uri: Uri) {
        try {
            selectedImageUri = uri
            
            // Convert to bitmap and base64
            val bitmap = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                ImageDecoder.decodeBitmap(ImageDecoder.createSource(contentResolver, uri))
            } else {
                @Suppress("DEPRECATION")
                MediaStore.Images.Media.getBitmap(contentResolver, uri)
            }
            
            // Resize bitmap if too large
            val resizedBitmap = resizeBitmap(bitmap, 1024)
            selectedImageBase64 = bitmapToBase64(resizedBitmap)
            
            // Show image preview
            imagePreview.setImageBitmap(resizedBitmap)
            imageFileName.text = "📷 Image selected"
            uploadSection.visibility = View.VISIBLE
            
            Log.d(TAG, "Image selected and processed")
            
        } catch (e: Exception) {
            Log.e(TAG, "Error processing selected image", e)
            showError("Error processing image: ${e.message}")
        }
    }
    
    private fun clearSelectedImage() {
        selectedImageUri = null
        selectedImageBase64 = null
        uploadSection.visibility = View.GONE
        Log.d(TAG, "Image cleared")
    }
    
    private fun sendMessage() {
        val messageText = messageInput.text.toString().trim()
        if (messageText.isEmpty() && selectedImageBase64 == null) {
            return
        }
        
        // Create user message
        val userMessage = ChatMessage(
            text = if (messageText.isEmpty()) "📷 [Image uploaded]" else messageText,
            isUser = true,
            imageUri = selectedImageUri?.toString()
        )
        
        // Add user message to chat
        chatAdapter.addMessage(userMessage)
        currentSessionState.messages.add(userMessage)
        scrollToBottom()
        
        // Clear input
        messageInput.text.clear()
        val imageB64 = selectedImageBase64
        clearSelectedImage()
        
        // Send to FSM agent
        sendToFSMAgent(messageText.ifEmpty { "Please analyze this plant image" }, imageB64)
        
        // Show thinking indicator
        showThinkingIndicator()
        
        // Update state
        updateStateIndicator("Processing...")
    }
    
    private fun sendToFSMAgent(message: String, imageBase64: String?) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val request = streamHandler.createChatRequest(
                    message = message,
                    imageBase64 = imageBase64,
                    sessionId = currentSessionState.sessionId,
                    context = FSMRetrofitClient.getDefaultContext()
                )
                
                Log.d(TAG, "Sending request to FSM agent: $message")
                
                val call = FSMRetrofitClient.apiService.chatStream(request)
                val response = call.execute()
                
                if (response.isSuccessful && response.body() != null) {
                    streamHandler.processStream(response.body()!!, this@MainActivityFSM)
                } else {
                    withContext(Dispatchers.Main) {
                        showError("Failed to connect to FSM agent: ${response.message()}")
                        updateStateIndicator("Error")
                    }
                }
                
            } catch (e: Exception) {
                Log.e(TAG, "Error sending message to FSM agent", e)
                withContext(Dispatchers.Main) {
                    showError("Connection error: ${e.message}")
                    updateStateIndicator("Error")
                }
            }
        }
    }
    
    private fun handleFollowUpClick(followUpText: String) {
        Log.d(TAG, "Follow-up clicked: $followUpText")
        
        // Add follow-up as user message
        val followUpMessage = ChatMessage(
            text = followUpText,
            isUser = true
        )
        
        chatAdapter.addMessage(followUpMessage)
        currentSessionState.messages.add(followUpMessage)
        scrollToBottom()
        
        // Send to FSM agent
        sendToFSMAgent(followUpText, null)
        
        // Show thinking indicator
        showThinkingIndicator()
        updateStateIndicator("Processing...")
        
        // Hide follow-up container
        followUpContainer.visibility = View.GONE
    }
    
    // FSM Stream Callback implementations
    override fun onStateUpdate(stateUpdate: FSMStateUpdate) {
        Log.d(TAG, "State update: ${stateUpdate.currentNode}")
        
        stateUpdate.currentNode?.let { node ->
            currentSessionState.currentNode = node
            currentSessionState.previousNode = stateUpdate.previousNode
            
            val displayName = streamHandler.getStateDisplayName(node)
            updateStateIndicator(displayName)
        }
        
        // Update session ID if provided
        stateUpdate.toString().let { 
            // Extract session_id if present in the data
        }
    }
    
    override fun onMessage(message: String) {
        Log.d(TAG, "Received message: $message")
        
        runOnUiThread {
            // Stop thinking indicator when we receive first message
            stopThinkingIndicator()
            
            // WhatsApp-style: Accumulate all streaming responses into ONE message card
            if (currentSessionState.messages.isNotEmpty() && 
                !currentSessionState.messages.last().isUser) {
                
                // Continue building the current assistant response
                val currentMessage = currentSessionState.messages.last()
                val updatedText = if (currentMessage.text.isBlank()) {
                    message
                } else {
                    "${currentMessage.text}\n\n$message"
                }
                
                // Update the existing message card with accumulated content
                chatAdapter.updateLastMessage(updatedText)
                currentSessionState.messages[currentSessionState.messages.size - 1] = 
                    currentMessage.copy(text = updatedText)
            } else {
                // Start new assistant response card
                val assistantMessage = ChatMessage(
                    text = message,
                    isUser = false,
                    state = streamHandler.getStateDisplayName(currentSessionState.currentNode)
                )
                chatAdapter.addMessage(assistantMessage)
                currentSessionState.messages.add(assistantMessage)
            }
            scrollToBottom()
        }
    }
    
    override fun onFollowUpItems(items: List<String>) {
        Log.d(TAG, "Received follow-up items: $items")
        
        runOnUiThread {
            if (items.isNotEmpty()) {
                // Add follow-ups as light green clickable buttons within the message card (WhatsApp style)
                chatAdapter.addFollowUpToLastMessage(items)
                
                // Hide the separate follow-up container since we're using in-card buttons
                followUpContainer.visibility = View.GONE
            }
        }
    }
    
    override fun onError(error: String) {
        Log.e(TAG, "Stream error: $error")
        runOnUiThread {
            stopThinkingIndicator()
            showError(error)
            updateStateIndicator("Error")
        }
    }
    
    override fun onStreamComplete() {
        Log.d(TAG, "Stream completed")
        runOnUiThread {
            stopThinkingIndicator()
            if (currentSessionState.currentNode == "completed") {
                updateStateIndicator("Complete")
            }
        }
    }
    
    // UI Helper methods
    private fun updateStateIndicator(state: String) {
        runOnUiThread {
            stateIndicator.text = state
        }
    }
    
    private fun showFollowUpItems(items: List<String>) {
        followUpChipGroup.removeAllViews()
        
        items.forEach { item ->
            val chip = Chip(this).apply {
                text = item
                isClickable = true
                isCheckable = false
                
                // Apply light green styling as requested
                setChipBackgroundColorResource(R.color.followup_chip_background)
                setTextColor(resources.getColor(R.color.followup_chip_text, theme))
                chipStrokeColor = resources.getColorStateList(R.color.followup_chip_stroke, theme)
                chipStrokeWidth = 4f
                
                setOnClickListener {
                    // Change appearance
                    setChipBackgroundColorResource(R.color.followup_chip_clicked)
                    text = "✓ $item"
                    isClickable = false
                    
                    handleFollowUpClick(item)
                }
            }
            followUpChipGroup.addView(chip)
        }
        
        followUpContainer.visibility = View.VISIBLE
    }
    
    private fun scrollToBottom() {
        if (chatAdapter.itemCount > 0) {
            chatRecyclerView.smoothScrollToPosition(chatAdapter.itemCount - 1)
        }
    }
    
    private fun showError(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }
    
    /**
     * Show dedicated server configuration dialog
     */
    private fun showServerSettings() {
        try {
            val dialogView = layoutInflater.inflate(R.layout.dialog_server_url, null)
            val urlSpinner = dialogView.findViewById<Spinner>(R.id.urlSpinner)
            val customUrlInput = dialogView.findViewById<EditText>(R.id.customUrlInput)

            // Get available server options from ServerConfig
            val defaultUrls = ServerConfig.getDefaultUrls()
            val serverOptions = defaultUrls.map { it.first }

            // Setup spinner
            val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, serverOptions)
            adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
            urlSpinner.adapter = adapter

            // Get current server configuration and set selection
            val currentUrl = ServerConfig.getServerUrl(this)
            val currentIndex = defaultUrls.indexOfFirst { it.second == currentUrl }
                .takeIf { it >= 0 } ?: (defaultUrls.size - 1) // Default to "Custom URL" if not found

            urlSpinner.setSelection(currentIndex)

            // Show/hide custom URL input based on selection
            urlSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                    val isCustom = position == defaultUrls.size - 1 // Last option is "Custom URL"
                    customUrlInput.visibility = if (isCustom) View.VISIBLE else View.GONE
                    
                    if (isCustom) {
                        customUrlInput.setText(currentUrl)
                        customUrlInput.requestFocus()
                    }
                }
                override fun onNothingSelected(parent: AdapterView<*>?) {}
            }

            // Trigger initial selection to show/hide custom input
            urlSpinner.onItemSelectedListener?.onItemSelected(urlSpinner, null, currentIndex, 0)

            AlertDialog.Builder(this)
                .setTitle("🌐 Server Configuration")
                .setMessage("Select your server endpoint for the Sasya Chikitsa AI assistant:")
                .setView(dialogView)
                .setPositiveButton("Connect") { _, _ ->
                    val selectedPosition = urlSpinner.selectedItemPosition
                    val newUrl = if (selectedPosition == defaultUrls.size - 1) {
                        // Custom URL selected
                        var customUrl = customUrlInput.text.toString().trim()
                        if (customUrl.isNotEmpty() && !customUrl.endsWith("/")) {
                            customUrl += "/"
                        }
                        customUrl
                    } else {
                        // Preset URL selected
                        defaultUrls[selectedPosition].second
                    }

                    if (newUrl.isNotEmpty() && ServerConfig.isValidUrl(newUrl)) {
                        ServerConfig.setServerUrl(this, newUrl)
                        updateServerStatusDisplay()
                        
                        val serverName = if (selectedPosition == defaultUrls.size - 1) "Custom Server" else defaultUrls[selectedPosition].first
                        Toast.makeText(this, "✅ Connected to $serverName\n$newUrl", Toast.LENGTH_LONG).show()
                        
                        Log.d(TAG, "Server URL updated to: $newUrl")
                        
                        // Refresh FSM client with new URL
                        FSMRetrofitClient.initialize(this)
                    } else {
                        Toast.makeText(this, "❌ Please enter a valid URL (e.g., http://192.168.1.100:8080/)", Toast.LENGTH_LONG).show()
                    }
                }
                .setNeutralButton("Test Connection") { _, _ ->
                    val selectedPosition = urlSpinner.selectedItemPosition
                    val testUrl = if (selectedPosition == defaultUrls.size - 1) {
                        customUrlInput.text.toString().trim()
                    } else {
                        defaultUrls[selectedPosition].second
                    }
                    testServerConnection(testUrl)
                }
                .setNegativeButton("Cancel", null)
                .show()
                
        } catch (e: Exception) {
            Log.e(TAG, "Error showing server settings dialog: ${e.message}", e)
            Toast.makeText(this, "Failed to show server settings: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }
    
    /**
     * Test server connection
     */
    private fun testServerConnection(url: String) {
        if (url.isEmpty() || !ServerConfig.isValidUrl(url)) {
            Toast.makeText(this, "❌ Invalid URL format", Toast.LENGTH_SHORT).show()
            return
        }
        
        Toast.makeText(this, "🔄 Testing connection to $url...", Toast.LENGTH_SHORT).show()
        
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // Create a test request to check server connectivity
                val testUrl = if (!url.endsWith("/")) "$url/" else url
                val response = RetrofitClient.getApiService(testUrl).testConnection()
                
                withContext(Dispatchers.Main) {
                    if (response.isSuccessful) {
                        Toast.makeText(this@MainActivityFSM, "✅ Server connection successful!", Toast.LENGTH_LONG).show()
                    } else {
                        Toast.makeText(this@MainActivityFSM, "⚠️ Server responded but may not be fully ready (${response.code()})", Toast.LENGTH_LONG).show()
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@MainActivityFSM, "❌ Connection failed: ${e.message}", Toast.LENGTH_LONG).show()
                    Log.e(TAG, "Server connection test failed for $url", e)
                }
            }
        }
    }
    
    /**
     * Update the server status indicator in the header
     */
    private fun updateServerStatusDisplay() {
        val currentUrl = ServerConfig.getServerUrl(this)
        
        // Update status indicator based on server configuration
        when {
            currentUrl.contains("localhost") || currentUrl.contains("127.0.0.1") -> {
                stateIndicator.text = "●"
                stateIndicator.setTextColor(ContextCompat.getColor(this, android.R.color.holo_orange_dark))
                stateIndicator.contentDescription = "Local Development Server"
            }
            currentUrl.contains("production") -> {
                stateIndicator.text = "●"
                stateIndicator.setTextColor(ContextCompat.getColor(this, android.R.color.holo_green_light))
                stateIndicator.contentDescription = "Production Server"
            }
            currentUrl.contains("staging") -> {
                stateIndicator.text = "●"
                stateIndicator.setTextColor(ContextCompat.getColor(this, android.R.color.holo_blue_light))
                stateIndicator.contentDescription = "Staging Server"
            }
            else -> {
                stateIndicator.text = "●"
                stateIndicator.setTextColor(ContextCompat.getColor(this, android.R.color.holo_red_light))
                stateIndicator.contentDescription = "Custom Server"
            }
        }
    }
    
    // Utility methods
    private fun resizeBitmap(bitmap: Bitmap, maxSize: Int): Bitmap {
        val width = bitmap.width
        val height = bitmap.height
        
        if (width <= maxSize && height <= maxSize) {
            return bitmap
        }
        
        val ratio = minOf(maxSize.toFloat() / width, maxSize.toFloat() / height)
        val newWidth = (width * ratio).toInt()
        val newHeight = (height * ratio).toInt()
        
        return Bitmap.createScaledBitmap(bitmap, newWidth, newHeight, true)
    }
    
    private fun bitmapToBase64(bitmap: Bitmap): String {
        val byteArrayOutputStream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, 80, byteArrayOutputStream)
        val byteArray = byteArrayOutputStream.toByteArray()
        return Base64.encodeToString(byteArray, Base64.DEFAULT)
    }
    
    // Thinking Indicator Methods
    private fun showThinkingIndicator() {
        Log.d(TAG, "🤔 Showing thinking indicator")
        
        isThinking = true
        
        // Create thinking message
        thinkingMessage = ChatMessage(
            text = "🤖 Sasya Arogya Thinking",
            isUser = false,
            state = "Thinking"
        )
        
        chatAdapter.addMessage(thinkingMessage!!)
        currentSessionState.messages.add(thinkingMessage!!)
        scrollToBottom()
        
        // Start dot animation
        startThinkingAnimation()
    }
    
    private fun startThinkingAnimation() {
        var dotCount = 0
        
        thinkingAnimation = object : Runnable {
            override fun run() {
                if (!isThinking) return
                
                runOnUiThread {
                    val dots = ".".repeat((dotCount % 3) + 1)
                    val thinkingText = "🤖 Sasya Arogya Thinking$dots"
                    
                    // Update the thinking message
                    thinkingMessage?.let { message ->
                        val updatedMessage = message.copy(text = thinkingText)
                        val messageIndex = currentSessionState.messages.indexOf(message)
                        if (messageIndex != -1) {
                            currentSessionState.messages[messageIndex] = updatedMessage
                            chatAdapter.updateLastMessage(thinkingText)
                            thinkingMessage = updatedMessage
                        }
                    }
                    
                    dotCount++
                    
                    // Schedule next update if still thinking
                    if (isThinking) {
                        chatRecyclerView.postDelayed(thinkingAnimation!!, 500)
                    }
                }
            }
        }
        
        chatRecyclerView.postDelayed(thinkingAnimation!!, 500)
    }
    
    private fun stopThinkingIndicator() {
        if (!isThinking) return
        
        Log.d(TAG, "🛑 Stopping thinking indicator")
        
        isThinking = false
        
        // Cancel animation
        thinkingAnimation?.let { 
            chatRecyclerView.removeCallbacks(it)
            thinkingAnimation = null
        }
        
        // Remove thinking message from chat
        thinkingMessage?.let { message ->
            val messageIndex = currentSessionState.messages.indexOf(message)
            if (messageIndex != -1) {
                currentSessionState.messages.removeAt(messageIndex)
                // Recreate the entire adapter to remove the message
                val tempMessages = currentSessionState.messages.toList()
                chatAdapter.clear()
                tempMessages.forEach { chatAdapter.addMessage(it) }
                scrollToBottom()
            }
            thinkingMessage = null
        }
    }
    
    // Feedback handling methods
    private fun handleThumbsUpFeedback(chatMessage: ChatMessage) {
        Log.d(TAG, "👍 Thumbs up feedback for message: ${chatMessage.text.take(50)}...")
        
        // Record feedback using FeedbackManager
        val feedback = MessageFeedback(
            messageText = chatMessage.text,
            feedbackType = FeedbackType.THUMBS_UP,
            sessionId = currentSessionState.sessionId,
            userContext = "User gave positive feedback in FSM chat"
        )
        FeedbackManager.recordFeedback(feedback)
        
        runOnUiThread {
            Toast.makeText(this, "👍 Thanks for your feedback!", Toast.LENGTH_SHORT).show()
        }
    }
    
    private fun handleThumbsDownFeedback(chatMessage: ChatMessage) {
        Log.d(TAG, "👎 Thumbs down feedback for message: ${chatMessage.text.take(50)}...")
        
        // Record feedback using FeedbackManager
        val feedback = MessageFeedback(
            messageText = chatMessage.text,
            feedbackType = FeedbackType.THUMBS_DOWN,
            sessionId = currentSessionState.sessionId,
            userContext = "User gave negative feedback in FSM chat - needs improvement"
        )
        FeedbackManager.recordFeedback(feedback)
        
        runOnUiThread {
            Toast.makeText(this, "👎 Thanks for your feedback! We'll improve.", Toast.LENGTH_SHORT).show()
        }
    }
}
