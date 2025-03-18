from decimal import Decimal
import os
import random
import re
from django.urls import reverse
from openai import OpenAI
import json
from django.views.generic import TemplateView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View
from django.http import FileResponse, JsonResponse, HttpResponse
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from django.contrib import messages
from django.db.models import Q
from django.core.exceptions import PermissionDenied
import requests
from .utils.currency import CurrencyManager


from dashboard.decorators import rate_limit
from .models import (
    MealPlan, PaymentHistory, Recipe, GroceryList, SubscriptionTier,
    UserSubscription, UserActivity, UserFeedback
)

import hashlib
from .forms import FeedbackForm, RecipeForm
import stripe
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
from celery.result import AsyncResult
from django.http import JsonResponse
import logging
from django.contrib.auth import logout
from openai import OpenAIError, RateLimitError, APIError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
import pandas as pd
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from google import genai
from .services.gemini_assistant import GeminiAssistant
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_GET
from math import radians, sin, cos, sqrt, atan2
from .services.store_finder import StoreFinder
from mailjet_rest import Client

# Set up logger
logger = logging.getLogger(__name__)


# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Cache timeouts
CACHE_TIMEOUTS = {
    'short': 300,        # 5 minutes
    'medium': 1800,      # 30 minutes
    'long': 3600,        # 1 hour
    'very_long': 86400,  # 24 hours
}

# views.py

def detect_user_currency(request):
    try:
        # Get user's IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        # Try to get from cache first
        cache_key = f'user_currency_{ip}'
        currency = cache.get(cache_key)

        if not currency:
            response = requests.get(
                f'https://ipapi.co/{ip}/json/',
                timeout=5,
                headers={'User-Agent': 'Mozilla/5.0'}
            )

            if response.status_code == 200:
                data = response.json()
                currency = data.get('currency', 'GBP')
                # Cache for 24 hours
                cache.set(cache_key, currency, 86400)
            else:
                currency = 'GBP'

        return JsonResponse({
            'success': True,
            'currency': currency
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'currency': 'GBP',
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_exchange_rates(request):
    try:
        base_currency = request.GET.get('base_currency', 'GBP')

        # Try to get from cache first
        cache_key = f'exchange_rates_{base_currency}'
        rates = cache.get(cache_key)

        if not rates:
            response = requests.get(
                'https://api.freecurrencyapi.com/v1/latest',
                headers={'apikey': settings.CURRENCY_API_KEY},
                params={
                    'base_currency': 'GBP',
                    'currencies': 'USD,EUR'
                },
            )

            if response.status_code == 200:
                rates = response.json()
                # Cache for 1 hour
                cache.set(cache_key, rates, 3600)
            else:
                return JsonResponse({
                    'error': 'Failed to fetch exchange rates'
                }, status=400)

        return JsonResponse(rates)

    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


def find_stores(request):
    try:
        lat = float(request.GET.get('lat', 0))
        lng = float(request.GET.get('lng', 0))
        ingredient = request.GET.get('ingredient', '')

        if not all([lat, lng, ingredient]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameters',
                'stores': []
            })

        store_finder = StoreFinder()
        result = store_finder.find_stores_for_ingredient(lat, lng, ingredient)

        # Ensure we always return a valid response
        return JsonResponse({
            'success': True,
            'stores': result.get('stores', []),
            'recommendations': result.get('recommendations', [])
        })

    except Exception as e:
        print(f"Store finder error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while searching for stores',
            'stores': []
        })    


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c

    return distance


def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c

    return distance


@require_http_methods(["POST"])
def gemini_chat(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '')

        # Here you would integrate with the Gemini API
        # For now, we'll return a simple response
        response = {
            'message': f"I received your message about: {user_message}"
        }

        return JsonResponse(response)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def check_task_status(request, task_id):
    task = AsyncResult(task_id)
    if task.ready():
        result = task.get()
        if result.get('success'):
            return JsonResponse(result)
        return JsonResponse({
            'success': False,
            'error': result.get('error')
        })
    return JsonResponse({'status': 'processing'})



@login_required
def meal_plan_history(request):
    meal_plans = MealPlan.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'meal_plan_history.html', {'meal_plans': meal_plans})

@login_required
def get_meal_plan_details(request, meal_plan_id):
    try:
        # Get the meal plan
        meal_plan = get_object_or_404(MealPlan, id=meal_plan_id, user=request.user)

        # Parse the JSON data from the description field
        meal_plan_data = json.loads(meal_plan.description)

        # Get associated recipes if they exist
        recipes = Recipe.objects.filter(
            meal_plan=meal_plan
        ).values('id', 'title', 'meal_type', 'day_index')

        # Create a recipe lookup dictionary
        recipe_lookup = {
            f"{recipe['day_index']}-{recipe['meal_type']}": recipe
            for recipe in recipes
        }

        # Add recipe information to meal plan data
        for day_index, day in enumerate(meal_plan_data):
            for meal_type in day['meals'].keys():
                recipe_key = f"{day_index}-{meal_type}"
                if recipe_key in recipe_lookup:
                    day['meals'][f"{meal_type}_recipe"] = recipe_lookup[recipe_key]

        return JsonResponse({
            'success': True,
            'meal_plan': meal_plan_data,
            'name': meal_plan.name,
            'created_at': meal_plan.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid meal plan data format'
        }, status=400)
    except Exception as e:
        logger.error(f"Error fetching meal plan details: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to load meal plan details'
        }, status=500)


        
# views.py

@require_POST
@staff_member_required
def mark_feedback_status(request, feedback_id):
    try:
        feedback = UserFeedback.objects.get(id=feedback_id)
        feedback.is_resolved = not feedback.is_resolved  # Toggle the resolved status
        feedback.save()

        # Calculate updated feedback statistics
        total_feedback = UserFeedback.objects.count()
        resolved_feedback = UserFeedback.objects.filter(is_resolved=True).count()
        unresolved_feedback = total_feedback - resolved_feedback

        feedback_stats = {
            'total': total_feedback,
            'resolved': resolved_feedback,
            'unresolved': unresolved_feedback
        }

        return JsonResponse({
            'success': True,
            'is_resolved': feedback.is_resolved,
            'feedback_stats': feedback_stats
        })
    except UserFeedback.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Feedback not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    

@require_GET
def update_currency(request):
    """API endpoint for currency updates"""
    currency = request.GET.get('currency', 'GBP')

    # Update session
    request.session['user_currency'] = currency

    # Get and return updated price data
    price_data = CurrencyManager.get_price_data(currency)
    return JsonResponse(price_data)


def google_login_redirect(request):
    """Redirect all login attempts to Google OAuth"""
    next_url = request.GET.get('next', '')
    return redirect(f'/accounts/google/login/?next={next_url}')

@require_http_methods(["GET"])
def custom_logout(request):
    logout(request)
    return redirect('/')




    

class HomeView(TemplateView):
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')

        # Get currency and pricing information
        currency = CurrencyManager.get_user_currency(request)
        price_data = CurrencyManager.get_price_data(currency)

        # Add pricing context
