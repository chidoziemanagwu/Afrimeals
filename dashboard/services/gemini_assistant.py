# dashboard/services/gemini_assistant.py

from google import genai
from django.conf import settings
import logging
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GeminiAssistant:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = 'gemini-2.0-flash'

        self.base_context = """
        You are a Nigerian cuisine expert assistant for NaijaPlate, specializing in:
        1. Nigerian cooking and recipes
        2. UK-Nigerian fusion cuisine
        3. Finding African ingredients in the UK
        4. Cooking techniques and cultural context

        When providing responses:
        - Include specific store locations with full addresses
        - Reference cooking tutorial videos when relevant
        - Format responses clearly with sections and bullet points
        - Provide practical substitutes for hard-to-find ingredients
        """

    def chat(self, message: str) -> str:
        """Process a chat message and return a response"""
        try:
            prompt = f"{self.base_context}\n\nUser: {message}\nAssistant:"
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return self.format_response(response.text)
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}", exc_info=True)
            return "I apologize, but I encountered an error. Please try again."

    # dashboard/services/gemini_assistant.py

    def format_response(self, response_text: str) -> str:
        """Format the response with enhanced styling and links"""
        try:
            # Format section headers
            response_text = self._format_sections(response_text)
            
            # Format YouTube links
            response_text = self._format_youtube_links(response_text)
            
            # Format location/store references
            response_text = self._format_location_links(response_text)
            
            # Format lists and bullet points
            response_text = self._format_lists(response_text)
            
            # Format markdown-style text
            response_text = self._format_markdown(response_text)
            
            # Add final styling touches
            response_text = self._add_styling(response_text)
            
            return response_text
        except Exception as e:
            logger.error(f"Error formatting response: {str(e)}", exc_info=True)
            return response_text

    def _format_sections(self, text: str) -> str:
        """Format section headers with proper styling"""
        # Main title
        text = re.sub(
            r'^(NAIJAPLATE:.+?)(?=\n|$)',
            r'<div class="text-2xl font-bold text-green-700 mb-4">\1</div>',
            text,
            flags=re.MULTILINE
        )
        
        # Section headers (Roman numerals)
        text = re.sub(
            r'^(I+V?\.|[IVX]+\.)\s*([^\n]+)',
            r'<h3 class="text-xl font-semibold text-green-600 mt-6 mb-3">\1 \2</h3>',
            text,
            flags=re.MULTILINE
        )
        
        return text

    def _format_lists(self, text: str) -> str:
        """Format lists with proper indentation and styling"""
        # Main bullet points
        text = re.sub(
            r'^\s*\*\s*(.*?)$',
            r'<div class="ml-4 my-2">• \1</div>',
            text,
            flags=re.MULTILINE
        )
        
        # Nested bullet points
        text = re.sub(
            r'^\s{4}\*\s*(.*?)$',
            r'<div class="ml-8 my-1">◦ \1</div>',
            text,
            flags=re.MULTILINE
        )
        
        # Numbered lists
        text = re.sub(
            r'^\s*(\d+)\.\s*(.*?)$',
            r'<div class="ml-4 my-2">\1. \2</div>',
            text,
            flags=re.MULTILINE
        )
        
        return text

    def _format_youtube_links(self, text: str) -> str:
        """Convert YouTube references to clickable links with icons"""
        patterns = [
            # Full URLs with video title
            (r'Watch this video:\s*([^:]+):\s*(https?://(?:www\.)?youtube\.com/watch\?v=[a-zA-Z0-9_-]+)',
            r'<div class="flex items-center gap-2 my-2"><span class="text-red-600">▶</span>'
            r'<a href="\2" target="_blank" class="text-green-600 hover:text-green-800">\1</a></div>'),
            
            # Video references
            (r'Search on YouTube for "(.[^"]+)"',
            r'<div class="flex items-center gap-2 my-2"><span class="text-red-600">▶</span>'
            r'<a href="https://www.youtube.com/results?search_query=\1" target="_blank" '
            r'class="text-green-600 hover:text-green-800">Watch: \1</a></div>')
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
        return text

    def _format_location_links(self, text: str) -> str:
        """Convert location references to Google Maps links with icons"""
        patterns = [
            # Store with address format
            (r'([^:]+):\s*([^(]+)\s*\(([^)]+)\)',
            lambda m: f'<div class="flex items-center gap-2 my-2">📍 {m.group(1)}: '
            f'<a href="https://www.google.com/maps/search/?api=1&query={m.group(3)}" '
            f'target="_blank" class="text-green-600 hover:text-green-800">{m.group(2)} '
            f'({m.group(3)})</a></div>')
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
        return text

    def _format_markdown(self, text: str) -> str:
        """Convert markdown-style formatting to HTML with enhanced styling"""
        # Bold text
        text = re.sub(
            r'\*\*(.*?)\*\*',
            r'<strong class="font-semibold">\1</strong>',
            text
        )
        
        # Italic text
        text = re.sub(
            r'\*(.*?)\*',
            r'<em class="italic">\1</em>',
            text
        )
        
        # Important notes
        text = re.sub(
            r'(Note:|Important:|Tip:)\s*(.*?)(?=\n|$)',
            r'<div class="bg-green-50 p-3 rounded-lg my-2"><span class="font-semibold">\1</span> \2</div>',
            text,
            flags=re.MULTILINE
        )
        
        return text

    def _add_styling(self, text: str) -> str:
        """Add final styling touches"""
        # Wrap the entire response in a container
        text = f'<div class="space-y-4 text-gray-800">{text}</div>'
        
        # Add spacing between sections
        text = text.replace('\n\n', '</div><div class="my-4">')
        
        # Clean up any remaining newlines
        text = text.replace('\n', ' ')
        
        return text




    def get_recipe_recommendations(self, preferences: str) -> Dict[str, Any]:
        """Get recipe recommendations based on preferences"""
        try:
            prompt = f"Suggest Nigerian recipes based on these preferences: {preferences}"
            response = self.client.models.generate_content(
                model=self.model,
                contents=self.base_context + prompt
            )
            return {
                'recommendations': self.format_response(response.text),
                'status': 'success'
            }
        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}", exc_info=True)
            return {
                'message': str(e),
                'status': 'error'
            }

    def find_ingredient_substitutes(self, ingredient: str, location: str) -> Dict[str, Any]:
        """Find substitutes for ingredients"""
        try:
            prompt = f"Suggest substitutes for {ingredient} that can be found in {location} for Nigerian cooking"
            response = self.client.models.generate_content(
                model=self.model,
                contents=self.base_context + prompt
            )
            return {
                'substitutes': self.format_response(response.text),
                'status': 'success'
            }
        except Exception as e:
            logger.error(f"Error finding substitutes: {str(e)}", exc_info=True)
            return {
                'message': str(e),
                'status': 'error'
            }

    def get_cooking_tips(self, recipe_name: str) -> Dict[str, Any]:
        """Get cooking tips for a specific recipe"""
        try:
            prompt = f"Provide cooking tips for preparing {recipe_name} (Nigerian cuisine)"
            response = self.client.models.generate_content(
                model=self.model,
                contents=self.base_context + prompt
            )
            return {
                'tips': self.format_response(response.text),
                'status': 'success'
            }
        except Exception as e:
            logger.error(f"Error getting cooking tips: {str(e)}", exc_info=True)
            return {
                'message': str(e),
                'status': 'error'
            }