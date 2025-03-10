from django.views.generic import TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from datetime import timedelta
import json
import stripe
import os
from celery import shared_task

from .models import MealPlan, Recipe, GroceryList, SubscriptionTier, UserSubscription
from django.contrib.auth.models import User
from openai import OpenAI

from celery.result import AsyncResult
import logging
from django.core.cache import cache
from functools import wraps  # Correct

logger = logging.getLogger('dashboard')
# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def simple_rate_limit(key_prefix, requests=5, window=3600):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            cache_key = f"{key_prefix}:{request.user.id}"
            count = cache.get(cache_key, 0)

            if count >= requests:
                return HttpResponse("Rate limit exceeded", status=429)

            cache.set(cache_key, count + 1, window)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# Define Celery task for meal generation
@shared_task
def generate_meal_plan_task(user_id, form_data):
    """Asynchronously generate meal plan using OpenAI"""
    try:
        user = User.objects.get(id=user_id)
        
        # Extract form data
        dietary_preferences = form_data.get('dietary_preferences') or "balanced"
        preferred_cuisine = form_data.get('preferred_cuisine') or "Contemporary Nigerian"
        health_goals = form_data.get('health_goals', '')
        allergies = form_data.get('allergies', '')
        meals_per_day = form_data.get('meals_per_day') or "3"
        include_snacks = form_data.get('include_snacks') == 'on'
        plan_days = form_data.get('plan_days') or "7"
        budget = form_data.get('budget') or "moderate"
        skill_level = form_data.get('skill_level') or "Intermediate"
        family_size = form_data.get('family_size') or "4"

        # Construct the prompt for OpenAI
        prompt = (
            f"Generate a meal plan for {plan_days} days and grocery list for a {dietary_preferences} diet "
            f"with {preferred_cuisine} cuisine. "
        )

        if health_goals:
            prompt += f"Health goals: {health_goals}. "

        if allergies:
            prompt += f"Allergies and restrictions: {allergies}. "

        prompt += (
            f"Include {meals_per_day} meals per day. "
            f"{'' if not include_snacks else 'Include a snack for each day. '}"
            f"Budget: {budget}. Skill level: {skill_level}. "
            f"Family size: {family_size}. "
            f"\n\nPlease format the response exactly as follows:\n"
            f"MEAL PLAN:\n"
        )

        # Include format instructions for specific days
        for day in range(1, int(plan_days) + 1):
            prompt += f"Day {day}:\n"
            prompt += "Breakfast: [breakfast meal]\n"
            prompt += "Lunch: [lunch meal]\n"
            if include_snacks:
                prompt += "Snack: [snack food]\n"
            prompt += "Dinner: [dinner meal]\n\n"

        prompt += "GROCERY LIST:\n[List each ingredient on a new line with a - in front]"

        # Call OpenAI API
        response = client.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=2000,
            temperature=0.7,
        )

        if not response:
            return {
                'success': False,
                'error': 'Failed to generate meal plan'
            }

        full_response = response.choices[0].text.strip()
        parts = full_response.split('GROCERY LIST:')

        if len(parts) < 2:
            return {
                'success': False,
                'error': 'Invalid response format from OpenAI'
            }

        meal_plan_text = parts[0].replace('MEAL PLAN:', '').strip()
        grocery_list = parts[1].strip() if len(parts) > 1 else ''

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
                        'snack': '' if include_snacks else None,
                        'dinner': ''
                    }
                }
                structured_meal_plan.append(current_day)
            elif current_day and ':' in line:
                meal_type, meal = line.split(': ', 1)
                meal_type_lower = meal_type.lower()
                if meal_type_lower in current_day['meals']:
                    current_day['meals'][meal_type_lower] = meal

        # Ensure all days have the expected meal structure
        for day in structured_meal_plan:
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                if not day['meals'].get(meal_type):
                    day['meals'][meal_type] = f"Nigerian {meal_type.capitalize()}"

            # Handle snacks specially
            if include_snacks and not day['meals'].get('snack'):
                day['meals']['snack'] = "Nigerian Snack (e.g., Chin Chin, Plantain Chips)"

        # Process grocery list into structured data
        structured_grocery_list = [
            item.strip('- ').strip()
            for item in grocery_list.split('\n')
            if item.strip()
        ]

        # Save to database
        meal_plan = MealPlan.objects.create(
            user=user,
            name=f"Meal Plan for {dietary_preferences}",
            description=meal_plan_text
        )

        # Create grocery list
        grocery_items = "\n".join(structured_grocery_list)
        GroceryList.objects.create(
            user=user,
            items=grocery_items
        )

        return {
            'success': True,
            'meal_plan': structured_meal_plan,
            'grocery_list': structured_grocery_list
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


class HomeView(TemplateView):
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().get(request, *args, **kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

# Apply the custom rate limiter to your views
@method_decorator(simple_rate_limit(key_prefix='meal_generation', requests=5, window=3600), name='post')
class MealGeneratorView(LoginRequiredMixin, View):
    def get(self, request):
        # Check if user has an active subscription
        has_subscription = self.has_active_subscription(request.user)
        subscription_tier = None

        if has_subscription:
            subscription = UserSubscription.objects.get(
                user=request.user,
                is_active=True,
                end_date__gte=timezone.now()
            )
            subscription_tier = subscription.subscription_tier

        return render(request, 'meal_generator.html', {
            'has_subscription': has_subscription,
            'subscription_tier': subscription_tier
        })

    def has_active_subscription(self, user):
        try:
            subscription = UserSubscription.objects.get(
                user=user,
                is_active=True,
                end_date__gte=timezone.now()
            )
            return True
        except UserSubscription.DoesNotExist:
            return False

    
    def post(self, request):
        try:
            logger.info(f"Meal plan generation requested by user: {request.user.id}")

            # Extract form data
            form_data = {}
            for key, value in request.POST.items():
                form_data[key] = value

            # Check if requested features require subscription
            premium_features_requested = False
            for premium_feature in ['detailed_nutrition', 'video_recipes', 'detailed_recipes']:
                if request.POST.get(premium_feature):
                    premium_features_requested = True
                    break

            if premium_features_requested and not self.has_active_subscription(request.user):
                logger.warning(f"User {request.user.id} attempted to access premium features without subscription")
                return JsonResponse({
                    'success': False,
                    'requires_upgrade': True,
                    'message': 'This feature requires a subscription. Please upgrade to access it.'
                })

            # Launch Celery task for asynchronous processing
            task = generate_meal_plan_task.delay(request.user.id, form_data)

            # Return task ID for frontend to poll
            logger.info(f"Meal plan generation task {task.id} started for user: {request.user.id}")
            return JsonResponse({
                'success': True,
                'status': 'processing',
                'task_id': task.id
            })

        except Exception as e:
            logger.error(f"Error in meal plan generation: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f"An error occurred: {str(e)}"
            }, status=500)    
        
class PricingView(TemplateView):
    template_name = 'pricing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_tiers'] = SubscriptionTier.objects.all().order_by('price')
        context['stripe_publishable_key'] = os.getenv('STRIPE_PUBLISHABLE_KEY')
        return context