# Set context for template
        self.extra_context = {
            **price_data,  # Unpack all price data
            'supported_currencies': CurrencyManager.get_supported_currencies(),
            'page_title': 'Welcome to NaijaPlate',
            'meta_description': 'AI-powered Nigerian meal planning for the UK diaspora'
        }

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add any additional context data if needed
        context['page_title'] = 'Welcome to NaijaPlate'
        context['meta_description'] = 'AI-powered Nigerian meal planning for the UK diaspora'

        return context

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        try:
            # Get recent activities
            recent_activities = UserActivity.objects.filter(
                user=user
            ).select_related('user').order_by('-timestamp')[:5]

            # Get meal plans and recipes
            recent_meal_plans = MealPlan.objects.filter(
                user=user
            ).select_related('user').order_by('-created_at')[:5]

            recent_recipes = Recipe.objects.filter(
                user=user
            ).select_related('user').order_by('-created_at')[:5]

            # Get subscription
            # subscription = UserSubscription.get_active_subscription(user.id)

            # Process activities to include related objects
            processed_activities = []
            for activity in recent_activities:
                activity_data = {
                    'id': activity.id,
                    'action': activity.action,
                    'timestamp': activity.timestamp,
                    'get_action_display': activity.get_action_display(),
                    'details': activity.details or {},
                }
                processed_activities.append(activity_data)

            context.update({
                'recent_meal_plans': recent_meal_plans,
                'recent_recipes': recent_recipes,
                # 'subscription': subscription,
                'recent_activities': processed_activities,
            })

        except Exception as e:
            # Log the error
            logger.error(f"Dashboard error for user {user.id}: {str(e)}", exc_info=True)
            # Provide empty defaults
            context.update({
                'recent_meal_plans': [],
                'recent_recipes': [],
                'subscription': None,
                'recent_activities': [],
            })
            messages.error(self.request, "There was an error loading your dashboard. Please try again later.")

        return context

# views.py



