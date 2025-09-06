package com.example.sasya_chikitsa

import android.annotation.SuppressLint
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
import android.text.SpannableString
import android.text.Spanned
import android.text.method.LinkMovementMethod
import android.text.style.ClickableSpan
import android.text.style.ForegroundColorSpan
import android.text.style.UnderlineSpan
import android.text.style.StyleSpan
import android.graphics.Typeface
import android.view.View
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.cardview.widget.CardView
import androidx.core.content.ContextCompat

import com.example.sasya_chikitsa.network.request.ChatRequestData // Import data class
import com.example.sasya_chikitsa.network.RetrofitClient // Import Retrofit client
import com.example.sasya_chikitsa.config.ServerConfig
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.BufferedReader
import java.io.InputStreamReader
import java.util.UUID
import com.example.sasya_chikitsa.network.fetchChatStream
import com.example.sasya_chikitsa.ui.theme.Sasya_ChikitsaTheme
import org.json.JSONObject
import org.json.JSONArray
import org.json.JSONException
import android.text.SpannableStringBuilder
import android.app.AlertDialog
import android.widget.ArrayAdapter
import android.widget.Spinner

class MainActivity : ComponentActivity() {
    private lateinit var imagePreview: ImageView
    private lateinit var uploadBtn: ImageButton
    private lateinit var sendBtn: ImageButton
    private lateinit var messageInput: EditText
    private lateinit var removeImageBtn: ImageButton
    private lateinit var uploadSection: CardView
    private lateinit var imageFileName: TextView
    private lateinit var serverStatus: TextView
    private lateinit var settingsBtn: ImageButton

    private lateinit var responseTextView: TextView // TextView to show stream output
    private lateinit var conversationScrollView: ScrollView // ScrollView for conversation
    private lateinit var conversationContainer: LinearLayout // Container for individual messages

    private var selectedImageUri: Uri? = null
    private var conversationHistory = SpannableStringBuilder() // Store conversation history with formatting
    
    // Data class for conversation messages with images
    data class ConversationMessage(
        val text: String,
        val isUser: Boolean,
        val imageUri: Uri? = null,
        val timestamp: Long = System.currentTimeMillis()
    )
    
    // List to store conversation messages with images
    private val conversationMessages = mutableListOf<ConversationMessage>()

    private val TAG = "MainActivity" // For logging
    
