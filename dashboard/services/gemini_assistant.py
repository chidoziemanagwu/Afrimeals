# dashboard/services/gemini_assistant.py

from google import genai
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class GeminiAssistant:
    def __init__(self):
        # Initialize Gemini client with your API key
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Base context for Nigerian cuisine
        self.base_context = """
        You are a Nigerian cuisine expert assistant for NaijaPlate, specializing in:
        1. Nigerian cooking and recipes
        2. UK-Nigerian fusion cuisine
        3. Finding African ingredients in the UK
        4. Cooking techniques and cultural context
        """

    async def chat(self, message: str) -> str:
        """Process a chat message and return a response"""
        try:
            prompt = f"{self.base_context}\n\nUser: {message}\nAssistant:"
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}", exc_info=True)
            return "I apologize, but I encountered an error. Please try again."

    async def get_recipe_recommendations(self, preferences):
        prompt = f"Suggest Nigerian recipes based on these preferences: {preferences}"
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=self.base_context + prompt
            )
            return {
                'recommendations': response.text,
                'status': 'success'
            }
        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}", exc_info=True)
            return {
                'message': f"Error getting recommendations: {str(e)}",
                'status': 'error'
            }

    async def find_ingredient_substitutes(self, ingredient, location):
        prompt = f"Suggest substitutes for {ingredient} that can be found in {location} for Nigerian cooking"
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=self.base_context + prompt
            )
            return {
                'substitutes': response.text,
                'status': 'success'
            }
        except Exception as e:
            logger.error(f"Error finding substitutes: {str(e)}", exc_info=True)
            return {
                'message': f"Error finding substitutes: {str(e)}",
                'status': 'error'
            }

    async def get_cooking_tips(self, recipe_name):
        prompt = f"Provide cooking tips for preparing {recipe_name} (Nigerian cuisine)"
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=self.base_context + prompt
            )
            return {
                'tips': response.text,
                'status': 'success'
            }
        except Exception as e:
            logger.error(f"Error getting cooking tips: {str(e)}", exc_info=True)
            return {
                'message': f"Error getting cooking tips: {str(e)}",
                'status': 'error'
            }