class MealGeneratorView(LoginRequiredMixin, View):
    # Configurable timeouts
    API_TIMEOUT = 15  # seconds
    CACHE_TIMEOUT = 3600  # 1 hour
    MAX_RETRIES = 2
    
    def __init__(self):
        super().__init__()
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        # Initialize Gemini client
        self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.base_context = """
        You are a Nigerian cuisine expert specializing in creating detailed recipes
        that blend traditional Nigerian cooking with modern techniques and UK ingredients.
        Focus on:
        1. Clear, step-by-step instructions
        2. UK-available ingredients with substitutions
        3. Precise measurements in UK units
        4. Cultural context and significance
        5. Health and nutrition information
        """

    def get(self, request):
        """Handle GET request - display meal generator form"""
        cache_key = f"meal_generator_data_{request.user.id}"
        view_data = cache.get(cache_key)

        if not view_data:
            subscription = UserSubscription.get_active_subscription(request.user.id)
            view_data = {
                'has_subscription': subscription is not None,
                # 'subscription_tier': subscription.subscription_tier if subscription else None,
                'dietary_preferences': settings.DIETARY_PREFERENCES,
                'supported_currencies': settings.SUPPORTED_CURRENCIES,  # Make sure this is passed
                'user_currency': self.get_user_currency(request)
            }
            cache.set(cache_key, view_data, settings.CACHE_TIMEOUTS['medium'])

        return render(request, 'meal_generator.html', view_data)

    def get_user_currency(self, request):
        """Detect user's currency based on IP location"""
        try:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

            response = requests.get(f'https://ipapi.co/{ip}/json/')
            data = response.json()

            currency_map = {
                'NG': 'NGN', 'US': 'USD', 'GB': 'GBP',
                'GH': 'GHS', 'KE': 'KES', 'ZA': 'ZAR'
            }

            return currency_map.get(data.get('country_code'), 'USD')
        except Exception as e:
            logger.warning(f"Currency detection failed: {str(e)}")
            return 'USD'

    @rate_limit('meal_generator', max_requests=5, timeout=3600)
    def post(self, request):
        """Handle POST request - generate meal plan"""
        try:
            form_data = self._extract_form_data(request.POST)

            if form_data['premium_features_requested'] and not self._has_active_subscription(request.user):
                return JsonResponse({
                    'success': False,
                    'requires_upgrade': True,
                    'message': 'This feature requires a subscription. Please upgrade to access it.'
                })

            response_data = self._generate_meal_plan(request.user, form_data)

            UserActivity.objects.create(
                user=request.user,
                action='create_meal',
                details={
                    'meal_plan_type': form_data['dietary_preferences'],
                    'currency': form_data['budget']['currency']
                }
            )

            return JsonResponse(response_data)

        except Exception as e:
            error_message = self._get_error_message(e)
            logger.error(f"Meal generation error: {str(e)}", exc_info=True, extra={
                'user_id': request.user.id,
                'form_data': form_data if 'form_data' in locals() else {}
            })

            return JsonResponse({
                'success': False,
                'error': error_message,
                'details': str(e) if settings.DEBUG else ""
            }, status=500)

    def _generate_with_gemini(self, prompt):
        """Generate response using Gemini API with enhanced randomization"""
        try:
            # Random context elements
            random_contexts = [
                "Create innovative Nigerian-British fusion recipes.",
                "Focus on traditional Nigerian flavors with modern British twists.",
                "Emphasize healthy adaptations of classic Nigerian dishes.",
                "Design weekday-friendly quick Nigerian meals.",
                "Create budget-conscious Nigerian recipes with UK ingredients."
            ]

            # Combine random elements with base context
            enhanced_prompt = (
                self.base_context + "\n" +
                random.choice(random_contexts) + "\n\n" +
                "Generate a Nigerian meal plan with grocery list. Format the response exactly as follows:\n\n" +
                "MEAL PLAN:\n" +
                "Day 1:\n" +
                "Breakfast: [meal]\n" +
                "Lunch: [meal]\n" +
                "Dinner: [meal]\n" +
                "[Continue for all days]\n\n" +
                "GROCERY LIST:\n" +
                "- [ingredient 1]\n" +
                "- [ingredient 2]\n" +
                "[Continue for all ingredients]\n\n" +
                prompt
            )

            # Generate content using gemini-2.0-flash model
            response = self.gemini_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=enhanced_prompt
            )

            if not response or not response.text:
                raise ValueError("Empty response from Gemini API")

            # Get the response text as string
            response_text = str(response.text)

            # Split the response into sections
            sections = response_text.split("GROCERY LIST:")
            
            if len(sections) < 2:
                raise ValueError("Invalid response format from Gemini")

            meal_plan_text = sections[0].replace("MEAL PLAN:", "").strip()
            grocery_list_text = sections[1].strip()

            # Process grocery list
            grocery_list = [
                item.strip("- ").strip()
                for item in grocery_list_text.split("\n")
                if item.strip() and not item.strip().startswith("COOKING TIPS:")
            ]

            # Add random cooking tips
            cooking_tips = random.sample([
                "Use fresh ingredients when possible",
                "Remember to adjust seasoning to taste",
                "Prep ingredients before starting to cook",
                "Store leftover ingredients properly",
                "Consider batch cooking for efficiency"
            ], 2)

            return {
                'success': True,
                'meal_plan': meal_plan_text,
                'grocery_list': grocery_list,
                'cooking_tips': cooking_tips,
                'generated_by': 'gemini'
            }

        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise


    
    def _generate_with_openai(self, prompt):
        """Generate response using OpenAI API with enhanced randomization"""
        try:
            # Random context elements
            random_contexts = [
                "You are a creative Nigerian-British fusion chef.",
                "You are a health-conscious Nigerian cuisine expert.",
                "You are a modern Nigerian food innovator.",
                "You are a traditional Nigerian cooking master.",
                "You are a Nigerian meal prep specialist."
            ]

            # Random style elements
            random_styles = [
                "Focus on quick and easy methods.",
                "Emphasize authentic techniques.",
                "Prioritize healthy adaptations.",
                "Create budget-friendly versions.",
                "Design meal-prep friendly recipes."
            ]

            # Random dietary elements
            random_dietary = [
                "Consider balanced nutrition.",
                "Include vegetarian options.",
                "Focus on protein-rich meals.",
                "Emphasize whole ingredients.",
                "Add low-carb alternatives."
            ]

            # Random system messages
            system_messages = [
                {"role": "system", "content": random.choice(random_contexts)},
                {"role": "system", "content": random.choice(random_styles)},
                {"role": "system", "content": random.choice(random_dietary)}
            ]

            # Randomize API parameters
            api_params = {
                "model": random.choice(["gpt-4", "gpt-4-turbo-preview"]),
                "temperature": random.uniform(0.7, 0.9),
                "presence_penalty": random.uniform(0.0, 0.5),
                "frequency_penalty": random.uniform(0.0, 0.5),
                "top_p": random.uniform(0.9, 1.0),
                "max_tokens": random.randint(1800, 2000)
            }

            # Create message array with random elements
            messages = [
                random.choice(system_messages),
                {"role": "user", "content": prompt}
            ]

            # Randomly add follow-up guidance
            if random.random() > 0.5:
                messages.append(random.choice([
                    {"role": "system", "content": "Add practical cooking tips."},
                    {"role": "system", "content": "Include seasonal variations."},
                    {"role": "system", "content": "Suggest ingredient substitutions."},
                    {"role": "system", "content": "Add cultural context."}
                ]))

            response = self.openai_client.chat.completions.create(
                messages=messages,
                **api_params
            )

            response_text = response.choices[0].message.content

            # Post-process with random additions
            if random.random() > 0.6:
                additional_content = random.choice([
                    self._generate_random_tips(),
                    self._generate_random_variations(),
                    self._generate_random_cultural_notes()
                ])
                response_text += "\n\n" + additional_content

            return response_text

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise

    def _generate_random_tips(self):
        """Generate random cooking tips"""
        tips = random.sample([
            "For best results, marinate overnight",
            "Toast spices before grinding",
            "Use fresh herbs when possible",
            "Adjust heat levels to taste",
            "Let stews simmer for deeper flavor",
            "Store leftovers properly sealed",
            "Prep ingredients before starting",
            "Monitor cooking temperatures carefully"
        ], 3)
        return "Additional Tips:\n- " + "\n- ".join(tips)

    def _generate_random_variations(self):
        """Generate random recipe variations"""
        variations = random.sample([
            "Make it vegetarian by substituting mushrooms",
            "Add extra spice with scotch bonnets",
            "Create a fusion version with British ingredients",
            "Make it kid-friendly by reducing spices",
            "Prepare a batch-cooking version",
            "Create a quick weeknight version"
        ], 2)
        return "Recipe Variations:\n- " + "\n- ".join(variations)

    def _generate_random_cultural_notes(self):
        """Generate random cultural context"""
        notes = random.sample([
            "Traditionally served during festivals",
            "Common street food in Lagos",
            "Popular for Sunday family gatherings",
            "Modern adaptation of a classic dish",
            "Fusion of Nigerian and British tastes",
            "Regional variation from Northern Nigeria"
        ], 2)
        return "Cultural Notes:\n- " + "\n- ".join(notes)

    def _generate_meal_plan(self, user, form_data):
        """Generate meal plan using OpenAI"""
        prompt = self._construct_prompt(form_data)
        cache_key = f"meal_plan_{hashlib.md5(prompt.encode()).hexdigest()}"

        cached_response = cache.get(cache_key)
        if cached_response:
            return cached_response

        # Add randomization to the prompt
        random_elements = [
            "Be creative and surprise me with unique combinations.",
            "Include some fusion elements in the recipes.",
            "Mix traditional and modern cooking methods.",
            "Focus on seasonal ingredients available in the UK.",
            "Include some lesser-known Nigerian dishes.",
        ]
        prompt += f"\n{random.choice(random_elements)}"

        try:
            # Generate with OpenAI
            response_text = self._generate_with_openai(prompt)

            if not response_text:
                raise ValueError("Empty response from OpenAI API")

            processed_data = self._process_response(response_text, form_data, user, 'openai')

            # Add randomization to the response
            if processed_data['success']:
                # Randomly shuffle the days in the meal plan
                random.shuffle(processed_data['meal_plan'])

                # Randomly shuffle the grocery list
                random.shuffle(processed_data['grocery_list'])

                # Add random cooking tips
                tips = [
                    "Remember to adjust seasoning to taste",
                    "Prep ingredients before starting to cook",
                    "Store leftover ingredients properly",
                    "Consider batch cooking for efficiency",
                    "Use fresh ingredients when possible"
                ]
                processed_data['cooking_tips'] = random.sample(tips, 2)

            cache.set(cache_key, processed_data, settings.CACHE_TIMEOUTS['very_long'])
            return processed_data

        except Exception as e:
            logger.error(f"OpenAI generation failed: {str(e)}")
            raise Exception("Failed to generate meal plan")



    def _process_response(self, response_text, form_data, user, source):
        """Process AI response into structured data"""
        parts = response_text.strip().split('GROCERY LIST:')

        if len(parts) < 2:
            raise ValueError(f'Invalid response format from {source}')

        meal_plan_text = parts[0].replace('MEAL PLAN:', '').strip()
        grocery_list_text = parts[1].strip()

        structured_meal_plan = self._structure_meal_plan(meal_plan_text, form_data)
        structured_grocery_list = [
            item.strip('- ').strip()
            for item in grocery_list_text.split('\n')
            if item.strip()
        ]

        # Save to database
        meal_plan = MealPlan.objects.create(
            user=user,
            name=f"Meal Plan for {form_data['dietary_preferences']}",
            description=json.dumps(structured_meal_plan)
        )

        GroceryList.objects.create(
            user=user,
            items="\n".join(structured_grocery_list)
        )

        return {
            'success': True,
            'meal_plan_id': meal_plan.id,
            'meal_plan': structured_meal_plan,
            'grocery_list': structured_grocery_list,
            'generated_by': source
        }    
    
    
    
    def _extract_form_data(self, post_data):
        """Extract and validate form data"""
        try:
            budget_amount = Decimal(post_data.get('budget', '0'))
        except:
            budget_amount = Decimal('0')

        dietary_pref = post_data.get('dietary_preferences', 'balanced')
        if dietary_pref not in settings.DIETARY_PREFERENCES:
            dietary_pref = 'balanced'

        return {
            'dietary_preferences': dietary_pref,
            'preferred_cuisine': post_data.get('preferred_cuisine', 'Contemporary Nigerian'),
            'health_goals': post_data.get('health_goals', ''),
            'allergies': post_data.get('allergies', ''),
            'meals_per_day': post_data.get('meals_per_day', '3'),
            'include_snacks': post_data.get('include_snacks') == 'on',
            'plan_days': post_data.get('plan_days', '7'),
            'budget': {
                'amount': budget_amount,
                'currency': post_data.get('currency', 'USD')
            },
            'skill_level': post_data.get('skill_level', 'Intermediate'),
            'family_size': post_data.get('family_size', '4'),
            'premium_features_requested': any(
                post_data.get(feature) for feature in
                ['detailed_nutrition', 'video_recipes', 'detailed_recipes']
            )
        }

    def _construct_prompt(self, form_data):
        """Construct the prompt for AI models"""
        # Get currency symbol directly since it's a simple mapping
        currency_symbol = settings.SUPPORTED_CURRENCIES.get(
            form_data['budget']['currency'], '$'  # Default to $ if currency not found
        )
        budget_string = f"{currency_symbol}{form_data['budget']['amount']}"

        prompt = (
            f"Generate a meal plan for {form_data['plan_days']} days and grocery list "
            f"for a {form_data['dietary_preferences']} diet with {form_data['preferred_cuisine']} cuisine.\n"
            f"Budget: {budget_string} in {form_data['budget']['currency']}.\n"
        )

        if form_data['health_goals']:
            prompt += f"Health goals: {form_data['health_goals']}.\n"
        if form_data['allergies']:
            prompt += f"Allergies and restrictions: {form_data['allergies']}.\n"

        prompt += self._add_meal_structure(form_data)
        return prompt


    
    def _add_meal_structure(self, form_data):
        """Add meal structure to prompt"""
        structure = (
            f"Include {form_data['meals_per_day']} meals per day.\n"
            f"{'Include a snack for each day.' if form_data['include_snacks'] else ''}\n"
            f"Skill level: {form_data['skill_level']}.\n"
            f"Family size: {form_data['family_size']}.\n\n"
            "Format the response as:\n"
            "MEAL PLAN:\n"
        )

        for day in range(1, int(form_data['plan_days']) + 1):
            structure += f"Day {day}:\n"
            if int(form_data['meals_per_day']) >= 2:
                structure += "Breakfast: [meal]\n"
            structure += "Lunch: [meal]\n"
            if form_data['include_snacks']:
                structure += "Snack: [snack]\n"
            if int(form_data['meals_per_day']) >= 3:
                structure += "Dinner: [meal]\n"
            structure += "\n"

        structure += "GROCERY LIST:\n- [ingredient 1]\n- [ingredient 2]\n..."
        return structure



    def _structure_meal_plan(self, meal_plan_text, form_data):
        """Convert meal plan text to structured data"""
        structured_meal_plan = []
        current_day = None

        for line in meal_plan_text.split('\n'):
            line = line.strip()
            if not line:
                continue

            if line.startswith('Day'):
                current_day = {
                    'day': line.split(':')[0],
                    'meals': {
                        'breakfast': '',
                        'lunch': '',
                        'snack': '' if form_data['include_snacks'] else None,
                        'dinner': ''
                    }
                }
                structured_meal_plan.append(current_day)
            elif current_day and ':' in line:
                meal_type, meal = line.split(': ', 1)
                meal_type_lower = meal_type.lower()
                if meal_type_lower in current_day['meals']:
                    current_day['meals'][meal_type_lower] = meal

        return structured_meal_plan

    def _get_error_message(self, error):
        """Get appropriate error message based on error type"""
        if isinstance(error, RateLimitError):
            return "We're experiencing high demand. Please try again in a few minutes."
        elif isinstance(error, APIError):
            return "Our meal generation service is temporarily unavailable. Please try again later."
        elif isinstance(error, ValueError):
            return "Please check your meal preferences and try again."
        return "We couldn't generate your meal plan. Please try again with different preferences."

    def _has_active_subscription(self, user):
        """Check if user has an active subscription"""
        return UserSubscription.get_active_subscription(user.id) is not None





