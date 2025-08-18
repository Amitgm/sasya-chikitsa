package com.example.sasya_chikitsa

import android.os.Bundle
import androidx.activity.ComponentActivity
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.Toast
import android.content.Intent
import android.net.Uri
import android.provider.MediaStore
import android.app.Activity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import com.example.sasya_chikitsa.ui.theme.Sasya_ChikitsaTheme

class MainActivity : ComponentActivity() {
    private lateinit var imageView: ImageView
    private lateinit var promptInput: EditText
    private var imageUri: Uri? = null

    private val PICK_IMAGE = 100   // request code for gallery intent

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // ✅ Connects this Activity to res/layout/activity_main.xml
        setContentView(R.layout.activity_main)

        // Link UI elements
        imageView = findViewById(R.id.imageView)
        promptInput = findViewById(R.id.promptInput)
        val selectImageBtn: Button = findViewById(R.id.selectImageBtn)
        val submitBtn: Button = findViewById(R.id.submitBtn)

        // ✅ Handle Select Image button
        selectImageBtn.setOnClickListener {
            openGallery()
        }

        // ✅ Handle Submit button
        submitBtn.setOnClickListener {
            val prompt = promptInput.text.toString()
            if (imageUri != null && prompt.isNotEmpty()) {
                Toast.makeText(this, "Image + Prompt ready!", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(this, "Please select image & enter prompt.", Toast.LENGTH_SHORT).show()
            }
        }
    }

    // Open gallery to pick image
    private fun openGallery() {
        val intent = Intent(Intent.ACTION_PICK, MediaStore.Images.Media.EXTERNAL_CONTENT_URI)
        startActivityForResult(intent, PICK_IMAGE)
    }

    // Handle result from gallery
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode == PICK_IMAGE && resultCode == Activity.RESULT_OK) {
            imageUri = data?.data
            imageView.setImageURI(imageUri)  // ✅ show selected image
        }
    }
}