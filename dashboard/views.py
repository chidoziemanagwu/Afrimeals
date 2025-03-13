import os
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

from dashboard.decorators import rate_limit
from .models import (
    MealPlan, Recipe, GroceryList, SubscriptionTier,
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

class HomeView(TemplateView):
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().get(request, *args, **kwargs)

# dashboard/views.py (update the DashboardView)

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
            subscription = UserSubscription.get_active_subscription(user.id)

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
                'subscription': subscription,
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

class MealGeneratorView(LoginRequiredMixin, View):
    def get(self, request):
        cache_key = f"meal_generator_data_{request.user.id}"
        view_data = cache.get(cache_key)

        if not view_data:
            subscription = UserSubscription.get_active_subscription(request.user.id)
            view_data = {
                'has_subscription': subscription is not None,
                'subscription_tier': subscription.subscription_tier if subscription else None
            }
            cache.set(cache_key, view_data, CACHE_TIMEOUTS['medium'])

        return render(request, 'meal_generator.html', view_data)

    @rate_limit('meal_generator', max_requests=5, timeout=3600)
    def post(self, request):
        try:
            # Extract and validate form data
            form_data = self._extract_form_data(request.POST)

            # Check subscription requirements
            if form_data['premium_features_requested'] and not self._has_active_subscription(request.user):
                return JsonResponse({
                    'success': False,
                    'requires_upgrade': True,
                    'message': 'This feature requires a subscription. Please upgrade to access it.'
                })

            # Generate and process meal plan
            response_data = self._generate_meal_plan(request.user, form_data)

            # Track activity
            UserActivity.objects.create(
                user=request.user,
                action='create_meal',
                details={'meal_plan_type': form_data['dietary_preferences']}
            )

            return JsonResponse(response_data)

        except OpenAIError as e:
            error_message = "We couldn't generate your meal plan. Please try again with different preferences."

            if isinstance(e, RateLimitError):
                error_message = "We're experiencing high demand. Please try again in a few minutes."
            elif isinstance(e, APIError):
                error_message = "Our meal generation service is temporarily unavailable. Please try again later."

            logger.error(f"OpenAI Error: {str(e)}", exc_info=True, extra={
                'user_id': request.user.id,
                'form_data': form_data if 'form_data' in locals() else {}
            })

            return JsonResponse({
                'success': False,
                'error': error_message,
                'details': str(e) if settings.DEBUG else ""
            }, status=500)

        except ValueError as e:
            logger.warning(f"Value Error in meal generator: {str(e)}", extra={
                'user_id': request.user.id
            })

            return JsonResponse({
                'success': False,
                'error': "Please check your meal preferences and try again.",
                'details': str(e) if settings.DEBUG else ""
            }, status=400)

        except Exception as e:
            logger.critical(f"Unexpected error in meal generator: {str(e)}", exc_info=True, extra={
                'user_id': request.user.id
            })

        return JsonResponse({
            'success': False,
            'error': "Something went wrong. Our team has been notified and will fix this soon.",
            'details': str(e) if settings.DEBUG else ""
        }, status=500)

    def _extract_form_data(self, post_data):
        """Extract and validate form data with defaults"""
        return {
            'dietary_preferences': post_data.get('dietary_preferences', 'balanced'),
            'preferred_cuisine': post_data.get('preferred_cuisine', 'Contemporary Nigerian'),
            'health_goals': post_data.get('health_goals', ''),
            'allergies': post_data.get('allergies', ''),
            'meals_per_day': post_data.get('meals_per_day', '3'),
            'include_snacks': post_data.get('include_snacks') == 'on',
            'plan_days': post_data.get('plan_days', '7'),
            'budget': post_data.get('budget', 'moderate'),
            'skill_level': post_data.get('skill_level', 'Intermediate'),
            'family_size': post_data.get('family_size', '4'),
            'premium_features_requested': any(
                post_data.get(feature) for feature in
                ['detailed_nutrition', 'video_recipes', 'detailed_recipes']
            )
        }

    def _has_active_subscription(self, user):
        return UserSubscription.get_active_subscription(user.id) is not None

    def _generate_meal_plan(self, user, form_data):
        """Generate meal plan using OpenAI API"""
        prompt = self._construct_prompt(form_data)
        cache_key = f"meal_plan_{hashlib.md5(prompt.encode()).hexdigest()}"

        # Check cache first
        cached_response = cache.get(cache_key)
        if cached_response:
            return cached_response

        # Generate new meal plan
        response = client.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=2000,
            temperature=0.7,
        )

        if not response:
            raise Exception('Failed to generate meal plan')

        # Process response
        processed_data = self._process_response(response, form_data, user)

        # Cache the response
        cache.set(cache_key, processed_data, CACHE_TIMEOUTS['very_long'])

        return processed_data

    def _construct_prompt(self, form_data):
        """Construct the prompt for OpenAI API"""
        prompt = (
            f"Generate a meal plan for {form_data['plan_days']} days and grocery list "
            f"for a {form_data['dietary_preferences']} diet with {form_data['preferred_cuisine']} cuisine.\n"
        )

        if form_data['health_goals']:
            prompt += f"Health goals: {form_data['health_goals']}.\n"

        if form_data['allergies']:
            prompt += f"Allergies and restrictions: {form_data['allergies']}.\n"

        prompt += (
            f"Include {form_data['meals_per_day']} meals per day.\n"
            f"{'Include a snack for each day.' if form_data['include_snacks'] else ''}\n"
            f"Budget: {form_data['budget']}.\n"
            f"Skill level: {form_data['skill_level']}.\n"
            f"Family size: {form_data['family_size']}.\n\n"
            "Please format the response exactly as follows:\n"
            "MEAL PLAN:\n"
        )

        # Add day-by-day format
        for day in range(1, int(form_data['plan_days']) + 1):
            prompt += f"Day {day}:\n"
            prompt += "Breakfast: [breakfast meal]\n"
            prompt += "Lunch: [lunch meal]\n"
            if form_data['include_snacks']:
                prompt += "Snack: [snack food]\n"
            prompt += "Dinner: [dinner meal]\n\n"

        prompt += "GROCERY LIST:\n[List each ingredient on a new line with a - in front]"

        return prompt
    def _process_response(self, response, form_data, user):
        """Process OpenAI response into structured data and save to database"""
        full_response = response.choices[0].text.strip()
        parts = full_response.split('GROCERY LIST:')

        if len(parts) < 2:
            raise ValueError('Invalid response format from OpenAI')

        meal_plan_text = parts[0].replace('MEAL PLAN:', '').strip()
        grocery_list_text = parts[1].strip()

        # Process meal plan into structured data
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

        # Process grocery list into structured data
        structured_grocery_list = [
            item.strip('- ').strip()
            for item in grocery_list_text.split('\n')
            if item.strip()
        ]

        # Save to database
        meal_plan = MealPlan.objects.create(
            user=user,
            name=f"Meal Plan for {form_data['dietary_preferences']}",
            description=json.dumps(structured_meal_plan)  # Store as JSON string
        )

        # Create grocery list
        grocery_items = "\n".join(structured_grocery_list)
        GroceryList.objects.create(
            user=user,
            items=grocery_items
        )

        return {
            'success': True,
            'meal_plan_id': meal_plan.id,  # Include the meal plan ID in response
            'meal_plan': structured_meal_plan,
            'grocery_list': structured_grocery_list
        }