# views.py

class PricingView(TemplateView):
    template_name = 'pricing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get subscription tiers from cache or database
        cache_key = 'active_subscription_tiers'
        subscription_tiers = cache.get(cache_key)

        if not subscription_tiers:
            subscription_tiers = SubscriptionTier.objects.filter(
                is_active=True
            ).order_by('price')
            cache.set(cache_key, subscription_tiers, CACHE_TIMEOUTS['long'])

        # Add currency-related context
        context.update({
            'subscription_tiers': subscription_tiers,
            'stripe_public_key': settings.STRIPE_PUBLISHABLE_KEY,
            'currency_api_key': settings.CURRENCY_API_KEY,
            'base_currency': 'GBP',
            'supported_currencies': settings.SUPPORTED_CURRENCIES
        })
        return context

class CheckoutView(View):
    def post(self, request, tier_id):
        try:
            tier = get_object_or_404(SubscriptionTier, id=tier_id)
            currency = request.headers.get('X-Currency', 'GBP')
            exchange_rate = self.get_exchange_rate(currency)
            converted_price = float(tier.price) * exchange_rate

            # Deactivate existing subscriptions
            UserSubscription.objects.filter(
                user=request.user,
                is_active=True
            ).update(
                is_active=False,
                status='expired',
                end_date=timezone.now()
            )

            # Calculate end date based on tier type
            end_date = timezone.now() + {
                'weekly': timedelta(days=7),
                'monthly': timedelta(days=30),
                'one_time': timedelta(days=365),
            }.get(tier.tier_type, timedelta(days=30))

            # Map our tier types to Stripe's accepted intervals
            stripe_intervals = {
                'weekly': 'week',
                'monthly': 'month'
            }

            # Set up common metadata
            metadata = {
                'user_id': str(request.user.id),
                'tier_id': str(tier.id),
                'tier_type': tier.tier_type,
                'payment_currency': currency,
                'exchange_rate': str(exchange_rate),
                'end_date': end_date.isoformat()
            }

            if tier.tier_type in ['weekly', 'monthly']:
                # For subscription plans
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': currency.lower(),
                            'unit_amount': int(converted_price * 100),
                            'product_data': {
                                'name': f"{tier.name} - {tier.get_tier_type_display()}",
                                'description': tier.description,
                            },
                            'recurring': {
                                'interval': stripe_intervals[tier.tier_type],  # Use mapped interval
                                'interval_count': 1
                            }
                        },
                        'quantity': 1,
                    }],
                    mode='subscription',
                    success_url=request.build_absolute_uri(reverse('checkout_success')),
                    cancel_url=request.build_absolute_uri(reverse('checkout_cancel')),
                    metadata=metadata
                )
            else:
                # For one-time payment
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': currency.lower(),
                            'unit_amount': int(converted_price * 100),
                            'product_data': {
                                'name': f"{tier.name} - One-time Payment",
                                'description': tier.description,
                            },
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=request.build_absolute_uri(reverse('checkout_success')),
                    cancel_url=request.build_absolute_uri(reverse('checkout_cancel')),
                    metadata=metadata
                )

            # Create subscription record
            subscription = UserSubscription.objects.create(
                user=request.user,
                subscription_tier=tier,
                start_date=timezone.now(),
                end_date=end_date,
                is_active=True,
                status='active',
                payment_status='pending',
                stripe_subscription_id=checkout_session.id
            )

            # Create payment history record
            PaymentHistory.objects.create(
                user=request.user,
                subscription=subscription,
                amount=converted_price,
                currency=currency.upper(),
                payment_method='card',
                transaction_id=checkout_session.id,
                status='pending'
            )

            self.send_confirmation_email(request.user, tier, end_date)

            return JsonResponse({
                'sessionId': checkout_session.id
            })

        except Exception as e:
            logger.error(f"Checkout error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    def get_exchange_rate(self, target_currency):
        """Get exchange rate from GBP to target currency"""
        try:
            cache_key = f'exchange_rate_GBP_{target_currency}'
            rate = cache.get(cache_key)

            if rate is None:
                response = requests.get(
                    'https://api.freecurrencyapi.com/v1/latest',
                    headers={'apikey': settings.CURRENCY_API_KEY},
                    params={'base_currency': 'GBP'}
                )

                if response.ok:
                    rates = response.json().get('data', {})
                    rate = rates.get(target_currency, 1.0)
                    cache.set(cache_key, rate, 3600)
                else:
                    logger.error(f"Failed to fetch exchange rate: {response.status_code}")
                    rate = 1.0

            return float(rate)

        except Exception as e:
            logger.error(f"Error fetching exchange rate: {str(e)}")
            return 1.0

    def send_confirmation_email(self, user, tier, end_date):
        try:
            # Initialize Mailjet client
            mailjet = Client(
                auth=(settings.MAILJET_API_KEY, settings.MAILJET_API_SECRET),
                version='v3.1'
            )

            # Prepare email content
            end_date_str = end_date.strftime('%Y-%m-%d')
            text_content = (
                f"Dear {user.username},\n\n"
                f"Thank you for subscribing to {tier.name}! "
                f"Your subscription is active until {end_date_str}."
            )
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Subscription Confirmation</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        background-color: #f4f4f4;
                        margin: 0;
                        padding: 0;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #ffffff;
                        border-radius: 8px;
                        box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                    }}
                    .header {{
                        background-color: #4CAF50;
                        color: white;
                        text-align: center;
                        padding: 20px;
                        border-radius: 8px 8px 0 0;
                    }}
                    .content {{
                        padding: 20px;
                    }}
                    .footer {{
                        background-color: #f4f4f4;
                        text-align: center;
                        padding: 10px;
                        border-radius: 0 0 8px 8px;
                        font-size: 0.8em;
                    }}
                    .icon {{
                        font-size: 24px;
                        color: #4CAF50;
                        margin-right: 10px;
                    }}
                    h1 {{
                        color: #fffff;
                    }}
                    h3 {{
                        color: #333;
                    }}
                    p {{
                        margin-bottom: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Subscription Confirmation</h1>
                    </div>
                    <div class="content">
                        <h3><span class="icon">✨</span> Dear {user.username},</h3>
                        <p>Thank you for subscribing to <strong>{tier.name}</strong>! Your subscription is now active and will remain so until <strong>{end_date_str}</strong>.</p>
                        <p>We're excited to have you on board and can't wait for you to enjoy all the benefits of your new plan. If you have any questions or need assistance, feel free to reach out to our support team.</p>
                        <p>Happy meal planning!</p>
                        <p>The NaijaPlate Team</p>
                    </div>
                    <div class="footer">
                        <p>&copy; 2025 NaijaPlate. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Build Mailjet API payload
            data = {
                'Messages': [{
                    "From": {
                        "Email": settings.DEFAULT_FROM_EMAIL,
                        "Name": "NaijaPlate"
                    },
                    "To": [{
                        "Email": user.email,
                        "Name": user.get_full_name() or user.username
                    }],
                    "Subject": "Subscription Confirmation",
                    "TextPart": text_content,
                    "HTMLPart": html_content
                }]
            }

            # Send email and handle response
            response = mailjet.send.create(data=data)
            if response.status_code != 200:
                logger.error(f"Mailjet API error: {response.status_code} - {response.json()}")
            else:
                logger.info(f"Confirmation email sent successfully to {user.email}")

        except Exception as email_err:
            logger.error(f"Failed to send confirmation email: {str(email_err)}")


class SubscriptionSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'subscription_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subscription = UserSubscription.get_active_subscription(self.request.user.id)
        context['subscription'] = subscription
        return context

class MySubscriptionView(LoginRequiredMixin, DetailView):
    template_name = 'my_subscription.html'

    def get_object(self):
        cache_key = f"user_subscription_{self.request.user.id}"
        subscription = cache.get(cache_key)

        if not subscription:
            subscription = UserSubscription.objects.filter(
                user=self.request.user,
                is_active=True,
                end_date__gt=timezone.now()
            ).select_related('subscription_tier').first()
            if subscription:
                cache.set(cache_key, subscription, CACHE_TIMEOUTS['medium'])

        return subscription

class RecipeListView(LoginRequiredMixin, ListView):
    template_name = 'recipes.html'
    context_object_name = 'user_recipes'  # Changed from 'recipes'
    paginate_by = 12

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['admin_recipes'] = Recipe.objects.filter(is_admin_recipe=True).order_by('-created_at')
        context['query'] = self.request.GET.get('q', '')
        context['sort'] = self.request.GET.get('sort', '-created_at')
        return context

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        sort = self.request.GET.get('sort', '-created_at')

        recipes = Recipe.objects.filter(user=self.request.user, is_admin_recipe=False)

        if query:
            recipes = recipes.filter(
                Q(title__icontains=query) |
                Q(ingredients__icontains=query) |
                Q(instructions__icontains=query)
            )

        if sort in ['title', '-title', 'created_at', '-created_at']:
            recipes = recipes.order_by(sort)
        else:
            recipes = recipes.order_by('-created_at')

        return recipes.select_related('user')   
    




# Update MealPlanListView (add this if you don't have it)
class MealPlanListView(LoginRequiredMixin, ListView):
    template_name = 'meal_plans.html'
    context_object_name = 'meal_plans'
    paginate_by = 10

    def get_queryset(self):
        return MealPlan.objects.filter(
            user=self.request.user
        ).select_related('user').order_by('-created_at')
    


    
    
class RecipeDetailView(LoginRequiredMixin, DetailView):
    model = Recipe
    template_name = 'recipe_detail.html'
    context_object_name = 'recipe'

    def get_object(self):
        cache_key = f"recipe_detail_{self.kwargs['pk']}_{self.request.user.id}"
        recipe = cache.get(cache_key)

        if not recipe:
            recipe = get_object_or_404(
                Recipe.objects.select_related('user'),
                pk=self.kwargs['pk'],
                user=self.request.user
            )
            cache.set(cache_key, recipe, CACHE_TIMEOUTS['medium'])

        return recipe

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     context['has_subscription'] = UserSubscription.get_active_subscription(
    #         self.request.user.id
    #     ) is not None
    #     return context


class RecipeDetailsView(LoginRequiredMixin, View):
    def __init__(self):
        super().__init__()
        self.gemini_assistant = GeminiAssistant()

    def _clean_json_response(self, response_text: str) -> str:
        """Clean the response text to get valid JSON"""
        # Remove markdown code block markers
        cleaned_text = re.sub(r'^```json\s*', '', response_text)
        cleaned_text = re.sub(r'\s*```$', '', cleaned_text)

        # Remove any leading/trailing whitespace
        cleaned_text = cleaned_text.strip()

        return cleaned_text

    def get(self, request, meal_plan_id, day_index, meal_type):
        try:
            # Get the meal plan
            meal_plan = get_object_or_404(MealPlan, id=meal_plan_id, user=request.user)

            try:
                meal_data = json.loads(meal_plan.description)
                meal_name = meal_data[int(day_index)]['meals'][meal_type]
            except (json.JSONDecodeError, IndexError, KeyError) as e:
                logger.error(f"Error parsing meal plan data: {str(e)}")
                return JsonResponse({
                    'error': 'Invalid meal plan data'
                }, status=400)

            # Check for existing recipe
            existing_recipe = Recipe.objects.filter(
                meal_plan=meal_plan,
                day_index=day_index,
                meal_type=meal_type
            ).first()

            if existing_recipe:
                return JsonResponse({
                    'title': existing_recipe.title,
                    'description': self.gemini_assistant.format_response(existing_recipe.description),
                    'prepTime': existing_recipe.prep_time,
                    'cookTime': existing_recipe.cook_time,
                    'servings': existing_recipe.servings,
                    'difficulty': existing_recipe.difficulty,
                    'ingredients': existing_recipe.ingredients_list,
                    'instructions': existing_recipe.instructions_list,
                    'nutrition': existing_recipe.nutrition_info,
                    'tips': existing_recipe.tips,
                    'isNewlyGenerated': False  # Add this flag
                })

            # Construct the recipe generation prompt
            prompt = f"""
            Create a detailed Nigerian recipe for {meal_name}.
            Return only the JSON object without any markdown formatting or code blocks.
            The response should be a valid JSON object with this structure:
            {{
                "title": "{meal_name}",
                "description": "Brief description including cultural significance and UK-Nigerian fusion notes",
                "prep_time": "30 mins",
                "cook_time": "45 mins",
                "servings": 4,
                "difficulty": "Medium",
                "ingredients": [
                    "List each ingredient with UK measurements",
                    "Include UK store suggestions in parentheses"
                ],
                "instructions": [
                    "Detailed steps with UK-specific notes",
                    "Include temperature in both Celsius and Fahrenheit"
                ],
                "nutrition_info": {{
                    "calories": "per serving",
                    "protein": "in grams",
                    "carbs": "in grams",
                    "fat": "in grams"
                }},
                "tips": [
                    "UK ingredient substitutions",
                    "Storage and reheating advice",
                    "Serving suggestions"
                ]
            }}
            """

            try:
                # Generate recipe using GeminiAssistant
                response = self.gemini_assistant.client.models.generate_content(
                    model=self.gemini_assistant.model,
                    contents=self.gemini_assistant.base_context + "\n" + prompt
                )

                if not response or not response.text:
                    raise ValueError("Empty response from Gemini API")

                # Clean the response text before parsing JSON
                cleaned_response = self._clean_json_response(response.text)
                recipe_data = json.loads(cleaned_response)

                                # Create the recipe
                recipe = Recipe.objects.create(
                        user=request.user,
                        meal_plan=meal_plan,
                        meal_type=meal_type,
                        day_index=day_index,
                        title=recipe_data['title'],
                        description=recipe_data['description'],
                        ingredients=json.dumps(recipe_data['ingredients']),
                        instructions=json.dumps(recipe_data['instructions']),
                        prep_time=recipe_data['prep_time'],
                        cook_time=recipe_data['cook_time'],
                        servings=recipe_data['servings'],
                        difficulty=recipe_data['difficulty'],
                        nutrition_info=recipe_data['nutrition_info'],
                        tips=recipe_data.get('tips', []),
                        is_ai_generated=True
                    )

                    # Return response with isNewlyGenerated flag
                return JsonResponse({
                    'title': recipe.title,
                    'description': self.gemini_assistant.format_response(recipe.description),
                    'prepTime': recipe.prep_time,
                    'cookTime': recipe.cook_time,
                    'servings': recipe.servings,
                    'difficulty': recipe.difficulty,
                    'ingredients': [
                        self.gemini_assistant.format_response(ingredient)
                        for ingredient in recipe.ingredients_list
                    ],
                    'instructions': [
                        self.gemini_assistant.format_response(instruction)
                        for instruction in recipe.instructions_list
                    ],
                    'nutrition': recipe.nutrition_info,
                    'tips': [
                        self.gemini_assistant.format_response(tip)
                        for tip in recipe.tips
                    ],
                    'isNewlyGenerated': True  # Add this flag
                })

            except Exception as e:
                logger.error(f"Error in RecipeDetailsView: {str(e)}", exc_info=True)
                return JsonResponse({
                    'error': 'An error occurred while generating the recipe'
                }, status=500)

        except Exception as e:
            logger.error(f"Error in RecipeDetailsView: {str(e)}", exc_info=True)
            return JsonResponse({
                'error': 'An error occurred while generating the recipe'
            }, status=500)
            
                       


class UserProfileView(LoginRequiredMixin, View):
    def get(self, request):
        # Get all user data with efficient queries
        user_data = {
            'activities': UserActivity.objects.filter(user=request.user),
            # 'active_subscription': UserSubscription.get_active_subscription(request.user.id),
            'purchases': UserSubscription.objects.filter(
                user=request.user
            ).select_related('subscription_tier').order_by('-start_date')
        }

        # Handle activity filters
        filters = self._handle_filters(request, user_data['activities'])

        # Paginate activities
        activities_page = self._paginate_activities(
            request,
            filters['filtered_activities']
        )

        context = {
            'user': request.user,
            # 'subscription': user_data['active_subscription'],
            'purchases': user_data['purchases'],
            'recent_activity': activities_page,
            'is_paginated': True,
            'action_types': UserActivity.ACTION_CHOICES,
            'current_filters': filters['current_filters'],
            # Add subscription stats
            'subscription_stats': self._get_subscription_stats(user_data['purchases'])
        }

        return render(request, 'user_profile.html', context)

    def _handle_filters(self, request, activities):
        """Handle activity filtering"""
        current_filters = {
            'search': request.GET.get('search', ''),
            'action_type': request.GET.get('action_type', ''),
            'date_filter': request.GET.get('date_filter', '')
        }

        filtered_activities = activities

        # Search filter
        if current_filters['search']:
            filtered_activities = filtered_activities.filter(
                Q(action__icontains=current_filters['search']) |
                Q(details__icontains=current_filters['search'])
            )

        # Action type filter
        if current_filters['action_type'] and current_filters['action_type'] != 'all':
            filtered_activities = filtered_activities.filter(
                action=current_filters['action_type']
            )

        # Date filter
        if current_filters['date_filter']:
            today = timezone.now()
            date_filters = {
                'today': today.date(),
                'week': today - timedelta(days=7),
                'month': today - timedelta(days=30)
            }

            if current_filters['date_filter'] == 'today':
                filtered_activities = filtered_activities.filter(
                    timestamp__date=date_filters['today']
                )
            else:
                filtered_activities = filtered_activities.filter(
                    timestamp__gte=date_filters[current_filters['date_filter']]
                )

        return {
            'filtered_activities': filtered_activities.order_by('-timestamp'),
            'current_filters': current_filters
        }

    def _paginate_activities(self, request, activities, per_page=10):
        """Handle activity pagination"""
        paginator = Paginator(activities, per_page)
        page = request.GET.get('page', 1)

        try:
            activities_page = paginator.page(page)
        except PageNotAnInteger:
            activities_page = paginator.page(1)
        except EmptyPage:
            activities_page = paginator.page(paginator.num_pages)

        return activities_page

    def _get_subscription_stats(self, purchases):
        """Calculate subscription statistics"""
        stats = {
            'total_spent': 0,
            'active_plans': 0,
            'total_purchases': len(purchases),
            'subscription_types': {}
        }

        for purchase in purchases:
            # Calculate total spent
            stats['total_spent'] += float(purchase.subscription_tier.price)

            # Count active plans
            if purchase.status == 'active':
                stats['active_plans'] += 1

            # Count subscription types
            plan_type = purchase.subscription_tier.get_tier_type_display()
            stats['subscription_types'][plan_type] = stats['subscription_types'].get(plan_type, 0) + 1

        return stats



# dashboard/views.py
class RecipeCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = RecipeForm()
        return render(request, 'recipe_form.html', {
            'form': form,
            'title': 'Add Recipe'
        })

    @rate_limit('recipe_create', max_requests=10, timeout=3600)
    def post(self, request):
        form = RecipeForm(request.POST, request.FILES)
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.user = request.user
            recipe.is_admin_recipe = request.user.is_staff  # Only staff can create admin recipes
            recipe.save()

            # Track activity
            UserActivity.objects.create(
                user=request.user,
                action='create_recipe',
                details={'recipe_id': recipe.id, 'title': recipe.title}
            )

            # Invalidate relevant caches
            cache.delete_many([
                f"user_recipes_{request.user.id}",
                f"dashboard_data_{request.user.id}"
            ])

            messages.success(request, "Recipe created successfully!")
            return redirect('recipe_detail', pk=recipe.pk)

        return render(request, 'recipe_form.html', {
            'form': form,
            'title': 'Add Recipe'
        })
    
    
    
    
class RecipeDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
        recipe.delete()
        messages.success(request, "Recipe deleted successfully")
        return JsonResponse({'success': True})
        
    
# dashboard/views.py
class RecipeUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
            form = RecipeForm(instance=recipe)
            return render(request, 'recipe_form.html', {
                'form': form,
                'title': 'Edit Recipe',
                'recipe': recipe,
                'editing': True
            })
        except Exception as e:
            logger.error(f"Error in recipe edit view: {str(e)}", exc_info=True)
            messages.error(request, "Unable to load recipe for editing.")
            return redirect('recipe_list')

    @rate_limit('recipe_update', max_requests=10, timeout=3600)
    def post(self, request, pk):
        try:
            recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
            form = RecipeForm(request.POST, instance=recipe)

            if form.is_valid():
                recipe = form.save(commit=False)
                recipe.user = request.user
                recipe.save()

                # Track activity
                UserActivity.objects.create(
                    user=request.user,
                    action='update_recipe',
                    details={
                        'recipe_id': recipe.id,
                        'title': recipe.title,
                        'updated_at': timezone.now().isoformat()
                    }
                )

                # Invalidate relevant caches
                cache_keys = [
                    f"recipe_detail_{pk}_{request.user.id}",
                    f"user_recipes_{request.user.id}",
                    f"dashboard_data_{request.user.id}"
                ]
                cache.delete_many(cache_keys)

                messages.success(request, "Recipe updated successfully!")
                return redirect('recipe_detail', pk=recipe.pk)

            return render(request, 'recipe_form.html', {
                'form': form,
                'title': 'Edit Recipe',
                'recipe': recipe,
                'editing': True
            })

        except Exception as e:
            logger.error(f"Error updating recipe {pk}: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while updating the recipe.")
            return render(request, 'recipe_form.html', {
                'form': form,
                'title': 'Edit Recipe',
                'recipe': recipe,
                'editing': True
            })



class ShoppingListView(LoginRequiredMixin, View):
    def get(self, request):
        cache_key = f"shopping_list_{request.user.id}"
        grocery_list = cache.get(cache_key)

        if not grocery_list:
            grocery_list = GroceryList.objects.filter(
                user=request.user
            ).order_by('-created_at').first()
            if grocery_list:
                cache.set(cache_key, grocery_list, CACHE_TIMEOUTS['short'])

        return render(request, 'shopping_list.html', {
            'grocery_list': grocery_list
        })



class ExportMealPlanView(LoginRequiredMixin, View):
    @rate_limit('export_pdf', max_requests=5, timeout=3600)
    def get(self, request, pk):
        try:
            meal_plan = get_object_or_404(MealPlan, pk=pk, user=request.user)

            # Create DataFrame from meal plan data
            meal_data = self._parse_meal_plan(meal_plan.description)
            df = pd.DataFrame(meal_data)

            # Create PDF buffer
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )

            # Build PDF content
            elements = self._build_pdf_elements(meal_plan, df)
            doc.build(elements)

            # Prepare response
            pdf = buffer.getvalue()
            buffer.close()

            # Create response
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="meal_plan_{pk}.pdf"'
            response.write(pdf)

            # Log activity
            UserActivity.log_activity(
                user=request.user,
                action='export_meal',
                details={
                    'meal_plan_id': meal_plan.id,
                    'meal_plan_name': meal_plan.name
                },
                request=request
            )

            return response

        except Exception as e:
            logger.error(f"Error exporting meal plan: {str(e)}", exc_info=True)
            messages.error(request, "Failed to export meal plan. Please try again.")
            return redirect('dashboard')

    def _parse_meal_plan(self, description):
        """Parse meal plan description into structured data"""
        meal_data = []
        current_day = None

        for line in description.split('\n'):
            line = line.strip()
            if not line:
                continue

            if line.startswith('Day'):
                current_day = line.split(':')[0]
            elif ':' in line and current_day:
                meal_type, meal = line.split(':', 1)
                meal_data.append({
                    'Day': current_day,
                    'Meal Type': meal_type.strip(),
                    'Meal': meal.strip()
                })

        return meal_data

    def _build_pdf_elements(self, meal_plan, df):
        """Build PDF elements using the meal plan DataFrame"""
        styles = getSampleStyleSheet()
        elements = []

        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1
        )

        # Add title
        elements.append(Paragraph(f"Meal Plan: {meal_plan.name}", title_style))
        elements.append(Spacer(1, 20))

        # Add creation date
        elements.append(Paragraph(
            f"Created on: {meal_plan.created_at.strftime('%B %d, %Y')}",
            styles['Normal']
        ))
        elements.append(Spacer(1, 20))

        # Create meal plan table
        table_data = [['Day', 'Meal Type', 'Meal']]
        table_data.extend(df.values.tolist())

        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ])

        meal_table = Table(table_data)
        meal_table.setStyle(table_style)
        elements.append(meal_table)
        elements.append(Spacer(1, 20))

        # Add grocery list if available
        grocery_list = GroceryList.objects.filter(
            user=meal_plan.user
        ).order_by('-created_at').first()

        if grocery_list:
            elements.append(Paragraph("Grocery List", styles['Heading2']))
            elements.append(Spacer(1, 10))

            items = grocery_list.items.split('\n')
            for item in items:
                if item.strip():
                    elements.append(Paragraph(f"• {item.strip()}", styles['Normal']))
                    elements.append(Spacer(1, 5))

        return elements

