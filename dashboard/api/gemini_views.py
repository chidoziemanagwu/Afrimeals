# dashboard/api/gemini_views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from dashboard.services.gemini_assistant import GeminiAssistant
from django.core.cache import cache
import logging
import asyncio

logger = logging.getLogger(__name__)
gemini = GeminiAssistant()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat(request):
    try:
        message = request.data.get('message')

        if not message:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cache_key = f"chat_response_{hash(message)}"
        cached_response = cache.get(cache_key)

        if cached_response:
            return Response(cached_response)

        # Run async function in sync context
        response = asyncio.run(gemini.chat(message))

        response_data = {
            'success': True,
            'message': response
        }

        cache.set(cache_key, response_data, timeout=3600)  # Cache for 1 hour
        return Response(response_data)

    except Exception as e:
        logger.error(f"Error in chat: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to process chat message'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )