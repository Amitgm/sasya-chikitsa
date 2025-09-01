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
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.activity.ComponentActivity
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

class MainActivity : ComponentActivity() {
    private lateinit var imagePreview: ImageView
    private lateinit var uploadBtn: Button
    private lateinit var sendBtn: ImageButton
    private lateinit var messageInput: EditText

    private lateinit var responseTextView: TextView // TextView to show stream output

    private var selectedImageUri: Uri? = null

    private val PICK_IMAGE_REQUEST = 1
    private val TAG = "MainActivity" // For logging

    @SuppressLint("MissingInflatedId")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        imagePreview = findViewById(R.id.imagePreview)
        uploadBtn = findViewById(R.id.uploadBtn)
        sendBtn = findViewById(R.id.sendBtn)
        messageInput = findViewById(R.id.messageInput)
        responseTextView = findViewById(R.id.responseTextView)

        // Upload Button
        uploadBtn.setOnClickListener {
            val intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.type = "image/*"
            startActivityForResult(intent, PICK_IMAGE_REQUEST)
        }

        // Send Button
        sendBtn.setOnClickListener {
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

            // Fetch the stream
            fetchChatStreamFromServer(message, imageBase64, "session1")

            if (message.isNotEmpty()) {
                Toast.makeText(this, "Message sent: $message", Toast.LENGTH_SHORT).show()
            }

            // Clear the input field
            messageInput.text.clear()
            // Optionally clear the image preview and selectedImageUri if you want a one-time send
            // imagePreview.setImageURI(null)
            // selectedImageUri = null
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == PICK_IMAGE_REQUEST && resultCode == Activity.RESULT_OK) {
            val imageUri: Uri? = data?.data
            imagePreview.setImageURI(imageUri)
            //fetchChatStream()
            selectedImageUri = imageUri
            Toast.makeText(this, "Image selected.", Toast.LENGTH_SHORT).show()
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
        responseTextView.text = "Sending..." // Initial UI update
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

                        try {
                            while (withContext(Dispatchers.IO) { reader.readLine() }.also { line = it } != null) {
                                val currentLine = line ?: ""
                                Log.d(TAG, "Stream line: $currentLine")
                                if (currentLine.startsWith("data: ")) {
                                    val actualData = currentLine.substringAfter("data: ").trim()
                                    if (actualData == "[DONE]") {
                                        Log.d(TAG, "Stream finished by [DONE] signal.")
                                        withContext(Dispatchers.Main) {
                                            // Handle end of stream
                                            responseTextView.append("\n\n--- Stream End ---")
                                        }
                                        break
                                    }
                                    if (actualData.isNotEmpty()) {
                                        fullResponse.append(actualData)
                                        withContext(Dispatchers.Main) {
                                            // Append chunk to TextView. For continuous display:
                                            responseTextView.append(actualData)
                                        }
                                    }
                                } else if (currentLine.isNotEmpty()) {
                                    // Handle plain text chunks if not using SSE "data:" prefix
                                    fullResponse.append(currentLine).append("\n")
                                    withContext(Dispatchers.Main) {
                                        responseTextView.append(currentLine + "\n")
                                    }
                                }
                            }
                            if (line == null) { // Reached end of stream naturally
                                Log.d(TAG, "Stream finished naturally.")
                                withContext(Dispatchers.Main) {
                                    if (responseTextView.text.endsWith("Sending...")) {
                                        responseTextView.text = fullResponse.toString().ifEmpty { "Stream ended with no data." }
                                    } else if (fullResponse.isNotEmpty() && !responseTextView.text.contains("--- Stream End ---")) {
                                        // If [DONE] was not received but we got data
                                        responseTextView.append("\n\n--- Stream End (Connection Closed) ---")
                                    } else if (fullResponse.isEmpty() && !responseTextView.text.contains("--- Stream End ---")){
                                        responseTextView.append("\n\n--- Stream End (No data & Connection Closed) ---")
                                    }
                                }
                            }
                        } catch (e: IOException) {
                            Log.e(TAG, "Error reading stream", e)
                            withContext(Dispatchers.Main) {
                                responseTextView.append("\nError reading stream: ${e.message}")
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
                            responseTextView.text = "Error: Empty response body"
                        }
                    }
                } else {
                    val errorBody = response.errorBody()?.string() ?: "Unknown error"
                    Log.e(TAG, "Error: ${response.code()} - $errorBody")
                    withContext(Dispatchers.Main) {
                        responseTextView.text = "Error: ${response.code()} - $errorBody"
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Exception in fetchChatStreamFromServer", e)
                withContext(Dispatchers.Main) {
                    responseTextView.text = "Exception: ${e.message}"
                }
            }
        }
    }
}