class FeedbackView(LoginRequiredMixin, View):
    def get(self, request):
        form = FeedbackForm()
        return render(request, 'feedback.html', {'form': form})

    @rate_limit('feedback', max_requests=3, timeout=3600)
    def post(self, request):
        try:
            form = FeedbackForm(request.POST)
            if form.is_valid():
                feedback = form.save(commit=False)
                feedback.user = request.user
                feedback.save()

                # Track activity
                UserActivity.objects.create(
                    user=request.user,
                    action='feedback',
                    details={
                        'feedback_type': feedback.feedback_type,
                        'subject': feedback.subject
                    }
                )

                messages.success(
                    request,
                    "Thank you for your feedback! We'll review it shortly."
                )
                return redirect('dashboard')

            return render(request, 'feedback.html', {'form': form})

        except Exception as e:
            messages.error(
                request,
                "An error occurred while submitting your feedback. Please try again."
            )
            return render(request, 'feedback.html', {'form': form})


class LogoutView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            # Track activity before logout
            UserActivity.objects.create(
                user=request.user,
                action='logout',
                details={'ip': request.META.get('REMOTE_ADDR', '')}
            )

            # Perform logout
            logout(request)
            messages.success(request, "You have been successfully logged out.")
            return redirect('home')

        except Exception as e:
            messages.error(
                request,
                "An error occurred during logout. Please try again."
            )
            return redirect('dashboard')



