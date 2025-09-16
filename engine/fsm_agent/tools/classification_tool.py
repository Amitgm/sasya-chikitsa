"""
Classification Tool for LangGraph Workflow

This tool wraps the CNN classification functionality for use in the LangGraph workflow.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import base64
import io
import sys
import os

# Add the parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from engine.ml.cnn_attn_classifier_improved import CNNWithAttentionClassifier

logger = logging.getLogger(__name__)


class ClassificationInput(BaseModel):
    """Input schema for classification tool"""
    image_b64: str = Field(description="Base64 encoded image of the plant leaf")
    plant_type: Optional[str] = Field(default=None, description="Type of plant (optional)")
    location: Optional[str] = Field(default=None, description="Location for context (optional)")
    season: Optional[str] = Field(default=None, description="Season for context (optional)")
    growth_stage: Optional[str] = Field(default=None, description="Growth stage (optional)")


class ClassificationTool(BaseTool):
    """
    Tool for classifying plant diseases from leaf images
    """
    name: str = "plant_disease_classifier"
    description: str = "Classifies plant diseases from leaf images using CNN with attention mechanism"
    args_schema: type[BaseModel] = ClassificationInput
    
    # Declare the classifier field properly
    classifier: Optional[Any] = Field(default=None, exclude=True)
    
    def __init__(self, **data):
        super().__init__(**data)
        self._load_classifier()
    
    def _load_classifier(self):
        """Load the CNN classifier"""
        try:
            # Initialize classifier (no parameters needed - uses hardcoded paths)
            self.classifier = CNNWithAttentionClassifier()
            logger.info("CNN classifier loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load CNN classifier: {str(e)}")
            self.classifier = None
    
    async def _arun(self, **kwargs) -> Dict[str, Any]:
        """Async implementation"""
        return await asyncio.to_thread(self._run, **kwargs)
    
    def _run(self, **kwargs) -> Dict[str, Any]:
        """
        Run the classification tool
        
        Returns:
            Dictionary containing classification results or error
        """
        try:
            # Validate input
            if not kwargs.get("image_b64"):
                return {"error": "No image provided"}
            
            if not self.classifier:
                return {"error": "CNN classifier not available"}
            
            # Run classification (it's a generator that yields status messages)
            try:
                classification_generator = self.classifier.predict_leaf_classification(
                    image_bytes=kwargs["image_b64"],
                    input_text=f"Plant: {kwargs.get('plant_type', 'unknown')}, Location: {kwargs.get('location', 'unknown')}, Season: {kwargs.get('season', 'unknown')}"
                )
                
                # Consume all yielded messages to get final result and extract attention overlay
                messages = []
                attention_overlay_b64 = None
                
                for message in classification_generator:
                    messages.append(message)
                    
                    # Check for attention overlay data
                    if "ATTENTION_OVERLAY_BASE64:" in message:
                        attention_overlay_b64 = message.split("ATTENTION_OVERLAY_BASE64:")[1].strip()
                        logger.info("Attention overlay captured successfully")
                
                # Parse the final diagnosis message
                if messages:
                    final_message = messages[-1]  # Last message should contain diagnosis
                    
                    # Extract disease name and confidence from final message
                    # Format: "Diagnosis Complete! Health Status: {disease} with confidence {confidence}"
                    if "Health Status:" in final_message and "confidence" in final_message:
                        import re
                        match = re.search(r'Health Status: (.+?) with confidence ([0-9.]+)', final_message)
                        if match:
                            disease_name = match.group(1).strip()
                            confidence = float(match.group(2))
                            
                            formatted_result = {
                                "disease_name": disease_name,
                                "confidence": confidence,
                                "severity": "Unknown",  # Not provided by current model
                                "description": f"Detected {disease_name} with {confidence:.2%} confidence",
                                "attention_overlay": attention_overlay_b64,  # Include captured attention overlay
                                "raw_predictions": messages,  # Include all status messages
                                "plant_context": {
                                    "plant_type": kwargs.get("plant_type"),
                                    "location": kwargs.get("location"),
                                    "season": kwargs.get("season"),
                                    "growth_stage": kwargs.get("growth_stage")
                                }
                            }
                            
                            logger.info(f"Classification successful: {disease_name} ({confidence:.2f}) with attention overlay")
                            return formatted_result
                
                return {"error": "Classification failed - could not parse diagnosis result"}
                
            except Exception as e:
                return {"error": f"Classification failed: {str(e)}"}
                
        except Exception as e:
            error_msg = f"Classification error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg}


# Async wrapper for compatibility
async def run_classification_tool(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Async wrapper for the classification tool
    
    Args:
        input_data: Dictionary containing image_b64 and optional context
    
    Returns:
        Classification results or error
    """
    tool = ClassificationTool()
    return await tool._arun(**input_data)
