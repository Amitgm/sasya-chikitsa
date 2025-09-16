package com.example.sasya_chikitsa.fsm

import android.graphics.drawable.GradientDrawable
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.example.sasya_chikitsa.R
import com.google.android.material.chip.Chip
import com.google.android.material.chip.ChipGroup
import java.text.SimpleDateFormat
import java.util.*

/**
 * RecyclerView Adapter for chat messages with follow-up buttons and feedback
 */
class ChatAdapter(
    private val onFollowUpClick: (String) -> Unit,
    private val onThumbsUpClick: (ChatMessage) -> Unit = {},
    private val onThumbsDownClick: (ChatMessage) -> Unit = {}
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {
    
    private val messages = mutableListOf<ChatMessage>()
    private val timeFormatter = SimpleDateFormat("HH:mm", Locale.getDefault())
    
    companion object {
        private const val VIEW_TYPE_USER = 1
        private const val VIEW_TYPE_ASSISTANT = 2
    }
    
    override fun getItemViewType(position: Int): Int {
        return if (messages[position].isUser) VIEW_TYPE_USER else VIEW_TYPE_ASSISTANT
    }
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val inflater = LayoutInflater.from(parent.context)
        return when (viewType) {
            VIEW_TYPE_USER -> {
                val view = inflater.inflate(R.layout.item_chat_user, parent, false)
                UserMessageViewHolder(view)
            }
            VIEW_TYPE_ASSISTANT -> {
                val view = inflater.inflate(R.layout.item_chat_assistant, parent, false)
                AssistantMessageViewHolder(view, onFollowUpClick, onThumbsUpClick, onThumbsDownClick)
            }
            else -> throw IllegalArgumentException("Invalid view type")
        }
    }
    
    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val message = messages[position]
        when (holder) {
            is UserMessageViewHolder -> holder.bind(message)
            is AssistantMessageViewHolder -> holder.bind(message)
        }
    }
    
    override fun getItemCount(): Int = messages.size
    
    fun addMessage(message: ChatMessage) {
        messages.add(message)
        notifyItemInserted(messages.size - 1)
    }
    
    fun updateLastMessage(text: String) {
        if (messages.isNotEmpty()) {
            val lastMessage = messages[messages.size - 1]
            if (!lastMessage.isUser) {
                messages[messages.size - 1] = lastMessage.copy(text = text)
                notifyItemChanged(messages.size - 1)
            }
        }
    }
    
    fun addFollowUpToLastMessage(followUpItems: List<String>) {
        if (messages.isNotEmpty()) {
            val lastMessage = messages[messages.size - 1]
            if (!lastMessage.isUser) {
                messages[messages.size - 1] = lastMessage.copy(followUpItems = followUpItems)
                notifyItemChanged(messages.size - 1)
            }
        }
    }
    
    fun clear() {
        messages.clear()
        notifyDataSetChanged()
    }
    
    /**
     * ViewHolder for user messages
     */
    inner class UserMessageViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val messageText: TextView = itemView.findViewById(R.id.messageText)
        private val messageTime: TextView = itemView.findViewById(R.id.messageTime)
        private val messageImage: ImageView = itemView.findViewById(R.id.messageImage)
        
        fun bind(message: ChatMessage) {
            messageText.text = message.text
            messageTime.text = timeFormatter.format(Date(message.timestamp))
            
            // Show image if present
            if (message.imageUri != null) {
                messageImage.visibility = View.VISIBLE
                Glide.with(itemView.context)
                    .load(message.imageUri)
                    .into(messageImage)
            } else {
                messageImage.visibility = View.GONE
            }
        }
    }
    
    /**
     * ViewHolder for assistant messages with follow-up buttons and feedback
     */
    inner class AssistantMessageViewHolder(
        itemView: View, 
        private val onFollowUpClick: (String) -> Unit,
        private val onThumbsUpClick: (ChatMessage) -> Unit,
        private val onThumbsDownClick: (ChatMessage) -> Unit
    ) : RecyclerView.ViewHolder(itemView) {
        
        private val messageText: TextView = itemView.findViewById(R.id.messageText)
        private val messageTime: TextView = itemView.findViewById(R.id.messageTime)
        private val stateIndicator: TextView = itemView.findViewById(R.id.stateIndicator)
        private val followUpContainer: LinearLayout = itemView.findViewById(R.id.followUpContainer)
        private val followUpChipGroup: ChipGroup = itemView.findViewById(R.id.followUpChipGroup)
        private val thumbsUpButton: ImageButton = itemView.findViewById(R.id.thumbsUpButton)
        private val thumbsDownButton: ImageButton = itemView.findViewById(R.id.thumbsDownButton)
        
        fun bind(message: ChatMessage) {
            messageText.text = message.text
            messageTime.text = timeFormatter.format(Date(message.timestamp))
            
            // Show state indicator if present
            if (message.state != null) {
                stateIndicator.visibility = View.VISIBLE
                stateIndicator.text = message.state
                
                // Color based on state
                val backgroundColor = when (message.state.lowercase()) {
                    "ready" -> ContextCompat.getColor(itemView.context, R.color.state_ready)
                    "analyzing plant..." -> ContextCompat.getColor(itemView.context, R.color.state_processing)
                    "diagnosis complete" -> ContextCompat.getColor(itemView.context, R.color.state_complete)
                    else -> ContextCompat.getColor(itemView.context, R.color.state_default)
                }
                
                val drawable = stateIndicator.background as? GradientDrawable
                drawable?.setColor(backgroundColor)
            } else {
                stateIndicator.visibility = View.GONE
            }
            
            // Add follow-up buttons
            if (message.followUpItems != null && message.followUpItems.isNotEmpty()) {
                followUpContainer.visibility = View.VISIBLE
                followUpChipGroup.removeAllViews()
                
                message.followUpItems.forEach { followUpText ->
                    val chip = Chip(itemView.context).apply {
                        text = followUpText
                        isClickable = true
                        isCheckable = false
                        
                        // Light green styling as requested
                        chipBackgroundColor = ContextCompat.getColorStateList(
                            itemView.context, R.color.followup_chip_background
                        )
                        setTextColor(ContextCompat.getColor(itemView.context, R.color.followup_chip_text))
                        chipStrokeColor = ContextCompat.getColorStateList(
                            itemView.context, R.color.followup_chip_stroke
                        )
                        chipStrokeWidth = 2f
                        
                        setOnClickListener {
                            // Change appearance to show clicked state
                            chipBackgroundColor = ContextCompat.getColorStateList(
                                itemView.context, R.color.followup_chip_clicked
                            )
                            isClickable = false
                            text = "✓ $followUpText"
                            
                            // Trigger callback
                            onFollowUpClick(followUpText)
                        }
                    }
                    followUpChipGroup.addView(chip)
                }
            } else {
                followUpContainer.visibility = View.GONE
            }
            
            // Set up feedback button listeners
            thumbsUpButton.setOnClickListener {
                // Visual feedback - highlight the clicked button
                thumbsUpButton.setColorFilter(
                    ContextCompat.getColor(itemView.context, R.color.thumbs_up_selected)
                )
                thumbsDownButton.setColorFilter(
                    ContextCompat.getColor(itemView.context, R.color.thumbs_default)
                )
                
                // Record feedback
                val feedback = com.example.sasya_chikitsa.models.MessageFeedback(
                    messageText = message.text,
                    feedbackType = com.example.sasya_chikitsa.models.FeedbackType.THUMBS_UP,
                    userContext = "Positive feedback from chat"
                )
                com.example.sasya_chikitsa.models.FeedbackManager.recordFeedback(feedback)
                
                // Trigger callback
                onThumbsUpClick(message)
            }
            
            thumbsDownButton.setOnClickListener {
                // Visual feedback - highlight the clicked button  
                thumbsDownButton.setColorFilter(
                    ContextCompat.getColor(itemView.context, R.color.thumbs_down_selected)
                )
                thumbsUpButton.setColorFilter(
                    ContextCompat.getColor(itemView.context, R.color.thumbs_default)
                )
                
                // Record feedback
                val feedback = com.example.sasya_chikitsa.models.MessageFeedback(
                    messageText = message.text,
                    feedbackType = com.example.sasya_chikitsa.models.FeedbackType.THUMBS_DOWN,
                    userContext = "Negative feedback from chat - needs improvement"
                )
                com.example.sasya_chikitsa.models.FeedbackManager.recordFeedback(feedback)
                
                // Trigger callback
                onThumbsDownClick(message)
            }
        }
    }
}