class ExportMealPlanPDF(LoginRequiredMixin, View):
    def get(self, request, meal_plan_id):
        meal_plan = get_object_or_404(MealPlan, id=meal_plan_id, user=request.user)

        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Add content
        elements.append(Paragraph("Your Meal Plan", styles['Title']))

        # Add meal plan table
        data = [['Day', 'Breakfast', 'Lunch', 'Snack', 'Dinner']]
        for day in json.loads(meal_plan.content):
            data.append([
                day['day'],
                day['meals']['breakfast'],
                day['meals']['lunch'],
                day['meals'].get('snack', ''),
                day['meals']['dinner']
            ])

        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t)

        doc.build(elements)
        buffer.seek(0)

        return FileResponse(
            buffer,
            as_attachment=True,
            filename=f'meal_plan_{meal_plan_id}.pdf'
        )


@login_required
def checkout_success(request):
    """Handle successful checkout"""
    # Get latest subscription
    subscription = UserSubscription.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('subscription_tier').first()

    return render(request, 'checkout_success.html', {
        'title': 'Payment Successful',
        # 'subscription': subscription
    })



@login_required
def checkout_cancel(request):
    """Handle cancelled checkout"""
    messages.warning(request, 'Your payment was cancelled.')
    return render(request, 'checkout_cancel.html', {
        'title': 'Payment Cancelled',
    })

