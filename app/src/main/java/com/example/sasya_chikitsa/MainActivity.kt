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
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.BufferedReader
import java.io.InputStreamReader
import com.example.sasya_chikitsa.network.fetchChatStream
import com.example.sasya_chikitsa.ui.theme.Sasya_ChikitsaTheme
import org.json.JSONObject
import org.json.JSONArray
import org.json.JSONException

class MainActivity : ComponentActivity() {
    private lateinit var imagePreview: ImageView
    private lateinit var uploadBtn: ImageButton
    private lateinit var sendBtn: ImageButton
    private lateinit var messageInput: EditText
    private lateinit var removeImageBtn: ImageButton
    private lateinit var uploadSection: CardView
    private lateinit var imageFileName: TextView

    private lateinit var responseTextView: TextView // TextView to show stream output
    private lateinit var conversationScrollView: ScrollView // ScrollView for conversation

    private var selectedImageUri: Uri? = null
    private var conversationHistory = StringBuilder() // Store conversation history

    private val TAG = "MainActivity" // For logging
    
    // Modern Activity Result API for image selection
    private val imagePickerLauncher = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            try {
                showSelectedImage(uri)
                Toast.makeText(this, "Image selected.", Toast.LENGTH_SHORT).show()
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

        imagePreview = findViewById(R.id.imagePreview)
        uploadBtn = findViewById(R.id.uploadBtn)
        sendBtn = findViewById(R.id.sendBtn)
        messageInput = findViewById(R.id.messageInput)
        removeImageBtn = findViewById(R.id.removeImageBtn)
        uploadSection = findViewById(R.id.uploadSection)
        imageFileName = findViewById(R.id.imageFileName)
        responseTextView = findViewById(R.id.responseTextView)
        conversationScrollView = findViewById(R.id.conversationScrollView)
        
        // Initialize conversation history if empty
        if (conversationHistory.isEmpty()) {
            val welcomeMessage = "MAIN_ANSWER: Hi! I'm your plant health assistant. I can help diagnose plant diseases, provide care recommendations, and guide you through treatment procedures. Upload a photo or ask me about plant care to get started.\n\nACTION_ITEMS: Send Image | Give me watering schedule | Show fertilization procedure | Explain prevention methods"
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

            // Add user message to conversation history
            if (message.isNotEmpty()) {
                addUserMessage(message, currentImageUri != null)
                Toast.makeText(this, "Message sent: $message", Toast.LENGTH_SHORT).show()
            } else if (currentImageUri != null) {
                addUserMessage("Image", true)
                Toast.makeText(this, "Image sent", Toast.LENGTH_SHORT).show()
            }

            // Clear the input field
            messageInput.text.clear()

            // Fetch the stream
            fetchChatStreamFromServer(message, imageBase64, "session1")
            
                // Clear the image after sending (one-time use) - silently
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

    // Helper method to add assistant message to conversation
    private fun addAssistantMessage(message: String) {
        // Check if this is a structured response
        val structuredResponse = parseStructuredResponse(message)
        
        if (structuredResponse != null) {
            // Handle structured response with separate main answer and action items
            addStructuredAssistantMessage(structuredResponse.mainAnswer, structuredResponse.actionItems)
        } else {
            // Handle regular unstructured response
            val formattedMessage = formatMessageWithCollapsibleJson(message)
            val assistantMsg = "🤖 $formattedMessage\n\n"
            
            Log.d(TAG, "Adding assistant message to history. Current length: ${conversationHistory.length}")
            conversationHistory.append(assistantMsg)
            Log.d(TAG, "After adding assistant message. New length: ${conversationHistory.length}")
            
            updateConversationDisplay()
        }
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
        conversationHistory.append(assistantMsg)
        Log.d(TAG, "After adding structured assistant message. New length: ${conversationHistory.length}")
        
        updateConversationDisplay()
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

    // Helper method to make action items clickable and handle JSON collapsibles
    private fun makeActionItemsClickable() {
        val text = responseTextView.text.toString()
        
        val spannableString = SpannableString(text)
        var foundInteractiveElements = false
        
        // Handle action items (look for bullet points under "Quick Actions:")
        val actionItemPattern = "• [^\\n]+"
        val actionItemRegex = Regex(actionItemPattern)
        
        // Only look for action items that appear after "📋 Quick Actions:"
        val quickActionsIndex = text.indexOf("📋 Quick Actions:")
        if (quickActionsIndex != -1) {
            val actionSectionText = text.substring(quickActionsIndex)
            
            actionItemRegex.findAll(actionSectionText).forEach { match ->
                foundInteractiveElements = true
                val actionItemText = match.value
                val actualStartIndex = quickActionsIndex + match.range.first
                val actualEndIndex = quickActionsIndex + match.range.last
                
                val clickableSpan = object : ClickableSpan() {
                    override fun onClick(view: View) {
                        // Remove the bullet point and auto-fill the action in the message input
                        val cleanAction = actionItemText.replace("• ", "").trim()
                        messageInput.setText(cleanAction)
                        // Scroll to input field
                        conversationScrollView.post {
                            conversationScrollView.fullScroll(ScrollView.FOCUS_DOWN)
                        }
                        Toast.makeText(this@MainActivity, "Action added to input", Toast.LENGTH_SHORT).show()
                    }
                }
                
                spannableString.setSpan(
                    clickableSpan, 
                    actualStartIndex, 
                    actualEndIndex + 1, 
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                )
                
                // Make the action item blue, underlined, and bold
                spannableString.setSpan(
                    ForegroundColorSpan(ContextCompat.getColor(this, android.R.color.holo_blue_dark)),
                    actualStartIndex,
                    actualEndIndex + 1,
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                )
                
                spannableString.setSpan(
                    UnderlineSpan(),
                    actualStartIndex,
                    actualEndIndex + 1,
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                )
                
                spannableString.setSpan(
                    StyleSpan(Typeface.BOLD),
                    actualStartIndex,
                    actualEndIndex + 1,
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                )
            }
        }
        
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
                    
                    // Re-apply clickable spans
                    makeActionItemsClickable()
                    
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
            Log.d(TAG, "Updating conversation display. History length: ${conversationHistory.length}")
            responseTextView.text = conversationHistory.toString()
            Log.d(TAG, "Display updated. TextView length: ${responseTextView.text.length}")
            
            // Apply clickable spans AFTER setting text
            makeActionItemsClickable()
            
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
                            while (withContext(Dispatchers.IO) { reader.readLine() }.also { line = it } != null) {
                                val currentLine = line ?: ""
                                Log.d(TAG, "Stream line: $currentLine")
                                if (currentLine.startsWith("data: ")) {
                                    val actualData = currentLine.substringAfter("data: ").trim()
                                    if (actualData == "[DONE]") {
                                        Log.d(TAG, "Stream finished by [DONE] signal.")
                                        break
                                    }
                                    if (actualData.isNotEmpty()) {
                                        fullResponse.append(actualData)
                                        // Just log the chunk, keep typing indicator simple
                                        Log.d(TAG, "Received chunk: $actualData")
                                    }
                                } else if (currentLine.isNotEmpty()) {
                                    // Handle plain text chunks if not using SSE "data:" prefix
                                    fullResponse.append(currentLine).append("\n")
                                    Log.d(TAG, "Received line: $currentLine")
                                }
                            }
                            // Handle end of stream - add final response to conversation history
                                Log.d(TAG, "Stream finished naturally.")
                                withContext(Dispatchers.Main) {
                                if (fullResponse.isNotEmpty()) {
                                    addAssistantMessage(fullResponse.toString())
                                } else {
                                    addAssistantMessage("No response received from server.")
                                }
                            }
                        } catch (e: IOException) {
                            Log.e(TAG, "Error reading stream", e)
                            withContext(Dispatchers.Main) {
                                removeTypingIndicator()
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
                            removeTypingIndicator()
                            addAssistantMessage("⚠️ Error: Empty response body")
                        }
                    }
                } else {
                    val errorBody = response.errorBody()?.string() ?: "Unknown error"
                    Log.e(TAG, "Error: ${response.code()} - $errorBody")
                    withContext(Dispatchers.Main) {
                        removeTypingIndicator()
                        addAssistantMessage("⚠️ Error: ${response.code()} - $errorBody")
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Exception in fetchChatStreamFromServer", e)
                withContext(Dispatchers.Main) {
                    removeTypingIndicator()
                    addAssistantMessage("⚠️ Exception: ${e.message}")
                }
            }
        }
    }
}