    // Modern Activity Result API for image selection
    private val imagePickerLauncher = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            try {
                showSelectedImage(uri)
//                Toast.makeText(this, "Image selected.", Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                Log.e(TAG, "Error handling selected image", e)
                Toast.makeText(this, "Error processing image: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    @SuppressLint("MissingInflatedId")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        try {
        setContentView(R.layout.activity_main)

        // Initialize RetrofitClient with context for configurable server URL
        RetrofitClient.initialize(this)
        Log.d(TAG, "Server URL configured: ${ServerConfig.getServerUrl(this)}")

        imagePreview = findViewById(R.id.imagePreview)
        uploadBtn = findViewById(R.id.uploadBtn)
        sendBtn = findViewById(R.id.sendBtn)
        messageInput = findViewById(R.id.messageInput)
        removeImageBtn = findViewById(R.id.removeImageBtn)
        uploadSection = findViewById(R.id.uploadSection)
        imageFileName = findViewById(R.id.imageFileName)
        serverStatus = findViewById(R.id.serverStatus)
        settingsBtn = findViewById(R.id.settingsBtn)
        responseTextView = findViewById(R.id.responseTextView)
        conversationScrollView = findViewById(R.id.conversationScrollView)
        conversationContainer = findViewById(R.id.conversationContainer)
        
        // Update server status display
        updateServerStatusDisplay()
        
        // Initialize conversation history if empty
        if (conversationHistory.length == 0) {
            val welcomeMessage = "MAIN_ANSWER: Welcome to Sasya Chikitsa! I'm your AI plant health assistant. I can help diagnose plant diseases, provide care recommendations, and guide you through treatment procedures. Each app session starts fresh with a new conversation. Upload a photo or ask me about plant care to get started.\n\nACTION_ITEMS: Send Image | Give me watering schedule | Show fertilization procedure | Explain prevention methods"
            addAssistantMessage(welcomeMessage)
            
            // Add some test content to demonstrate action items
            val exampleMessage = "MAIN_ANSWER: Here are some common plant problems I can help with:\n• Leaf spots and discoloration\n• Wilting and drooping\n• Pest infestations\n• Nutrient deficiencies\n• Growth issues\n\nACTION_ITEMS: Identify plant disease from photo | Create plant care schedule | Get soil testing recommendations | Show organic treatment options"
            addAssistantMessage(exampleMessage)
        }
        } catch (e: Exception) {
            Log.e(TAG, "Error in onCreate", e)
            // Show error message and finish activity
            Toast.makeText(this, "Error initializing app: ${e.message}", Toast.LENGTH_LONG).show()
            finish()
            return
        }

        // Settings Button
        settingsBtn.setOnClickListener {
            showServerUrlDialog()
        }

        // Upload Button
        uploadBtn.setOnClickListener {
            imagePickerLauncher.launch("image/*")
        }

        // Remove Image Button
        removeImageBtn.setOnClickListener {
            clearSelectedImage()
        }

        // Send Button
        sendBtn.setOnClickListener {
            try {
            val message = messageInput.text.toString().trim()
            val currentImageUri = selectedImageUri // Use the stored URI
            if (message.isEmpty() && currentImageUri == null) {
                Toast.makeText(this, "Please enter a message or upload an image.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            // Convert image to Base64 if an image is selected
            var imageBase64: String? = null
            if (currentImageUri != null) {
                try {
                    imageBase64 = uriToBase64(currentImageUri)
                } catch (e: IOException) {
                    Log.e(TAG, "Error converting image to Base64", e)
                    Toast.makeText(this, "Error processing image.", Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }
            }

            // Add user message to conversation history with image
            if (message.isNotEmpty()) {
                addUserMessageWithImage(message, currentImageUri)
//                Toast.makeText(this, "Message sent: $message", Toast.LENGTH_SHORT).show()
            } else if (currentImageUri != null) {
                addUserMessageWithImage("Image", currentImageUri)
//                Toast.makeText(this, "Image sent", Toast.LENGTH_SHORT).show()
            }

            // Clear the input field
            messageInput.text.clear()

            // Fetch the stream
            fetchChatStreamFromServer(message, imageBase64, sessionId)
            
            // Clear the upload preview but keep image in conversation history
            if (currentImageUri != null) {
                clearSelectedImage(showToast = false)
            }
            } catch (e: Exception) {
                Log.e(TAG, "Error in send button logic", e)
                Toast.makeText(this, "Error sending message: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    // Helper method to show selected image
    private fun showSelectedImage(imageUri: Uri) {
        selectedImageUri = imageUri
            imagePreview.setImageURI(imageUri)
        imageFileName.text = "📷 Image attached"
        uploadSection.visibility = android.view.View.VISIBLE
        
        Log.d(TAG, "Image selected and upload section shown")
    }

    // Helper method to clear selected image
    private fun clearSelectedImage(showToast: Boolean = true) {
        selectedImageUri = null
        imagePreview.setImageURI(null)
        uploadSection.visibility = android.view.View.GONE
        
        if (showToast) {
            Toast.makeText(this, "Image removed", Toast.LENGTH_SHORT).show()
        }
        Log.d(TAG, "Image cleared and upload section hidden")
    }

    // Helper method to add user message to conversation
    private fun addUserMessage(message: String, hasImage: Boolean = false) {
        val imageIndicator = if (hasImage) " 📷" else ""
        val userMsg = "👤 $message$imageIndicator\n\n"
        
        Log.d(TAG, "Adding user message to history. Current length: ${conversationHistory.length}")
        conversationHistory.append(userMsg)
        Log.d(TAG, "After adding user message. New length: ${conversationHistory.length}")
        
        updateConversationDisplay()
    }
    
    // Enhanced helper method to add user message with image support
    private fun addUserMessageWithImage(message: String, imageUri: Uri?) {
        // Add to new conversation messages list
        val conversationMsg = ConversationMessage(
            text = message,
            isUser = true,
            imageUri = imageUri
        )
        conversationMessages.add(conversationMsg)
        
        // Also add to legacy text-based history for compatibility
        val imageIndicator = if (imageUri != null) " 📷" else ""
        val userMsg = "👤 $message$imageIndicator\n\n"
        conversationHistory.append(userMsg)
        
        Log.d(TAG, "Added user message with image. Total messages: ${conversationMessages.size}")
        updateConversationDisplay()
    }

    // Helper method to add assistant message to conversation
    private fun addAssistantMessage(message: String) {
        // Check if this is a structured response
        val structuredResponse = parseStructuredResponse(message)
        
        if (structuredResponse != null) {
            // Handle structured response with separate main answer and action items
            addStructuredAssistantMessage(structuredResponse.mainAnswer, structuredResponse.actionItems)
        } else {
            // Handle regular unstructured response
            addAssistantMessageToConversation(message)
        }
    }
    
    // Enhanced helper method to add assistant message to new conversation structure
    private fun addAssistantMessageToConversation(message: String) {
        val formattedMessage = formatMessageWithCollapsibleJson(message)
        
        // Add to new conversation messages list
        val conversationMsg = ConversationMessage(
            text = formattedMessage,
            isUser = false,
            imageUri = null
        )
        conversationMessages.add(conversationMsg)
        
        // Also add to legacy text-based history for compatibility
        val assistantMsg = "🤖 $formattedMessage\n\n"
        conversationHistory.append(assistantMsg)
        
        Log.d(TAG, "Added assistant message. Total messages: ${conversationMessages.size}")
        updateConversationDisplay()
    }
    
    // Helper method to create a user message view with optional image
    private fun createUserMessageView(message: ConversationMessage): View {
        val messageCard = androidx.cardview.widget.CardView(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                setMargins(0, 0, 0, 16)
            }
            radius = 20f
            cardElevation = 4f
            setCardBackgroundColor(android.graphics.Color.parseColor("#E3F2FD"))
        }
        
        val messageLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 16, 24, 16)
        }
        
        // Add text
        val textView = TextView(this).apply {
            text = "👤 ${message.text}"
            textSize = 16f
            setTextColor(android.graphics.Color.parseColor("#1565C0"))
            setLineSpacing(6f, 1f)
        }
        messageLayout.addView(textView)
        
        // Add image if present
        if (message.imageUri != null) {
            val imageView = ImageView(this).apply {
                layoutParams = LinearLayout.LayoutParams(
                    400, // width in pixels
                    300  // height in pixels
                ).apply {
                    setMargins(0, 16, 0, 0)
                }
                scaleType = ImageView.ScaleType.CENTER_CROP
                setImageURI(message.imageUri)
                
                // Add border and corner radius
                background = resources.getDrawable(R.drawable.modern_card_background, null)
                setPadding(8, 8, 8, 8)
            }
            messageLayout.addView(imageView)
        }
        
        messageCard.addView(messageLayout)
        return messageCard
    }
    
    // Helper method to create an assistant message view
    private fun createAssistantMessageView(message: ConversationMessage): View {
        val messageCard = androidx.cardview.widget.CardView(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                setMargins(0, 0, 0, 16)
            }
            radius = 20f
            cardElevation = 4f
            setCardBackgroundColor(android.graphics.Color.parseColor("#F3E5F5"))
        }
        
        val messageLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 16, 24, 16)
        }
        
        // Add text
        val textView = TextView(this).apply {
            text = "🤖 ${message.text}"
            textSize = 16f
            setTextColor(android.graphics.Color.parseColor("#2D3748"))
            setLineSpacing(6f, 1f)
            movementMethod = LinkMovementMethod.getInstance()
        }
        messageLayout.addView(textView)
        
        messageCard.addView(messageLayout)
        return messageCard
    }

    // Data class to hold parsed structured response
    data class StructuredResponse(
        val mainAnswer: String,
        val actionItems: List<String>
    )

    // Helper method to parse structured response format
    private fun parseStructuredResponse(message: String): StructuredResponse? {
        Log.d(TAG, "Parsing response for structure: $message")
        
        try {
            // Look for MAIN_ANSWER section
            val mainAnswerRegex = Regex(
                "MAIN_ANSWER:\\s*(.*?)(?=ACTION_ITEMS:|$)",
                setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.IGNORE_CASE)
            )
            val mainAnswerMatch = mainAnswerRegex.find(message)
            
            // Look for ACTION_ITEMS section
            val actionItemsRegex = Regex(
                "ACTION_ITEMS:\\s*(.*?)$",
                setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.IGNORE_CASE)
            )
            val actionItemsMatch = actionItemsRegex.find(message)
            
            if (mainAnswerMatch != null && actionItemsMatch != null) {
                val mainAnswer = mainAnswerMatch.groupValues[1].trim()
                val actionItemsText = actionItemsMatch.groupValues[1].trim()
                val actionItemsList = actionItemsText.split("|").map { it.trim() }.filter { it.isNotEmpty() }
                
                Log.d(TAG, "Structured response found - Main: '${mainAnswer.take(50)}...', Actions: $actionItemsList")
                return StructuredResponse(mainAnswer, actionItemsList)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing structured response", e)
        }
        
        Log.d(TAG, "No structured format found in response")
        return null
    }

