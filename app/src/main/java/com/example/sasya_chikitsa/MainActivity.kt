package com.example.sasya_chikitsa

import android.annotation.SuppressLint
import android.os.Bundle
import androidx.activity.ComponentActivity
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.ImageButton
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
    private lateinit var imagePreview: ImageView
    private lateinit var uploadBtn: Button
    private lateinit var sendBtn: ImageButton
    private lateinit var messageInput: EditText



    private val PICK_IMAGE_REQUEST = 1

    @SuppressLint("MissingInflatedId")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        imagePreview = findViewById(R.id.imagePreview)
        uploadBtn = findViewById(R.id.uploadBtn)
        sendBtn = findViewById(R.id.sendBtn)
        messageInput = findViewById(R.id.messageInput)

        // Upload Button
        uploadBtn.setOnClickListener {
            val intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.type = "image/*"
            startActivityForResult(intent, PICK_IMAGE_REQUEST)
        }

        // Send Button
        sendBtn.setOnClickListener {
            val message = messageInput.text.toString()
            if (message.isNotEmpty()) {
                // TODO: handle sending message
                messageInput.text.clear()
            }
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == PICK_IMAGE_REQUEST && resultCode == Activity.RESULT_OK) {
            val imageUri: Uri? = data?.data
            imagePreview.setImageURI(imageUri)
        }
    }
}