class CheckoutView(LoginRequiredMixin, View):
    def get(self, request, tier_id):
        tier = get_object_or_404(SubscriptionTier, id=tier_id)
        return render(request, 'checkout.html', {
            'tier': tier,
            'stripe_publishable_key': os.getenv('STRIPE_PUBLISHABLE_KEY')
        })

    def post(self, request, tier_id):
        tier = get_object_or_404(SubscriptionTier, id=tier_id)
        
        try:
            # Create a product in Stripe if it doesn't exist
            product_name = f"Afrimeals {tier.name}"
            products = stripe.Product.list(name=product_name)
            
            if products.data:
                product = products.data[0]
            else:
                product = stripe.Product.create(
                    name=product_name,
                    description=tier.description
                )
                
            # Create price object based on tier type
            if tier.tier_type == 'one_time':
                price = stripe.Price.create(
                    product=product.id,
                    unit_amount=int(tier.price * 100),  # Convert to cents
                    currency='gbp',
                )
                payment_mode = 'payment'
            else:
                # Subscription price
                interval = 'week' if tier.tier_type == 'weekly' else 'month'
                price = stripe.Price.create(
                    product=product.id,
                    unit_amount=int(tier.price * 100),
                    currency='gbp',
                    recurring={
                        'interval': interval
                    }
                )
                payment_mode = 'subscription'
            
            # Create a checkout session
            success_url = request.build_absolute_uri(reverse('subscription_success'))
            cancel_url = request.build_absolute_uri(reverse('checkout', args=[tier_id]))
            
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price.id,
                    'quantity': 1,
                }],
                mode=payment_mode,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': request.user.id,
                    'tier_id': tier.id,
                    'tier_type': tier.tier_type
                },
            )
            
            # Return the checkout URL
            return JsonResponse({
                'success': True,
                'checkout_url': checkout_session.url
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


class SubscriptionSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'subscription_success.html'


class MySubscriptionView(LoginRequiredMixin, DetailView):
    template_name = 'my_subscription.html'

    def get_object(self):
        subscription = UserSubscription.objects.filter(
            user=self.request.user,
            is_active=True,
            end_date__gt=timezone.now()
        ).first()
        return subscription

# Define endpoint to check task status
def check_task_status(request, task_id):
    """Check the status of an async task"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=403)

    task = AsyncResult(task_id)

    if not task.ready():
        return JsonResponse({
            'status': 'processing'
        })

    result = task.result
    return JsonResponse(result)

def custom_404(request, exception=None):
    return render(request, '404.html', status=404)

def custom_500(request, exception=None):
    return render(request, '500.html', status=500)

    
@method_decorator(csrf_exempt, name='dispatch')
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)
        
    # Handle the event
    event_type = event['type']
    
    if event_type == 'checkout.session.completed':
        session = event['data']['object']
        
        # Extract metadata
        metadata = session.get('metadata', {})
        user_id = metadata.get('user_id')
        tier_id = metadata.get('tier_id')
        tier_type = metadata.get('tier_type')
        
        if not user_id or not tier_id:
            return HttpResponse(status=400)
            
        try:
            user = User.objects.get(id=user_id)
            tier = SubscriptionTier.objects.get(id=tier_id)
            
            # Calculate end date based on tier type
            if tier_type == 'one_time':
                end_date = timezone.now() + timedelta(days=1)  # 24 hour access
            elif tier_type == 'weekly':
                end_date = timezone.now() + timedelta(days=7)
            elif tier_type == 'monthly':
                end_date = timezone.now() + timedelta(days=30)
            else:
                end_date = timezone.now() + timedelta(days=30)  # Default fallback
            
            # Create or update subscription
            UserSubscription.objects.update_or_create(
                user=user,
                subscription_tier=tier,
                defaults={
                    'start_date': timezone.now(),
                    'end_date': end_date,
                    'is_active': True,
                    'payment_id': session.get('payment_intent') or session.get('subscription')
                }
            )
        except (User.DoesNotExist, SubscriptionTier.DoesNotExist) as e:
            return HttpResponse(status=400)
    
    # Handle subscription updates if needed
    elif event_type in ['customer.subscription.updated', 'customer.subscription.deleted']:
        subscription = event['data']['object']
        subscription_id = subscription.get('id')
        
        try:
            user_sub = UserSubscription.objects.get(payment_id=subscription_id)
            
            if event_type == 'customer.subscription.updated':
                # Update subscription status based on Stripe status
                user_sub.is_active = subscription.get('status') == 'active'
                user_sub.save()
            elif event_type == 'customer.subscription.deleted':
                # Mark subscription as inactive
                user_sub.is_active = False
                user_sub.save()
        except UserSubscription.DoesNotExist:
            pass
    
    return HttpResponse(status=200)