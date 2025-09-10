"""
Base Component Class

Provides the common interface and functionality that all component handlers inherit from.
Ensures consistent behavior and error handling across all components.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ComponentResult:
    """Standard result format from component execution"""
    success: bool
    response: str
    session_data: Dict[str, Any]
    requires_user_input: bool
    next_suggestions: list
    error_message: Optional[str] = None

class BaseComponent(ABC):
    """
    Abstract base class for all workflow components.
    
    Each component implements one of the 8 core workflow steps and provides
    consistent interfaces for execution, error handling, and result formatting.
    """
    
    def __init__(self):
        self.component_name = self.__class__.__name__
        logger.debug(f"🔧 Initialized {self.component_name}")

    @abstractmethod
    async def execute(
        self,
        session_id: str,
        user_input: str,
        image_data: Optional[str],
        session_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ComponentResult:
        """
        Execute the component's main functionality.
        
        Args:
            session_id: Unique session identifier
            user_input: User's text input
            image_data: Base64 encoded image data if provided
            session_data: Current session data
            context: Additional context information
            
        Returns:
            ComponentResult with response and updated session data
        """
        pass

    async def validate_inputs(
        self,
        session_id: str,
        user_input: str,
        image_data: Optional[str],
        session_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Validate inputs before execution.
        
        Args:
            session_id: Session identifier
            user_input: User input
            image_data: Image data
            session_data: Session data
            context: Context data
            
        Returns:
            Error message if validation fails, None if valid
        """
        if not session_id or not isinstance(session_id, str):
            return "Invalid session ID provided"
        
        if user_input is None:
            user_input = ""
        
        return None  # Valid by default

    def create_success_result(
        self,
        response: str,
        session_data: Dict[str, Any],
        requires_user_input: bool = True,
        next_suggestions: list = None
    ) -> ComponentResult:
        """
        Create a successful ComponentResult.
        
        Args:
            response: Response message to user
            session_data: Updated session data
            requires_user_input: Whether user input is needed next
            next_suggestions: Suggested next actions
            
        Returns:
            ComponentResult indicating success
        """
        return ComponentResult(
            success=True,
            response=response,
            session_data=session_data or {},
            requires_user_input=requires_user_input,
            next_suggestions=next_suggestions or [],
            error_message=None
        )

    def create_error_result(
        self,
        error_message: str,
        response: str = None
    ) -> ComponentResult:
        """
        Create an error ComponentResult.
        
        Args:
            error_message: Error description
            response: User-friendly response message
            
        Returns:
            ComponentResult indicating error
        """
        return ComponentResult(
            success=False,
            response=response or "I encountered an error processing your request. Please try again.",
            session_data={},
            requires_user_input=True,
            next_suggestions=['retry', 'help'],
            error_message=error_message
        )

    async def handle_execution(
        self,
        session_id: str,
        user_input: str,
        image_data: Optional[str],
        session_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ComponentResult:
        """
        Wrapper method that handles validation and error catching.
        
        Args:
            session_id: Session identifier
            user_input: User input
            image_data: Image data
            session_data: Session data
            context: Context data
            
        Returns:
            ComponentResult from execution
        """
        try:
            # Validate inputs
            validation_error = await self.validate_inputs(
                session_id, user_input, image_data, session_data, context
            )
            if validation_error:
                logger.warning(f"❌ {self.component_name} validation failed: {validation_error}")
                return self.create_error_result(validation_error)

            # Log execution start
            logger.info(f"🚀 Executing {self.component_name} for session {session_id}")
            logger.debug(f"   User input: '{user_input[:100]}...'")
            logger.debug(f"   Has image: {bool(image_data)}")

            # Execute component
            result = await self.execute(session_id, user_input, image_data, session_data, context)

            # Log execution completion
            if result.success:
                logger.info(f"✅ {self.component_name} completed successfully")
                logger.debug(f"   Response: '{result.response[:100]}...'")
            else:
                logger.warning(f"⚠️ {self.component_name} completed with error: {result.error_message}")

            return result

        except Exception as e:
            error_msg = f"Unexpected error in {self.component_name}: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return self.create_error_result(error_msg)

    def format_response_with_context(
        self,
        main_response: str,
        context_info: Dict[str, Any] = None,
        suggestions: list = None
    ) -> str:
        """
        Format response with additional context and suggestions.
        
        Args:
            main_response: Primary response message
            context_info: Additional context to include
            suggestions: Suggested actions for user
            
        Returns:
            Formatted response string
        """
        formatted_response = main_response

        if context_info:
            context_parts = []
            for key, value in context_info.items():
                if value:
                    context_parts.append(f"{key}: {value}")
            
            if context_parts:
                formatted_response += f"\n\n📋 Context:\n" + "\n".join(f"• {part}" for part in context_parts)

        if suggestions:
            formatted_response += f"\n\n💡 What you can do next:\n" + "\n".join(f"• {suggestion}" for suggestion in suggestions)

        return formatted_response
