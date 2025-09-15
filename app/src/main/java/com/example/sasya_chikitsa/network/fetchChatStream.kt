package com.example.sasya_chikitsa.network

import com.example.sasya_chikitsa.network.request.ChatRequestData
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.BufferedReader
import java.io.InputStreamReader

// In your ViewModel or Repository
fun fetchChatStream(message: String, imageBase64: String?, sessionId: String?) {
    CoroutineScope(Dispatchers.IO).launch {
        try {
            val requestData = ChatRequestData(message, imageBase64, sessionId)

            // To request SSE explicitly via query param (optional, depends on your server logic)
            // val response = RetrofitClient.instance.chatStream(requestData, format = "sse")

            // Or rely on the Accept header (set in the ApiService interface)
            val response = RetrofitClient.instance.chatStream(requestData)


            if (response.isSuccessful) {
                val responseBody = response.body()
                if (responseBody != null) {
                    val inputStream = responseBody.byteStream()
                    val reader = BufferedReader(InputStreamReader(inputStream))
                    var line: String?
                    try {
                        while (withContext(Dispatchers.IO) { reader.readLine() }.also { line = it } != null) {
                            // Process each line (chunk) from the stream
                            // If it's SSE, parse the "data: " prefix
                            val currentLine = line ?: ""
                            if (currentLine.startsWith("data: ")) {
                                val actualData = currentLine.substringAfter("data: ").trim()
                                if (actualData == "[DONE]") {
                                    // Handle the end of the stream signal from your server
                                    println("Stream finished.")
                                    break
                                }
                                println("Received chunk: $actualData")
                                // Update your UI on the main thread
                                withContext(Dispatchers.Main) {
                                    // e.g., append actualData to a TextView
                                }
                            } else if (currentLine.isNotEmpty()) {
                                // If it's plain text and not SSE
                                println("Received chunk (plain text): $currentLine")
                                withContext(Dispatchers.Main) {
                                    // e.g., append currentLine to a TextView
                                }
                            }
                        }
                    } finally {
                        withContext(Dispatchers.IO) {
                            reader.close()
                            inputStream.close()
                        }
                        responseBody.close() // Important to close the response body
                    }
                } else {
                    println("Error: Empty response body")
                    // Handle error on the main thread
                }
            } else {
                val errorBody = response.errorBody()?.string()
                println("Error: ${response.code()} - ${errorBody ?: "Unknown error"}")
                // Handle error on the main thread
            }
        } catch (e: Exception) {
            println("Exception: ${e.message}")
            e.printStackTrace()
            // Handle exception on the main thread
        }
    }
}