class PricingView(TemplateView):
    template_name = 'pricing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cache_key = 'active_subscription_tiers'

        subscription_tiers = cache.get(cache_key)
        if not subscription_tiers:
            subscription_tiers = SubscriptionTier.objects.filter(
                is_active=True
            ).order_by('price')
            cache.set(cache_key, subscription_tiers, CACHE_TIMEOUTS['long'])

        context['subscription_tiers'] = subscription_tiers
        context['stripe_public_key'] = settings.STRIPE_PUBLISHABLE_KEY
        return context


class CheckoutView(View):
    def get(self, request, tier_id):
        try:
            tier = SubscriptionTier.objects.get(id=tier_id)

            # Check if user already has an active subscription
            if hasattr(request.user, 'subscription') and request.user.subscription.is_active:
                return render(request, 'checkout_error.html', {
                    'error': 'You already have an active subscription'
                })

            return render(request, 'checkout.html', {
                'tier': tier,
                'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY
            })
        except SubscriptionTier.DoesNotExist:
            logger.error(f"Subscription tier {tier_id} not found")
            return render(request, 'checkout_error.html', {
                'error': 'Selected subscription plan not found'
            })

    def post(self, request, tier_id):
        try:
            tier = SubscriptionTier.objects.get(id=tier_id)

            # Use stored Stripe price ID if available
            if tier.stripe_price_id:
                checkout_session = self._create_checkout_session_with_price_id(request, tier)
            else:
                checkout_session = self._create_checkout_session_with_price_data(request, tier)

            return JsonResponse({'sessionId': checkout_session.id})

        except SubscriptionTier.DoesNotExist:
            logger.error(f"Subscription tier {tier_id} not found during checkout")
            return JsonResponse({'error': 'Subscription tier not found'}, status=404)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error during checkout: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error during checkout: {str(e)}")
            return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

    def _create_checkout_session_with_price_id(self, request, tier):
        """Create checkout session using stored Stripe price ID"""
        return stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': tier.stripe_price_id,
                'quantity': 1,
            }],
            mode='payment' if tier.tier_type == 'one_time' else 'subscription',
            success_url=request.build_absolute_uri(reverse('checkout_success')),
            cancel_url=request.build_absolute_uri(reverse('checkout_cancel')),
            metadata=self._get_metadata(request, tier),
            customer_email=request.user.email
        )

    def _create_checkout_session_with_price_data(self, request, tier):
        """Create checkout session using price data"""
        price_data = self._get_price_data(tier)
        return stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': price_data,
                'quantity': 1,
            }],
            mode='payment' if tier.tier_type == 'one_time' else 'subscription',
            success_url=request.build_absolute_uri(reverse('checkout_success')),
            cancel_url=request.build_absolute_uri(reverse('checkout_cancel')),
            metadata=self._get_metadata(request, tier),
            customer_email=request.user.email
        )

    def _get_price_data(self, tier):
        """Generate price data based on tier type"""
        base_price_data = {
            'currency': 'gbp',
            'unit_amount': int(float(tier.price) * 100),
            'product_data': {
                'name': tier.name,
                'description': f'{tier.tier_type.capitalize()} plan - {tier.name}',
            }
        }

        if tier.tier_type != 'one_time':
            base_price_data['recurring'] = {
                'interval': 'week' if tier.tier_type == 'weekly' else 'month',
                'interval_count': 1
            }

        return base_price_data

    def _get_metadata(self, request, tier):
        """Generate metadata for the checkout session"""
        return {
            'user_id': str(request.user.id),
            'tier_id': str(tier.id),
            'tier_type': tier.tier_type,
            'email': request.user.email
        }

    @staticmethod
    def handle_successful_payment(session):
        """Handle successful payment webhook"""
        try:
            user_id = session.metadata.get('user_id')
            tier_id = session.metadata.get('tier_id')

            user = User.objects.get(id=user_id)
            tier = SubscriptionTier.objects.get(id=tier_id)

            # Update or create subscription
            subscription, created = Subscription.objects.update_or_create(
                user=user,
                defaults={
                    'tier': tier,
                    'is_active': True,
                    'stripe_subscription_id': session.subscription,
                    'stripe_customer_id': session.customer,
                    'current_period_end': None  # Set this based on webhook data
                }
            )

            logger.info(f"Successfully processed payment for user {user_id}")
            return subscription

        except Exception as e:
            logger.error(f"Error processing successful payment: {str(e)}")
            raise
        
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_subscription'] = UserSubscription.get_active_subscription(
            self.request.user.id
        ) is not None
        return context


