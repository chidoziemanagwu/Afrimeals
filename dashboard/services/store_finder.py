# dashboard/services/store_finder.py
from google import genai
from django.conf import settings
import json
import re

class StoreFinder:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Common Nigerian/African store keywords
        self.african_store_types = [
            "African Food Store",
            "Nigerian Store",
            "African Market",
            "African Grocery",
            "International Food Store",
            "World Food Market",
            "Ethnic Food Store"
        ]

    def clean_ingredient(self, text: str) -> dict:
        """Extract ingredient details and identify if it's a Nigerian/African specific item"""
        # Remove store suggestions in parentheses
        clean_text = re.sub(r'\s*\([^)]*\)', '', text).strip()

        # Common Nigerian/African ingredients keywords
        nigerian_ingredients = [
            "egusi", "ogbono", "uda", "uziza", "ehuru", "utazi", "ukazi",
            "stockfish", "crayfish", "palm oil", "red oil", "locust beans", "iru",
            "bitter leaf", "pounded yam", "garri", "fufu", "semolina", "efo",
            "okra", "okro", "melon seeds", "pepper soup", "suya", "yam flour",
            "plantain flour", "cassava flour", "ground melon", "dried fish",
            "dried prawns", "periwinkle", "snail", "goat meat", "cow foot",
            "cow skin", "kpomo", "dawadawa"
        ]

        # Check if ingredient is Nigerian/African specific
        is_nigerian = any(keyword in clean_text.lower() for keyword in nigerian_ingredients)

        return {
            "name": clean_text,
            "is_nigerian": is_nigerian
        }

    def find_stores_for_ingredient(self, lat: float, lng: float, ingredient: str) -> dict:
        """Find stores that sell the ingredient with special handling for Nigerian items"""
        try:
            # Clean and analyze ingredient
            ingredient_info = self.clean_ingredient(ingredient)

            # Create location-aware prompt
            prompt = {
                "role": "user",
                "parts": [{
                    "text": f"""As a store finder specializing in African and international foods in the UK:
                    Find stores near coordinates ({lat}, {lng}) that sell {ingredient_info['name']}.

                    Requirements:
                    {self.get_search_requirements(ingredient_info)}

                    Return exactly this JSON format:
                    {{
                        "stores": [
                            {{
                                "name": "Store name",
                                "type": "Store type (e.g. African Store, Supermarket)",
                                "address": "Full store address",
                                "distance": "X.X miles",
                                "likely_in_stock": true/false
                            }}
                        ]
                    }}

                    Sort by:
                    1. Likelihood of having the item
                    2. Distance from coordinates
                    Limit to 5 closest relevant stores."""
                }]
            }

            # Get store suggestions
            response = self.client.models.generate_content(
                model='gemini-2.0-pro',
                contents=prompt
            )

            # Parse JSON from response
            content = response.text
            start = content.find('{')
            end = content.rfind('}') + 1
            stores_data = json.loads(content[start:end])

            # Add store recommendations if needed
            if ingredient_info['is_nigerian']:
                stores_data = self.add_store_recommendations(stores_data, lat, lng)

            return stores_data

        except Exception as e:
            print(f"Store finder error: {e}")
            return self.get_fallback_data(ingredient_info['is_nigerian'])

    def get_search_requirements(self, ingredient_info: dict) -> str:
        """Get search requirements based on ingredient type"""
        if ingredient_info['is_nigerian']:
            return """
            - Prioritize African/Nigerian food stores
            - Include major international supermarkets with world food sections
            - Look for stores within 10 miles
            - Consider specialty food markets
            - Include halal shops that may stock African ingredients
            - Note if store is likely to have the item in stock
            """
        else:
            return """
            - Include major supermarkets
            - Look for stores within 5 miles
            - Include local grocery stores
            - Note if store is likely to have the item in stock
            """

    def add_store_recommendations(self, data: dict, lat: float, lng: float) -> dict:
        """Add helpful recommendations for Nigerian ingredients"""
        if not data.get('stores'):
            data['stores'] = []

        data['recommendations'] = [
            "Try calling the store to confirm stock availability",
            "Some stores may keep specialty items behind the counter",
            "Ask about delivery options for bulk purchases",
            "Check if they can order items specially for you"
        ]

        return data

    def get_fallback_data(self, is_nigerian: bool) -> dict:
        """Return fallback store data based on ingredient type"""
        stores = [
            {
                "name": "Local African Food Store",
                "type": "African Grocery",
                "address": "Bradford City Center",
                "distance": "0.5 miles",
                "likely_in_stock": True
            },
            {
                "name": "International Supermarket",
                "type": "World Foods",
                "address": "Leeds Road, Bradford",
                "distance": "1.2 miles",
                "likely_in_stock": True
            }
        ] if is_nigerian else [
            {
                "name": "Local Supermarket",
                "type": "Supermarket",
                "address": "Bradford City Center",
                "distance": "0.5 miles",
                "likely_in_stock": True
            }
        ]

        return {"stores": stores}