@login_required
def export_activity_pdf(request, activity_id):
    activity = get_object_or_404(UserActivity, id=activity_id, user=request.user)

    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Add content to PDF
    elements.append(Paragraph(f"Activity Details", styles['Title']))
    elements.append(Spacer(1, 12))

    # Add activity details
    elements.append(Paragraph(f"Type: {activity.get_action_display()}", styles['Normal']))
    elements.append(Paragraph(f"Date: {activity.timestamp.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))

    if activity.details:
        elements.append(Paragraph("Details:", styles['Heading2']))
        for key, value in activity.details.items():
            elements.append(Paragraph(f"{key}: {value}", styles['Normal']))

    # Build PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    # Create response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="activity_{activity_id}.pdf"'
    response.write(pdf)

    return response

@login_required
def activity_detail_api(request, activity_id):
    try:
        activity = get_object_or_404(UserActivity, id=activity_id, user=request.user)

        # Base response data
        response_data = {
            'id': activity.id,
            'action': activity.get_action_display(),
            'timestamp': activity.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'details': activity.details
        }

        # If this is a meal plan activity
        if 'meal' in activity.action:
            meal_plan_id = activity.details.get('meal_plan_id')
            if meal_plan_id:
                try:
                    meal_plan = MealPlan.objects.get(id=meal_plan_id)
                    meal_data = json.loads(meal_plan.description)

                    # Structure for the meal plan data
                    structured_days = []

                    # Process each day in the meal plan
                    for day_index, day_data in enumerate(meal_data):
                        day_meals = {}

                        # Process each meal type
                        for meal_type in ['breakfast', 'lunch', 'snack', 'dinner']:
                            if meal_type in day_data['meals']:
                                # Get the recipe for this meal
                                recipe = Recipe.objects.filter(
                                    meal_plan=meal_plan,
                                    day_index=day_index,
                                    meal_type=meal_type
                                ).first()

                                day_meals[meal_type] = day_data['meals'][meal_type]

                                if recipe:
                                    day_meals[f'{meal_type}_recipe'] = recipe.id
                                    day_meals[f'{meal_type}_recipe_details'] = {
                                        'title': recipe.title,
                                        'prep_time': recipe.prep_time,
                                        'cook_time': recipe.cook_time,
                                        'servings': recipe.servings,
                                        'difficulty': recipe.difficulty,
                                        'ingredients': recipe.ingredients_list,
                                        'instructions': recipe.instructions_list,
                                        'nutrition_info': recipe.nutrition_info,
                                        'tips': recipe.tips
                                    }

                        structured_days.append({
                            'day': f"Day {day_index + 1}",
                            'meals': day_meals
                        })

                    response_data['meal_plan'] = {
                        'id': meal_plan.id,
                        'name': meal_plan.name,
                        'created_at': meal_plan.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'days': structured_days
                    }

                except MealPlan.DoesNotExist:
                    logger.error(f"Meal plan {meal_plan_id} not found")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in meal plan description")
                except Exception as e:
                    logger.error(f"Error processing meal plan: {str(e)}")

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error in activity_detail_api: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred while fetching activity details'
        }, status=500)



