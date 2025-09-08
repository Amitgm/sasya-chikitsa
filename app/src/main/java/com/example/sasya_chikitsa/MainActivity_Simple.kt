package com.example.sasya_chikitsa

import android.os.Bundle
import android.util.Log
import android.widget.TextView
import android.widget.Toast
import androidx.activity.ComponentActivity
import com.example.sasya_chikitsa.config.ServerConfig
import com.example.sasya_chikitsa.network.RetrofitClient

/**
 * Simplified MainActivity for crash debugging
 * This version only includes basic functionality to isolate crash causes
 */
class MainActivity_Simple : ComponentActivity() {
    
    private val TAG = "MainActivity_Simple"
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        Log.d(TAG, "🚀 Starting MainActivity_Simple onCreate()")
        
        try {
            Log.d(TAG, "✅ Step 1: Calling super.onCreate()")
            // super.onCreate() already called above
            
            Log.d(TAG, "✅ Step 2: Setting content view")
            setContentView(createSimpleLayout())
            
            Log.d(TAG, "✅ Step 3: Initializing RetrofitClient")
            RetrofitClient.initialize(this)
            
            Log.d(TAG, "✅ Step 4: Getting server URL")
            val serverUrl = ServerConfig.getServerUrl(this)
            Log.d(TAG, "Server URL: $serverUrl")
            
            Log.d(TAG, "✅ Step 5: Finding TextView")
            val textView = findViewById<TextView>(android.R.id.text1)
            
            Log.d(TAG, "✅ Step 6: Setting text")
            textView?.text = "🌿 Sasya Chikitsa - Simple Mode\nServer: $serverUrl\n\nIf you see this, basic initialization works!"
            
            Log.d(TAG, "✅ Step 7: Showing toast")
            Toast.makeText(this, "Simple MainActivity loaded successfully!", Toast.LENGTH_LONG).show()
            
            Log.d(TAG, "🎉 MainActivity_Simple onCreate() completed successfully!")
            
        } catch (e: Exception) {
            Log.e(TAG, "❌ CRASH in MainActivity_Simple onCreate(): ${e.message}", e)
            Log.e(TAG, "❌ Stack trace: ${e.stackTraceToString()}")
            
            try {
                Toast.makeText(this, "Error in simple mode: ${e.message}", Toast.LENGTH_LONG).show()
            } catch (toastError: Exception) {
                Log.e(TAG, "❌ Even Toast failed: ${toastError.message}")
            }
            
            // Don't finish() - let it crash naturally so we can see the full stack trace
            throw e
        }
    }
    
    private fun createSimpleLayout(): TextView {
        return TextView(this).apply {
            id = android.R.id.text1
            text = "Loading..."
            textSize = 16f
            setPadding(32, 32, 32, 32)
        }
    }
}
