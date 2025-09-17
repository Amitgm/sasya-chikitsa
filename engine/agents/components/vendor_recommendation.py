"""
Component 6: Vendor Recommendation Branch

Agent asks if vendor suggestions are needed for prescribed items.
If yes, recommended vendors are retrieved and displayed; includes product details and local availability.
"""

import logging
from typing import Dict, Any, Optional
from .base_component import BaseComponent, ComponentResult

logger = logging.getLogger(__name__)

class VendorRecommendationComponent(BaseComponent):
    """Handles vendor recommendation and supplier suggestions."""
    
    async def execute(self, session_id: str, user_input: str, image_data: Optional[str], 
                     session_data: Dict[str, Any], context: Dict[str, Any]) -> ComponentResult:
        
        user_profile = session_data.get('user_profile', {})
        prescription = session_data.get('prescription', {})
        location = user_profile.get('location', '')
        
        if not location:
            response = "I'd need your location to suggest local vendors. Could you share your district/state?"
            return self.create_success_result(
                response=response,
                session_data={},
                requires_user_input=True,
                next_suggestions=['provide_location', 'skip_vendors']
            )
        
        # Generate vendor recommendations
        vendors = self._generate_vendor_recommendations(location, prescription)
        
        response = f"🏪 **Local Vendor Recommendations for {location}:**\n\n"
        for vendor in vendors:
            response += f"• **{vendor['name']}** - {vendor['distance']} away\n"
            response += f"  Contact: {vendor.get('contact', 'N/A')}\n"
            response += f"  Speciality: {vendor.get('speciality', 'General agricultural supplies')}\n\n"
        
        response += "💰 **Estimated Cost:** ₹150-300 for complete treatment\n"
        response += "🚚 **Online Options:** Also available on AgriKart, BigHaat"
        
        return self.create_success_result(
            response=response,
            session_data={'vendor_recommendations': vendors},
            requires_user_input=True,
            next_suggestions=['contact_vendor', 'more_options', 'complete_consultation']
        )
    
    def _generate_vendor_recommendations(self, location: str, prescription: Dict[str, Any]) -> list:
        """Generate mock vendor recommendations based on location."""
        # This would integrate with actual vendor database
        return [
            {'name': 'Green Valley Agri Store', 'distance': '2.5 km', 'contact': '+91-98765-43210'},
            {'name': 'Farmers Choice Centre', 'distance': '5.1 km', 'contact': '+91-98765-43211'},
            {'name': 'Agro Tech Solutions', 'distance': '8.3 km', 'contact': '+91-98765-43212'}
        ]