class ActivityListView(LoginRequiredMixin, ListView):
    model = UserActivity
    template_name = 'dashboard/activity_list.html'
    context_object_name = 'activities'
    paginate_by = 10

    def get_queryset(self):
        queryset = UserActivity.objects.filter(user=self.request.user)

        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(action__icontains=search_query) |
                Q(details__icontains=search_query)
            )

        # Filter by action type
        action_type = self.request.GET.get('action_type', '')
        if action_type and action_type != 'all':
            queryset = queryset.filter(action=action_type)

        # Filter by date range
        date_filter = self.request.GET.get('date_filter', '')
        if date_filter:
            today = timezone.now()
            if date_filter == 'today':
                queryset = queryset.filter(timestamp__date=today.date())
            elif date_filter == 'week':
                queryset = queryset.filter(timestamp__gte=today - timedelta(days=7))
            elif date_filter == 'month':
                queryset = queryset.filter(timestamp__gte=today - timedelta(days=30))

        # Sorting
        sort_by = self.request.GET.get('sort', '-timestamp')
        if sort_by not in ['-timestamp', 'timestamp', '-action', 'action']:
            sort_by = '-timestamp'

        return queryset.order_by(sort_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'action_types': UserActivity.ACTION_CHOICES,
            'current_filters': {
                'search': self.request.GET.get('search', ''),
                'action_type': self.request.GET.get('action_type', 'all'),
                'date_filter': self.request.GET.get('date_filter', 'all'),
                'sort': self.request.GET.get('sort', '-timestamp'),
            }
        })
        return context