    // Helper method to add structured assistant message with separate action items
    private fun addStructuredAssistantMessage(mainAnswer: String, actionItems: List<String>) {
        // Format main answer
        val formattedMainAnswer = formatMessageWithCollapsibleJson(mainAnswer)
        var assistantMsg = "🤖 $formattedMainAnswer"
        
        // Add action items as clickable elements if they exist
        if (actionItems.isNotEmpty()) {
            assistantMsg += "\n\n📋 Quick Actions:"
            actionItems.forEach { actionItem ->
                assistantMsg += "\n• $actionItem"
            }
        }
        
        assistantMsg += "\n\n"
        
        Log.d(TAG, "Adding structured assistant message to history. Current length: ${conversationHistory.length}")
        
        // Create a SpannableString for the new message and apply action item spans immediately
        val spannableMessage = SpannableString(assistantMsg)
        applyActionItemSpansToText(spannableMessage, actionItems)
        
        // Add to new conversation messages list (convert SpannableString to String)
        val conversationMsg = ConversationMessage(
            text = spannableMessage.toString(),
            isUser = false,
            imageUri = null
        )
        conversationMessages.add(conversationMsg)
        
        // Append to legacy conversation history
        conversationHistory.append(spannableMessage)
        Log.d(TAG, "After adding structured assistant message. New length: ${conversationHistory.length}")
        
        updateConversationDisplay()
    }