class RecipeDetailsView(LoginRequiredMixin, View):
    def get(self, request, meal_plan_id, day_index, meal_type):
        try:
            meal_plan = get_object_or_404(MealPlan, id=meal_plan_id, user=request.user)
            meal_data = json.loads(meal_plan.description)
            meal_name = meal_data[day_index]['meals'][meal_type]

            # Generate recipe using GPT-4
            prompt = f"""
            Generate a detailed Nigerian recipe for {meal_name}. Format the response as JSON with the following structure:
            {{
                "description": "Brief description and cultural significance of the dish",
                "prep_time": "Preparation time in minutes",
                "cook_time": "Cooking time in minutes",
                "servings": "Number of servings (integer)",
                "difficulty": "Cooking difficulty level",
                "ingredients": ["List of ingredients with quantities"],
                "instructions": ["Step by step cooking instructions"],
                "nutrition_info": {{
                    "calories": "per serving",
                    "protein": "in grams",
                    "carbs": "in grams",
                    "fat": "in grams",
                    "fiber": "in grams"
                }},
                "tips": ["Traditional cooking tips and variations"]
            }}
            """

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert Nigerian chef."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )

            recipe_data = json.loads(response.choices[0].message.content)

            # Save the recipe to the database
            recipe = Recipe.objects.create(
                user=request.user,
                meal_plan=meal_plan,
                meal_type=meal_type,
                day_index=day_index,
                title=meal_name,
                description=recipe_data['description'],
                prep_time=recipe_data['prep_time'],
                cook_time=recipe_data['cook_time'],
                servings=recipe_data['servings'],
                difficulty=recipe_data['difficulty'],
                ingredients=recipe_data['ingredients'],
                instructions=recipe_data['instructions'],
                nutrition_info=recipe_data['nutrition_info'],
                tips=recipe_data['tips']
            )

            # Track recipe generation
            UserActivity.objects.create(
                user=request.user,
                action='create_recipe',
                details={
                    'meal_plan_id': meal_plan_id,
                    'meal_type': meal_type,
                    'day_index': day_index,
                    'recipe_id': recipe.id
                }
            )

            # Return recipe details
            return JsonResponse({
                'title': recipe.title,
                'description': recipe.description,
                'prepTime': recipe.prep_time,
                'cookTime': recipe.cook_time,
                'servings': recipe.servings,
                'difficulty': recipe.difficulty,
                'ingredients': recipe.ingredients,
                'instructions': recipe.instructions,
                'nutrition': recipe.nutrition_info,
                'tips': recipe.tips
            })

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}", exc_info=True)
            return JsonResponse({
                'error': 'Invalid recipe data format'
            }, status=400)
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
            return JsonResponse({
                'error': 'Failed to generate recipe. Please try again.'
            }, status=500)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return JsonResponse({
                'error': 'An unexpected error occurred'
            }, status=500)




