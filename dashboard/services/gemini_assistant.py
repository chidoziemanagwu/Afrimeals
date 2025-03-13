# dashboard/services/gemini_assistant.py

import google.generativeai as genai
from django.conf import settings
from typing import Dict, List, Optional
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

class GeminiAssistant:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
        self.geolocator = Nominatim(user_agent="naijaplate")

        # Base context for Nigerian cuisine
        self.base_context = """
        You are a Nigerian cuisine expert assistant for NaijaPlate, specializing in:
        1. Nigerian cooking and recipes
        2. UK-Nigerian fusion cuisine
        3. Finding African ingredients in the UK
        4. Cooking techniques and cultural context
        """

    async def get_recipe_recommendations(self, preferences: Dict) -> List[str]:
        prompt = f"""
        Based on these preferences:
        - Dietary restrictions: {preferences.get('dietary_restrictions', 'None')}
        - Cooking skill: {preferences.get('cooking_skill', 'Intermediate')}
        - Available ingredients: {preferences.get('available_ingredients', 'Standard UK ingredients')}

        Suggest 3 Nigerian recipes that would be suitable.
        Include brief descriptions and difficulty levels.
        """

        response = await self.model.generate_content(self.base_context + prompt)
        return response.text

    async def find_ingredient_substitutes(self, ingredient: str, location: Dict) -> Dict:
        """Find ingredient substitutes and nearby stores based on user location"""
        try:
            user_coords = (location.get('latitude'), location.get('longitude'))

            prompt = f"""
            For the Nigerian ingredient '{ingredient}' near {location.get('address', 'UK')}:
            1. Suggest common substitutes available in UK supermarkets
            2. Provide closest matching alternatives
            3. Explain how it might affect the dish's taste
            4. Recommend types of stores to find the authentic ingredient
            """

            response = await self.model.generate_content(self.base_context + prompt)

            return {
                'ingredient': ingredient,
                'location': location.get('address'),
                'substitutes': response.text,
                'coordinates': user_coords
            }
        except Exception as e:
            return {'error': str(e)}

    async def get_cooking_tips(self, recipe_name: str) -> str:
        prompt = f"""
        Provide detailed cooking tips for '{recipe_name}':
        1. Common mistakes to avoid
        2. Traditional techniques
        3. Modern adaptations for UK kitchens
        4. How to tell when it's properly cooked
        5. Serving suggestions and accompaniments
        """

        response = await self.model.generate_content(self.base_context + prompt)
        return response.text

    async def analyze_youtube_tutorial(self, video_title: str, transcript: str) -> Dict:
        prompt = f"""
        Analyze this Nigerian cooking tutorial:
        Title: {video_title}
        Transcript: {transcript}

        Provide:
        1. Key cooking steps
        2. Important techniques mentioned
        3. Ingredient substitutions discussed
        4. Cultural context and tips
        """

        response = await self.model.generate_content(self.base_context + prompt)
        return {
            'title': video_title,
            'analysis': response.text
        }

    def _get_coordinates(self, location: str) -> Optional[tuple]:
        """Get coordinates for a location string"""
        try:
            loc = self.geolocator.geocode(location)
            if loc:
                return (loc.latitude, loc.longitude)
            return None
        except:
            return None

    async def get_nearby_stores(self, location: Dict, radius_km: float = 5.0) -> List[Dict]:
        """Find African/Nigerian grocery stores near the user's location"""
        try:
            user_coords = (location.get('latitude'), location.get('longitude'))

            prompt = f"""
            For someone near {location.get('address', 'UK')}, suggest:
            1. Types of stores that typically stock Nigerian ingredients
            2. Common store names in the UK that carry African products
            3. What sections to look in regular supermarkets
            4. Tips for finding authentic ingredients
            """

            response = await self.model.generate_content(self.base_context + prompt)

            return {
                'location': location.get('address'),
                'suggestions': response.text,
                'coordinates': user_coords
            }
        except Exception as e:
            return {'error': str(e)}