    // Helper method to apply action item spans to a specific text
    private fun applyActionItemSpansToText(spannableText: SpannableString, actionItems: List<String>) {
        if (actionItems.isEmpty()) return
        
        val text = spannableText.toString()
        val quickActionsIndex = text.indexOf("📋 Quick Actions:")
        
        if (quickActionsIndex != -1) {
            actionItems.forEach { actionItem ->
                val bulletItemText = "• $actionItem"
                val itemIndex = text.indexOf(bulletItemText, quickActionsIndex)
                
                if (itemIndex != -1) {
                    val itemEndIndex = itemIndex + bulletItemText.length
                    
                    // Create clickable span for this specific action item
                    val clickableSpan = object : ClickableSpan() {
                        override fun onClick(view: View) {
                            messageInput.setText(actionItem.trim())
                            conversationScrollView.post {
                                conversationScrollView.fullScroll(ScrollView.FOCUS_DOWN)
                            }
                            Toast.makeText(this@MainActivity, "Action added to input", Toast.LENGTH_SHORT).show()
                        }
                    }
                    
                    // Apply styling spans
                    spannableText.setSpan(clickableSpan, itemIndex, itemEndIndex, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                    spannableText.setSpan(
                        ForegroundColorSpan(ContextCompat.getColor(this, android.R.color.holo_blue_dark)),
                        itemIndex, itemEndIndex, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                    )
                    spannableText.setSpan(UnderlineSpan(), itemIndex, itemEndIndex, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                    spannableText.setSpan(StyleSpan(Typeface.BOLD), itemIndex, itemEndIndex, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                }
            }
        }
    }

    // Helper method to format messages with collapsible JSON and highlighted questions
    private fun formatMessageWithCollapsibleJson(message: String): String {
        // Detect JSON blocks in the message
        val jsonRegex = Regex("\\{[^{}]*(?:\\{[^{}]*\\}[^{}]*)*\\}", RegexOption.DOT_MATCHES_ALL)
        val arrayRegex = Regex("\\[[^\\[\\]]*(?:\\[[^\\[\\]]*\\][^\\[\\]]*)*\\]", RegexOption.DOT_MATCHES_ALL)
        
        var formattedMessage = message
        
        // Find and replace JSON objects
        jsonRegex.findAll(message).forEach { match ->
            val jsonString = match.value
            if (isValidJson(jsonString)) {
                val collapsibleJson = createCollapsibleJsonText(jsonString, "JSON Data")
                formattedMessage = formattedMessage.replace(jsonString, collapsibleJson)
            }
        }
        
        // Find and replace JSON arrays
        arrayRegex.findAll(formattedMessage).forEach { match ->
            val jsonString = match.value
            if (isValidJson(jsonString)) {
                val collapsibleJson = createCollapsibleJsonText(jsonString, "JSON Array")
                formattedMessage = formattedMessage.replace(jsonString, collapsibleJson)
            }
        }
        
        return formattedMessage
    }



    // Helper method to check if string is valid JSON
    private fun isValidJson(jsonString: String): Boolean {
        return try {
            when {
                jsonString.trim().startsWith("{") -> {
                    JSONObject(jsonString)
                    true
                }
                jsonString.trim().startsWith("[") -> {
                    JSONArray(jsonString)
                    true
                }
                else -> false
            }
        } catch (e: JSONException) {
            false
        }
    }

    // Helper method to create collapsible JSON text
    private fun createCollapsibleJsonText(jsonString: String, label: String): String {
        return "\n▼ $label (tap to expand)\n[COLLAPSED_JSON:$jsonString]\n"
    }

    // Helper method to handle JSON collapsibles (action items are now handled immediately when added)
    private fun makeJsonCollapsiblesClickable() {
        val text = responseTextView.text.toString()
        
        val spannableString = SpannableString(text)
        var foundInteractiveElements = false
        
        // Handle collapsible JSON blocks
        val collapsedJsonRegex = Regex("▼ ([^\\n]+) \\(tap to expand\\)\\n\\[COLLAPSED_JSON:([^\\]]+)\\]")
        collapsedJsonRegex.findAll(text).forEach { match ->
            foundInteractiveElements = true
            val fullMatch = match.value
            val label = match.groupValues[1]
            val jsonContent = match.groupValues[2]
            
            val clickableSpan = object : ClickableSpan() {
                override fun onClick(view: View) {
                    // Replace collapsed section with expanded JSON
                    val currentText = responseTextView.text.toString()
                    val prettyJson = try {
                        if (jsonContent.trim().startsWith("{")) {
                            JSONObject(jsonContent).toString(2)
                        } else {
                            JSONArray(jsonContent).toString(2)
                        }
                    } catch (e: JSONException) {
                        jsonContent
                    }
                    
                    val expandedText = "▲ $label (tap to collapse)\n```json\n$prettyJson\n```"
                    val updatedText = currentText.replace(fullMatch, expandedText)
                    
                    // Update both conversation history and display
                    conversationHistory.clear()
                    conversationHistory.append(updatedText)
                    responseTextView.text = updatedText
                    
                    // Re-apply clickable spans for collapse functionality
                    makeExpandedJsonCollapsible()
                    
                    Toast.makeText(this@MainActivity, "JSON expanded", Toast.LENGTH_SHORT).show()
                }
            }
            
            val labelStart = text.indexOf("▼ $label")
            val labelEnd = labelStart + "▼ $label (tap to expand)".length
            
            spannableString.setSpan(
                clickableSpan, 
                labelStart, 
                labelEnd, 
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
            )
            
            // Make the label blue and underlined to indicate it's clickable
            spannableString.setSpan(
                ForegroundColorSpan(ContextCompat.getColor(this, android.R.color.holo_blue_dark)),
                labelStart,
                labelEnd,
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
            )
            
            spannableString.setSpan(
                UnderlineSpan(),
                labelStart,
                labelEnd,
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
            )
            
            spannableString.setSpan(
                StyleSpan(Typeface.BOLD),
                labelStart,
                labelEnd,
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
            )
        }
        
        if (foundInteractiveElements) {
            responseTextView.text = spannableString
            responseTextView.movementMethod = LinkMovementMethod.getInstance()
        }
    }

    // Helper method to make expanded JSON collapsible
    private fun makeExpandedJsonCollapsible() {
        val text = responseTextView.text.toString()
        val expandedJsonRegex = Regex("▲ ([^\\n]+) \\(tap to collapse\\)\\n```json\\n([\\s\\S]*?)\\n```")
        
        expandedJsonRegex.findAll(text).forEach { match ->
            val fullMatch = match.value
            val label = match.groupValues[1]
            val jsonContent = match.groupValues[2]
            
            val spannableString = SpannableString(text)
            val clickableSpan = object : ClickableSpan() {
                override fun onClick(view: View) {
                    // Replace expanded section with collapsed JSON
                    val currentText = responseTextView.text.toString()
                    val collapsedText = "▼ $label (tap to expand)\n[COLLAPSED_JSON:${jsonContent.replace("\\s+".toRegex(), " ").trim()}]"
                    val updatedText = currentText.replace(fullMatch, collapsedText)
                    
                    // Update both conversation history and display
                    conversationHistory.clear()
                    conversationHistory.append(updatedText)
                    responseTextView.text = updatedText
                    
                    // Re-apply clickable spans for JSON
                    makeJsonCollapsiblesClickable()
                    
                    Toast.makeText(this@MainActivity, "JSON collapsed", Toast.LENGTH_SHORT).show()
                }
            }
            
            val labelStart = text.indexOf("▲ $label")
            val labelEnd = labelStart + "▲ $label (tap to collapse)".length
            
            spannableString.setSpan(
                clickableSpan, 
                labelStart, 
                labelEnd, 
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
            )
            
            // Make the label blue and underlined to indicate it's clickable
            spannableString.setSpan(
                ForegroundColorSpan(ContextCompat.getColor(this, android.R.color.holo_blue_dark)),
                labelStart,
                labelEnd,
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
            )
            
            spannableString.setSpan(
                UnderlineSpan(),
                labelStart,
                labelEnd,
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
            )
            
            spannableString.setSpan(
                StyleSpan(Typeface.BOLD),
                labelStart,
                labelEnd,
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
            )
            
            responseTextView.text = spannableString
            responseTextView.movementMethod = LinkMovementMethod.getInstance()
        }
    }

    // Helper method to update conversation display and scroll to bottom
    private fun updateConversationDisplay() {
        runOnUiThread {
            Log.d(TAG, "Updating conversation display. Messages: ${conversationMessages.size}")
            
            // Clear existing conversation views (except welcome message)
            if (conversationContainer.childCount > 1) {
                conversationContainer.removeViews(1, conversationContainer.childCount - 1)
            }
            
            // Add each conversation message as a separate view
            for (message in conversationMessages) {
                val messageView = if (message.isUser) {
                    createUserMessageView(message)
                } else {
                    createAssistantMessageView(message)
                }
                conversationContainer.addView(messageView)
            }
            
            // Only update legacy TextView if NOT currently streaming to avoid wiping streaming content
            if (!isCurrentlyStreaming) {
                responseTextView.text = conversationHistory
                responseTextView.movementMethod = LinkMovementMethod.getInstance()
                Log.d(TAG, "Updated legacy TextView (not streaming)")
            } else {
                Log.d(TAG, "Skipping TextView update - streaming in progress")
            }
            
            Log.d(TAG, "Display updated. Message views: ${conversationMessages.size}")
            
            // Force layout update
            responseTextView.requestLayout()
            
            // Enhanced scroll to bottom with proper timing for ScrollView
            conversationScrollView.post {
                conversationScrollView.postDelayed({
                    conversationScrollView.fullScroll(ScrollView.FOCUS_DOWN)
                }, 100)
                
                conversationScrollView.postDelayed({
                    conversationScrollView.smoothScrollTo(0, responseTextView.bottom)
                }, 200)
            }
        }
    }

    // Helper method to show typing indicator - ONLY appends, never reconstructs
    private fun showTypingIndicator() {
        runOnUiThread {
            // Simply append typing indicator to existing text without touching conversationHistory
            if (!responseTextView.text.toString().endsWith("🤖 typing...\n")) {
                responseTextView.append("🤖 typing...\n")
            }
            
            // Enhanced scroll to show typing indicator
            conversationScrollView.post {
                conversationScrollView.smoothScrollTo(0, responseTextView.bottom)
            }
            conversationScrollView.postDelayed({
                conversationScrollView.fullScroll(ScrollView.FOCUS_DOWN)
            }, 50)
        }
    }

    // Helper method to remove typing indicator - restores from conversationHistory
    private fun removeTypingIndicator() {
        runOnUiThread {
            Log.d(TAG, "Removing typing indicator. Restoring from history length: ${conversationHistory.length}")
            // Only restore from conversationHistory, never reconstruct
            responseTextView.text = conversationHistory.toString()
            Log.d(TAG, "Typing indicator removed. TextView length: ${responseTextView.text.length}")
        }
    }

    // Variables for streaming response handling
    private val streamingChunks = mutableListOf<String>()
    private var isCurrentlyStreaming = false
    
    // Generate unique session ID for this app instance
    private val sessionId: String = UUID.randomUUID().toString().also { 
        Log.i(TAG, "🆔 New session created: $it") 
    }

    /**
     * Add a streaming chunk immediately to the UI while preserving conversation history
     */
    private fun addStreamingChunk(chunk: String) {
        runOnUiThread {
            // 📊 ENHANCED LOGGING - Track streaming chunks
            Log.i(TAG, "🔥 STREAMING CHUNK RECEIVED:")
            Log.i(TAG, "   📦 Chunk content: '$chunk'")
            Log.i(TAG, "   📊 Chunk length: ${chunk.length} characters")
            Log.i(TAG, "   ⏰ Timestamp: ${System.currentTimeMillis()}")
            Log.i(TAG, "   🔄 Currently streaming: $isCurrentlyStreaming")
            Log.i(TAG, "   📈 Total chunks so far: ${streamingChunks.size}")
            
            if (!isCurrentlyStreaming) {
                // Starting new streaming - clear any typing indicator
                Log.i(TAG, "🚀 STARTING NEW STREAMING SESSION")
                removeTypingIndicator()
                streamingChunks.clear()
                isCurrentlyStreaming = true
                
                // Add assistant header for the streaming response
                responseTextView.append("🤖 Plant Analysis Progress:\n")
                Log.i(TAG, "   ✅ Added assistant header with progress indicator")
            }
            
            // Add the chunk to the display and track it
            streamingChunks.add(chunk)
            
            // 🔍 PIPE-SEPARATED ACTION ITEMS DETECTION
            if (isPipeSeperatedActionItems(chunk)) {
                Log.i(TAG, "🎯 DETECTED PIPE-SEPARATED ACTION ITEMS:")
                Log.i(TAG, "   📋 Raw action items: '$chunk'")
                
                // Parse and display action items with special formatting
                val actionItems = chunk.split("|").map { it.trim() }.filter { it.isNotEmpty() }
                Log.i(TAG, "   📊 Parsed ${actionItems.size} action items")
                
                // Add section header for action items
                responseTextView.append("\n📋 Recommended Actions:\n")
                
                // Display each action item with special formatting
                actionItems.forEachIndexed { index, actionItem ->
                    val actionBullet = "  ✓ $actionItem"
                    responseTextView.append("$actionBullet\n")
                    Log.i(TAG, "   ✓ Action ${index + 1}: '$actionItem'")
                }
                
                Log.i(TAG, "   🎨 Formatted as highlighted action items list")
                
            } else {
                // 🎯 REGULAR BULLET POINT FORMATTING - Each chunk as a bullet point
                val bulletPointChunk = "  • $chunk"
                responseTextView.append("$bulletPointChunk\n")
                Log.i(TAG, "   💡 Formatted as regular bullet point: '$bulletPointChunk'")
            }
            
            Log.i(TAG, "   📱 Added to responseTextView display")
            
            // Auto-scroll to show new content
            conversationScrollView.post {
                conversationScrollView.smoothScrollTo(0, responseTextView.bottom)
                Log.d(TAG, "   📜 Auto-scrolled to show new content")
            }
            
            Log.i(TAG, "✅ STREAMING CHUNK PROCESSED SUCCESSFULLY")
            Log.i(TAG, "   📊 Updated total chunks: ${streamingChunks.size}")
            Log.i(TAG, "   🎯 Display format: Bullet point list")
            Log.i(TAG, "   " + "=".repeat(50))
        }
    }

    /**
     * Finalize streaming response and add it to conversation history
     */
    private fun finalizeStreamingResponse() {
        runOnUiThread {
            // 📊 ENHANCED FINALIZATION LOGGING
            Log.i(TAG, "🏁 FINALIZING STREAMING RESPONSE:")
            Log.i(TAG, "   🔄 Currently streaming: $isCurrentlyStreaming")
            Log.i(TAG, "   📦 Chunks collected: ${streamingChunks.size}")
            
            if (isCurrentlyStreaming && streamingChunks.isNotEmpty()) {
                Log.i(TAG, "✅ PROCESSING COLLECTED STREAMING CHUNKS:")
                Log.i(TAG, "   📊 Total chunks to finalize: ${streamingChunks.size}")
                
                // Log all collected chunks
                streamingChunks.forEachIndexed { index, chunk ->
                    Log.i(TAG, "   📦 Chunk ${index + 1}: '$chunk'")
                }
                
                // Combine all chunks into the final message
                val fullStreamingResponse = streamingChunks.joinToString("\n")
                
                // IMPORTANT: Don't call addAssistantMessage() as it overwrites the streaming display!
                // Instead, add the streamed content directly to conversation history
                
                // Check if this is a structured response
                val structuredResponse = parseStructuredResponse(fullStreamingResponse)
                
                if (structuredResponse != null) {
                    // Handle structured response - format with action items
                    val formattedMainAnswer = formatMessageWithCollapsibleJson(structuredResponse.mainAnswer)
                    var assistantMsg = "🤖 $formattedMainAnswer"
                    
                    if (structuredResponse.actionItems.isNotEmpty()) {
                        assistantMsg += "\n\n📋 Quick Actions:"
                        structuredResponse.actionItems.forEach { actionItem ->
                            assistantMsg += "\n• $actionItem"
                        }
                    }
                    assistantMsg += "\n\n"
                    
                    // Add to new conversation messages list
                    val conversationMsg = ConversationMessage(
                        text = assistantMsg.removePrefix("🤖 "), // Remove emoji for clean display
                        isUser = false,
                        imageUri = null
                    )
                    conversationMessages.add(conversationMsg)
                    
                    // Create spannable and add to legacy history
                    val spannableMessage = SpannableString(assistantMsg)
                    applyActionItemSpansToText(spannableMessage, structuredResponse.actionItems)
                    conversationHistory.append(spannableMessage)
                } else {
                    // Handle regular response - just add streamed content to history
                    val formattedMessage = formatMessageWithCollapsibleJson(fullStreamingResponse)
                    val assistantMsg = "🤖 $formattedMessage\n\n"
                    
                    // Add to new conversation messages list
                    val conversationMsg = ConversationMessage(
                        text = formattedMessage,
                        isUser = false,
                        imageUri = null
                    )
                    conversationMessages.add(conversationMsg)
                    
                    // Add to legacy history
                    conversationHistory.append(assistantMsg)
                }
                
                Log.d(TAG, "Streaming content added to conversation history. New length: ${conversationHistory.length}")
                
                // Clean up streaming state
                val totalChunks = streamingChunks.size
                streamingChunks.clear()
                isCurrentlyStreaming = false
                
                // Now update conversation display with the new message
                updateConversationDisplay()
                
                Log.i(TAG, "🧹 STREAMING STATE CLEANUP COMPLETE:")
                Log.i(TAG, "   ✅ Processed ${totalChunks} chunks total")
                Log.i(TAG, "   🔄 Streaming state reset")
                Log.i(TAG, "   💾 Content added to conversation history")
                Log.i(TAG, "   📱 Conversation display updated with new message")
                Log.i(TAG, "   🎯 Bullet point formatting preserved")
                Log.i(TAG, "✅ STREAMING RESPONSE FINALIZED SUCCESSFULLY")
            } else {
                // Just remove typing indicator if no streaming happened
                Log.i(TAG, "⚠️  NO STREAMING CONTENT TO FINALIZE:")
                Log.i(TAG, "   🔄 Currently streaming: $isCurrentlyStreaming")
                Log.i(TAG, "   📦 Chunks available: ${streamingChunks.size}")
                Log.i(TAG, "   🔧 Just removing typing indicator...")
                removeTypingIndicator()
                Log.i(TAG, "   ✅ Typing indicator removed")
            }
        }
    }



    // Helper function to convert Uri to Base64 String
    @Throws(IOException::class)
    private fun uriToBase64(uri: Uri): String? {
        val inputStream = contentResolver.openInputStream(uri) ?: return null
        val bitmap = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            ImageDecoder.decodeBitmap(ImageDecoder.createSource(contentResolver, uri))
        } else {
            MediaStore.Images.Media.getBitmap(contentResolver, uri)
        }
        val byteArrayOutputStream = ByteArrayOutputStream()
        // Choose format and quality. PNG is lossless, JPEG allows quality adjustment.
        bitmap.compress(Bitmap.CompressFormat.JPEG, 80, byteArrayOutputStream) // Adjust quality as needed
        val byteArray = byteArrayOutputStream.toByteArray()
        inputStream.close()
        return Base64.encodeToString(byteArray, Base64.DEFAULT)
    }

    /**
     * Detect if a chunk contains pipe-separated action items
     */
    private fun isPipeSeperatedActionItems(chunk: String): Boolean {
        // 🔍 DETECTION LOGIC for pipe-separated action items
        Log.d(TAG, "🔍 Analyzing chunk for action items: '$chunk'")
        
        // Check if chunk contains pipes and looks like action items
        val containsPipes = chunk.contains("|")
        val hasMultipleParts = chunk.split("|").size > 1
        val partsLookLikeActions = chunk.split("|").all { part ->
            val trimmedPart = part.trim()
            trimmedPart.isNotEmpty() && 
            (trimmedPart.length > 10) && // Action items are usually descriptive
            (trimmedPart.contains(" ")) && // Should contain spaces (multiple words)
            !trimmedPart.startsWith("http") && // Not URLs
            !trimmedPart.contains("...")  // Not typical progress messages
        }
        
        val isActionItems = containsPipes && hasMultipleParts && partsLookLikeActions
        
        Log.d(TAG, "   📊 Analysis results:")
        Log.d(TAG, "      🔗 Contains pipes: $containsPipes")
        Log.d(TAG, "      📄 Multiple parts: $hasMultipleParts")
        Log.d(TAG, "      ✅ Parts look like actions: $partsLookLikeActions")
        Log.d(TAG, "      🎯 Final decision: ${if (isActionItems) "ACTION ITEMS" else "REGULAR CHUNK"}")
        
        return isActionItems
    }

    private fun fetchChatStreamFromServer(
        message: String,
        imageBase64: String?,
        sessionId: String?
        // text: String? // Add if required in ChatRequestData
    ) {
        showTypingIndicator() // Show typing indicator instead of overwriting
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val requestData = ChatRequestData(
                    message = message,
                    image_b64 = imageBase64,
                    session_id = sessionId
                    // text = null
                )

                val response = RetrofitClient.instance.chatStream(requestData)

                if (response.isSuccessful) {
                    val responseBody = response.body()
                    if (responseBody != null) {
                        val inputStream = responseBody.byteStream()
                        val reader = BufferedReader(InputStreamReader(inputStream, Charsets.UTF_8))
                        var line: String?
                        val fullResponse = StringBuilder()
                        removeTypingIndicator() // Remove typing indicator before streaming

                        try {
                            Log.i(TAG, "🌊 STARTING STREAM PROCESSING LOOP")
                            Log.i(TAG, "   📖 Reading lines from server stream...")
                            
                            var lineCount = 0
                            while (withContext(Dispatchers.IO) { reader.readLine() }.also { line = it } != null) {
                                val currentLine = line ?: ""
                                lineCount++
                                
                                // 📊 COMPREHENSIVE LINE LOGGING
                                Log.i(TAG, "📥 STREAM LINE #$lineCount RECEIVED:")
                                Log.i(TAG, "   🔗 Raw content: '$currentLine'")
                                Log.i(TAG, "   📏 Length: ${currentLine.length}")
                                Log.i(TAG, "   🔍 Is SSE format: ${currentLine.startsWith("data: ")}")
                                Log.i(TAG, "   ⏰ Processing timestamp: ${System.currentTimeMillis()}")
                                if (currentLine.startsWith("data: ")) {
                                    val actualData = currentLine.substringAfter("data: ").trim()
                                    
                                    // 📊 ENHANCED SERVER-SENT EVENT LOGGING
                                    Log.i(TAG, "📡 SSE DATA RECEIVED:")
                                    Log.i(TAG, "   🔗 Raw line: '$currentLine'")
                                    Log.i(TAG, "   📦 Extracted data: '$actualData'")
                                    Log.i(TAG, "   📏 Data length: ${actualData.length}")
                                    
                                    if (actualData == "[DONE]") {
                                        Log.i(TAG, "🏁 STREAM COMPLETION SIGNAL RECEIVED")
                                        Log.i(TAG, "   ✅ Stream finished by [DONE] signal")
                                        break
                                    }
                                    if (actualData.isNotEmpty()) {
                                        fullResponse.append(actualData).append("\n")
                                        
                                        Log.i(TAG, "🚀 PROCESSING CHUNK FOR DISPLAY:")
                                        Log.i(TAG, "   📤 About to send to addStreamingChunk()")
                                        Log.i(TAG, "   🎯 Chunk will be formatted as bullet point")
                                        
                                        // Display each chunk immediately on UI thread
                                        withContext(Dispatchers.Main) {
                                            addStreamingChunk(actualData)
                                        }
                                        
                                        Log.i(TAG, "✅ CHUNK PROCESSING COMPLETE")
                                        Log.i(TAG, "   📱 Chunk sent to UI thread for display")
                                    } else {
                                        Log.w(TAG, "⚠️  Empty actualData received, skipping display")
                                    }
                                } else if (currentLine.isNotEmpty()) {
                                    // Handle plain text chunks if not using SSE "data:" prefix
                                    Log.i(TAG, "📄 PLAIN TEXT CHUNK RECEIVED:")
                                    Log.i(TAG, "   🔗 Raw line: '$currentLine'")
                                    Log.i(TAG, "   📏 Line length: ${currentLine.length}")
                                    
                                    fullResponse.append(currentLine).append("\n")
                                    
                                    Log.i(TAG, "🚀 PROCESSING PLAIN TEXT CHUNK:")
                                    Log.i(TAG, "   📤 About to send to addStreamingChunk()")
                                    
                                    // Display each line immediately on UI thread
                                    withContext(Dispatchers.Main) {
                                        addStreamingChunk(currentLine)
                                    }
                                    
                                    Log.i(TAG, "✅ PLAIN TEXT CHUNK PROCESSED")
                                }
                            }
                            
                            // Handle end of stream - finalize streaming response
                            Log.i(TAG, "🏁 STREAM PROCESSING COMPLETED")
                            Log.i(TAG, "   📊 Total lines processed: $lineCount")
                            Log.i(TAG, "   ✅ Stream finished naturally")
                            Log.i(TAG, "   🔄 About to finalize streaming response...")
                            
                                withContext(Dispatchers.Main) {
                                finalizeStreamingResponse()
                            }
                            
                            Log.i(TAG, "✅ STREAM FINALIZATION COMPLETE")
                        } catch (e: IOException) {
                            Log.e(TAG, "Error reading stream", e)
                            withContext(Dispatchers.Main) {
                                finalizeStreamingResponse()
                                addAssistantMessage("⚠️ Error reading stream: ${e.message}")
                            }
                        } finally {
                            withContext(Dispatchers.IO) {
                                reader.close()
                                inputStream.close()
                            }
                            responseBody.close()
                        }
                    } else {
                        Log.e(TAG, "Error: Empty response body")
                        withContext(Dispatchers.Main) {
                            finalizeStreamingResponse()
                            addAssistantMessage("⚠️ Error: Empty response body")
                        }
                    }
                } else {
                    val errorBody = response.errorBody()?.string() ?: "Unknown error"
                    Log.e(TAG, "Error: ${response.code()} - $errorBody")
                    withContext(Dispatchers.Main) {
                        finalizeStreamingResponse()
                        addAssistantMessage("⚠️ Error: ${response.code()} - $errorBody")
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Exception in fetchChatStreamFromServer", e)
                withContext(Dispatchers.Main) {
                    finalizeStreamingResponse()
                    addAssistantMessage("⚠️ Exception: ${e.message}")
                }
            }
        }
    }
    

    
    private fun updateServerStatusDisplay() {
        val currentUrl = ServerConfig.getServerUrl(this)
        val defaultUrls = ServerConfig.getDefaultUrls()
        
        // Find friendly name for current URL
        val friendlyName = defaultUrls.find { it.second == currentUrl }?.first ?: "Custom"
        val shortUrl = when {
            currentUrl.contains("10.0.2.2") -> "Emulator"
            currentUrl.contains("localhost") -> "Localhost"
            currentUrl.contains("192.168") -> "Local Network"
            currentUrl.contains("staging") -> "Staging"
            currentUrl.contains("production") || currentUrl.contains("prod") -> "Production"
            else -> currentUrl.replace("http://", "").replace("https://", "").take(20)
        }
        
        serverStatus.text = "📡 Server: $shortUrl"
        Log.d(TAG, "Server status updated: $friendlyName - $currentUrl")
    }
    
    private fun showServerUrlDialog() {
        val defaultUrls = ServerConfig.getDefaultUrls()
        val currentUrl = ServerConfig.getServerUrl(this)
        
        val builder = AlertDialog.Builder(this)
        builder.setTitle("Configure Server URL")
        
        // Create a custom layout with spinner and input field
        val layout = layoutInflater.inflate(R.layout.dialog_server_url, null)
        val spinner = layout.findViewById<Spinner>(R.id.urlSpinner)
        val customUrlInput = layout.findViewById<EditText>(R.id.customUrlInput)
        
        // Setup spinner with default URLs
        val urlLabels = defaultUrls.map { it.first }
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, urlLabels)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        spinner.adapter = adapter
        
        // Pre-select current URL if it matches a default
        val currentIndex = defaultUrls.indexOfFirst { it.second == currentUrl }
        if (currentIndex != -1) {
            spinner.setSelection(currentIndex)
        } else {
            // Select "Custom" and populate input field
            spinner.setSelection(defaultUrls.size - 1)
            customUrlInput.setText(currentUrl)
        }
        
        // Show/hide custom input based on selection
        spinner.setOnItemSelectedListener(object : android.widget.AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: android.view.View?, position: Int, id: Long) {
                customUrlInput.visibility = if (position == defaultUrls.size - 1) android.view.View.VISIBLE else android.view.View.GONE
            }
            override fun onNothingSelected(parent: android.widget.AdapterView<*>?) {}
        })
        
        builder.setView(layout)
        builder.setPositiveButton("Save") { _, _ ->
            val selectedIndex = spinner.selectedItemPosition
            val newUrl = if (selectedIndex == defaultUrls.size - 1) {
                // Custom URL
                customUrlInput.text.toString().trim().let { url ->
                    if (!url.startsWith("http://") && !url.startsWith("https://")) {
                        "http://$url"
                    } else {
                        url
                    }
                }
            } else {
                defaultUrls[selectedIndex].second
            }
            
            if (newUrl.isNotEmpty() && ServerConfig.isValidUrl(newUrl)) {
                ServerConfig.setServerUrl(this, newUrl)
                RetrofitClient.refreshInstance() // Force recreate with new URL
                updateServerStatusDisplay() // Update the status display
                Toast.makeText(this, "Server URL updated to: $newUrl", Toast.LENGTH_LONG).show()
                Log.d(TAG, "Server URL updated to: $newUrl")
            } else {
                Toast.makeText(this, "Please enter a valid URL (e.g., http://192.168.1.100:8080/)", Toast.LENGTH_LONG).show()
            }
        }
        builder.setNegativeButton("Cancel", null)
        
        val dialog = builder.create()
        dialog.show()
    }
}