class UserProfileView(LoginRequiredMixin, View):
    def get(self, request):
        # Get base queryset
        activities = UserActivity.objects.filter(user=request.user)

        # Handle search
        search_query = request.GET.get('search', '')
        if search_query:
            activities = activities.filter(
                Q(action__icontains=search_query) |
                Q(details__icontains=search_query)
            )

        # Handle action type filter
        action_type = request.GET.get('action_type', '')
        if action_type and action_type != 'all':
            activities = activities.filter(action=action_type)

        # Handle date filter
        date_filter = request.GET.get('date_filter', '')
        if date_filter:
            today = timezone.now()
            if date_filter == 'today':
                activities = activities.filter(timestamp__date=today.date())
            elif date_filter == 'week':
                activities = activities.filter(timestamp__gte=today - timedelta(days=7))
            elif date_filter == 'month':
                activities = activities.filter(timestamp__gte=today - timedelta(days=30))

        # Sort activities
        activities = activities.order_by('-timestamp')

        # Paginate activities
        paginator = Paginator(activities, 10)  # 10 items per page
        page = request.GET.get('page', 1)
        try:
            activities_page = paginator.page(page)
        except PageNotAnInteger:
            activities_page = paginator.page(1)
        except EmptyPage:
            activities_page = paginator.page(paginator.num_pages)

        # Get other context data
        subscription = UserSubscription.get_active_subscription(request.user.id)

        context = {
            'user': request.user,
            'subscription': subscription,
            'recent_activity': activities_page,
            'is_paginated': True,
            'action_types': UserActivity.ACTION_CHOICES,
            'current_filters': {
                'search': search_query,
                'action_type': action_type,
                'date_filter': date_filter,
            }
        }

        return render(request, 'user_profile.html', context)   


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
    return render(request, 'checkout_success.html', {
        'title': 'Payment Successful',
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
    activity = get_object_or_404(UserActivity, id=activity_id, user=request.user)

    data = {
        'id': activity.id,
        'action': activity.get_action_display(),
        'timestamp': activity.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'details': activity.details
    }

    return JsonResponse(data)
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