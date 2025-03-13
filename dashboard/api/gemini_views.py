# dashboard/api/gemini_views.py

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from dashboard.services.gemini_assistant import GeminiAssistant
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)
gemini = GeminiAssistant()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def get_recipe_recommendations(request):
    try:
        preferences = {
            'dietary_restrictions': request.data.get('dietary_restrictions', 'None'),
            'cooking_skill': request.data.get('cooking_skill', 'Intermediate'),
            'available_ingredients': request.data.get('available_ingredients', 'Standard UK ingredients')
        }

        cache_key = f"recipe_recommendations_{hash(str(preferences))}"
        cached_response = cache.get(cache_key)

        if cached_response:
            return Response(cached_response)

        recommendations = await gemini.get_recipe_recommendations(preferences)

        response_data = {
            'success': True,
            'recommendations': recommendations
        }

        cache.set(cache_key, response_data, timeout=3600)  # Cache for 1 hour
        return Response(response_data)

    except Exception as e:
        logger.error(f"Error getting recipe recommendations: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to get recipe recommendations'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def find_ingredient_substitutes(request):
    try:
        ingredient = request.data.get('ingredient')
        location = request.data.get('location', 'UK')

        if not ingredient:
            return Response(
                {'error': 'Ingredient is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cache_key = f"ingredient_substitutes_{ingredient}_{location}"
        cached_response = cache.get(cache_key)

        if cached_response:
            return Response(cached_response)

        substitutes = await gemini.find_ingredient_substitutes(ingredient, location)

        response_data = {
            'success': True,
            'data': substitutes
        }

        cache.set(cache_key, response_data, timeout=86400)  # Cache for 24 hours
        return Response(response_data)

    except Exception as e:
        logger.error(f"Error finding ingredient substitutes: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to find ingredient substitutes'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def get_cooking_tips(request):
    try:
        recipe_name = request.data.get('recipe_name')

        if not recipe_name:
            return Response(
                {'error': 'Recipe name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cache_key = f"cooking_tips_{recipe_name}"
        cached_response = cache.get(cache_key)

        if cached_response:
            return Response(cached_response)

        tips = await gemini.get_cooking_tips(recipe_name)

        response_data = {
            'success': True,
            'tips': tips
        }

        cache.set(cache_key, response_data, timeout=86400)  # Cache for 24 hours
        return Response(response_data)

    except Exception as e:
        logger.error(f"Error getting cooking tips: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to get cooking tips'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )