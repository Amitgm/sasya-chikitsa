package com.example.sasya_chikitsa

import android.os.Bundle
import android.util.Log
import android.widget.LinearLayout
import android.widget.TextView
import androidx.activity.ComponentActivity

/**
 * Ultra-minimal MainActivity for crash debugging
 * This version has ZERO dependencies on custom resources, themes, or network classes
 */
class MainActivity_Minimal : ComponentActivity() {
    
    private val TAG = "MainActivity_Minimal"
    
    override fun onCreate(savedInstanceState: Bundle?) {
        Log.d(TAG, "🚀 Starting MINIMAL MainActivity onCreate()")
        
        try {
            super.onCreate(savedInstanceState)
            Log.d(TAG, "✅ super.onCreate() completed")
            
            // Create the simplest possible layout programmatically
            val layout = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(50, 50, 50, 50)
            }
            
            val textView = TextView(this).apply {
                text = "🌿 Minimal Sasya Chikitsa\n\nIf you can see this text, the basic Android Activity works!\n\nThis means the crash is likely in:\n- Custom themes/resources\n- Network initialization\n- Complex UI layout\n\nCheck the logs for details."
                textSize = 16f
                setPadding(20, 20, 20, 20)
            }
            
            layout.addView(textView)
            setContentView(layout)
            
            Log.d(TAG, "🎉 MINIMAL MainActivity onCreate() completed successfully!")
            
        } catch (e: Exception) {
            Log.e(TAG, "❌ CRASH in MINIMAL MainActivity: ${e.message}", e)
            Log.e(TAG, "❌ This means there's a fundamental Android issue!")
            throw e // Let it crash with full stack trace
        }
    }
}
