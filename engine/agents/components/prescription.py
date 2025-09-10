"""
Component 4: Prescription via RAG

Agentic RAG retrieves best-matched treatments based on disease, using scientific guidelines and relevant documents.
Prescription (pesticide/medicine) is tailored to crop, disease, and user profile.

Enhanced with multi-plant ChromaDB collections for optimized performance.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from .base_component import BaseComponent, ComponentResult

logger = logging.getLogger(__name__)

class PrescriptionComponent(BaseComponent):
    """
    Generates RAG-based, personalized treatment prescriptions.
    
    This component:
    - Uses RAG system to find relevant treatment guidelines
    - Tailors recommendations to crop, disease, location, and season
    - Provides multiple treatment options (chemical, organic, preventive)
    - Includes dosage, timing, and application instructions
    - Considers user preferences and constraints
    """
    
    def __init__(self):
        super().__init__()
        # Import enhanced RAG system
        from rag.rag_with_ollama import ollama_rag
        # Initialize enhanced RAG system with pre-loaded collections for multiple plant types
        logger.info("🔧 Initializing Enhanced Multi-Plant RAG System for prescription component...")
        self.rag_system = ollama_rag(
            llm_name="llama3.1:8b",
            temperature=0.1,
            embedding_model="intfloat/multilingual-e5-large-instruct",
            # Initialize common plant collections
            collections_to_init=['Tomato', 'Potato', 'Rice', 'Wheat', 'Corn', 'Cotton']
        )
        logger.info(f"✅ RAG system initialized with collections: {self.rag_system.get_available_collections()}")

    async def execute(
        self,
        session_id: str,
        user_input: str,
        image_data: Optional[str],
        session_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ComponentResult:
        """
        Generate personalized prescription using RAG system.
        """
        logger.info(f"🔬 Starting prescription generation for session {session_id}")
        
        user_profile = session_data.get('user_profile', {})
        diagnosis_results = session_data.get('diagnosis_results', {})
        
        logger.debug(f"User profile: {user_profile}")
        logger.debug(f"Diagnosis results: {diagnosis_results}")
        
        if not diagnosis_results.get('disease_name'):
            logger.warning("No disease classification available for prescription")
            return self.create_error_result(
                "No disease classification available for prescription generation",
                "I need a disease diagnosis first. Please upload an image for classification."
            )
        
        try:
            # Generate RAG-based prescription
            logger.info("💊 Generating RAG-based prescription...")
            prescription = await self._generate_rag_prescription(
                diagnosis_results, user_profile, user_input
            )
            
            # Format prescription for user
            logger.info("📝 Formatting prescription response...")
            response = self._format_prescription_response(prescription, user_profile)
            
            session_update = {
                'prescription': prescription,
                'prescription_generated': True
            }
            
            logger.info("✅ Prescription generation completed successfully")
            
            return self.create_success_result(
                response=response,
                session_data=session_update,
                requires_user_input=False,  # Allow continuous workflow to proceed
                next_suggestions=['gather_constraints', 'proceed_to_vendors', 'ask_questions']
            )
            
        except Exception as e:
            logger.error(f"❌ Error in prescription generation: {e}")
            return self.create_error_result(
                f"Failed to generate prescription: {str(e)}",
                "I encountered an issue generating your prescription. Please try again or contact support."
            )

    async def _generate_rag_prescription(
        self,
        classification_results: Dict[str, Any],
        user_profile: Dict[str, Any],
        user_query: str
    ) -> Dict[str, Any]:
        """Generate prescription using enhanced multi-plant RAG system."""
        
        disease_name = classification_results.get('disease_name', '')
        crop_type = user_profile.get('crop_type', 'general')
        location = user_profile.get('location', '')
        season = user_profile.get('season', '')
        
        logger.debug(f"🔍 Generating prescription for: disease={disease_name}, crop={crop_type}, location={location}, season={season}")
        
        # Build comprehensive RAG query with contextual information
        rag_query = f"Treatment prescription for {disease_name}"
        if crop_type and crop_type != 'general':
            rag_query += f" in {crop_type} crop"
        if location:
            rag_query += f" in {location} region"
        if season:
            rag_query += f" during {season} season"
        
        # Add specific treatment request
        rag_query += ". Include chemical treatments, organic options, prevention methods, dosage, and timing."
        
        logger.debug(f"📝 RAG query: {rag_query}")
        
        try:
            # Determine plant type for collection selection
            plant_collection = self._map_crop_to_collection(crop_type)
            logger.debug(f"🎯 Using plant collection: {plant_collection}")
            
            # Query enhanced RAG system with plant-specific collection
            rag_response = await asyncio.to_thread(
                self.rag_system.run_query, 
                rag_query, 
                plant_collection
            )
            
            logger.debug(f"✅ RAG response received: {len(rag_response)} characters")
            
            # Structure the response
            return {
                'disease': disease_name,
                'crop': crop_type,
                'location': location,
                'season': season,
                'treatment_plan': rag_response,
                'confidence': classification_results.get('confidence', 0.0),
                'source': 'enhanced_rag_system',
                'collection_used': plant_collection,
                'available_collections': self.rag_system.get_available_collections()
            }
            
        except Exception as e:
            logger.error(f"Enhanced RAG prescription generation failed: {e}")
            logger.info("🔄 Attempting fallback prescription generation...")
            return self._get_fallback_prescription(disease_name, crop_type)

    def _map_crop_to_collection(self, crop_type: str) -> Optional[str]:
        """
        Map crop type to ChromaDB collection name.
        
        Args:
            crop_type: The crop type from user profile
            
        Returns:
            Collection name or None for auto-detection
        """
        if not crop_type or crop_type == 'general':
            return None  # Let RAG system auto-detect
            
        # Normalize crop type
        crop_lower = crop_type.lower()
        
        # Map to available collections
        crop_collection_map = {
            'tomato': 'Tomato',
            'tomatoes': 'Tomato',
            'potato': 'Potato', 
            'potatoes': 'Potato',
            'rice': 'Rice',
            'wheat': 'Wheat',
            'corn': 'Corn',
            'maize': 'Corn',
            'cotton': 'Cotton'
        }
        
        mapped_collection = crop_collection_map.get(crop_lower)
        if mapped_collection and mapped_collection in self.rag_system.get_available_collections():
            logger.debug(f"🎯 Mapped {crop_type} → {mapped_collection}")
            return mapped_collection
        
        logger.debug(f"🔄 No specific collection for {crop_type}, using auto-detection")
        return None  # Use auto-detection based on query content

    def _get_fallback_prescription(self, disease_name: str, crop_type: str) -> Dict[str, Any]:
        """Provide basic prescription as fallback."""
        
        basic_treatments = {
            'early_blight': {
                'chemical': 'Copper sulfate spray (2g/L), weekly application',
                'organic': 'Neem oil spray + proper plant spacing',
                'prevention': 'Crop rotation, drip irrigation'
            },
            'late_blight': {
                'chemical': 'Mancozeb fungicide (2.5g/L), bi-weekly',
                'organic': 'Bordeaux mixture + resistant varieties',
                'prevention': 'Avoid overhead watering, good ventilation'
            }
        }
        
        treatment = basic_treatments.get(disease_name.lower(), {
            'chemical': 'Broad spectrum fungicide as per label',
            'organic': 'Neem oil and biological controls',
            'prevention': 'Cultural practices and plant hygiene'
        })
        
        return {
            'disease': disease_name,
            'crop': crop_type,
            'treatment_options': treatment,
            'source': 'fallback'
        }

    def _format_prescription_response(
        self,
        prescription: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> str:
        """Format prescription into user-friendly response."""
        
        response = f"💊 **Treatment Prescription for {prescription.get('disease', 'Unknown Disease')}**\n\n"
        
        if prescription.get('treatment_plan'):
            response += f"**Recommended Treatment:**\n{prescription['treatment_plan']}\n\n"
        
        if prescription.get('treatment_options'):
            options = prescription['treatment_options']
            response += "**Treatment Options:**\n"
            for option_type, treatment in options.items():
                response += f"• **{option_type.title()}:** {treatment}\n"
        
        response += "\n🏪 Would you like me to suggest local vendors for these treatments?"
        
        return response
