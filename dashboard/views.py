from django.views.generic import TemplateView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View
from django.http import JsonResponse, HttpResponse
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
import os
from openai import OpenAI
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

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.user.id
        cache_key = f"dashboard_data_{user_id}"

        dashboard_data = cache.get(cache_key)
        if not dashboard_data:
            dashboard_data = {
                'recent_meal_plans': MealPlan.get_user_plans(user_id, limit=5),
                'recent_recipes': Recipe.get_user_recipes(user_id)[:5],
                'subscription': UserSubscription.get_active_subscription(user_id),
                'recent_activity': UserActivity.get_user_recent_activity(user_id, limit=10)
            }
            cache.set(cache_key, dashboard_data, CACHE_TIMEOUTS['short'])

        context.update(dashboard_data)
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
        grocery_list = parts[1].strip()

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

        # Ensure all days have the expected meal structure
        for day in structured_meal_plan:
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                if not day['meals'].get(meal_type):
                    day['meals'][meal_type] = f"Nigerian {meal_type.capitalize()}"

            if form_data['include_snacks'] and not day['meals'].get('snack'):
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
            name=f"Meal Plan for {form_data['dietary_preferences']}",
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
        return context


class CheckoutView(LoginRequiredMixin, View):
    @rate_limit('checkout', max_requests=5, timeout=3600)
    def get(self, request, tier_id):
        tier = get_object_or_404(SubscriptionTier, id=tier_id, is_active=True)
        return render(request, 'checkout.html', {
            'tier': tier,
            'stripe_public_key': settings.STRIPE_PUBLIC_KEY
        })

    @rate_limit('checkout', max_requests=5, timeout=3600)
    def post(self, request, tier_id):
        tier = get_object_or_404(SubscriptionTier, id=tier_id, is_active=True)
        token = request.POST.get('stripeToken')

        try:
            # Create Stripe customer
            customer = stripe.Customer.create(
                email=request.user.email,
                source=token
            )

            # Handle subscription based on tier type
            if tier.tier_type == 'monthly':
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{'price': tier.stripe_price_id}]
                )
                end_date = timezone.now() + timedelta(days=30)
                payment_id = subscription.id
            elif tier.tier_type == 'weekly':
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{'price': tier.stripe_price_id}]
                )
                end_date = timezone.now() + timedelta(days=7)
                payment_id = subscription.id
            else:
                charge = stripe.Charge.create(
                    customer=customer.id,
                    amount=int(tier.price * 100),
                    currency='gbp',
                    description=f'{tier.name} - One-time payment'
                )
                end_date = timezone.now() + timedelta(days=1)
                payment_id = charge.id

            # Create subscription in database
            UserSubscription.objects.create(
                user=request.user,
                subscription_tier=tier,
                end_date=end_date,
                payment_id=payment_id
            )

            # Track activity
            UserActivity.objects.create(
                user=request.user,
                action='subscription',
                details={'tier': tier.name, 'type': tier.tier_type}
            )

            # Invalidate relevant caches
            cache.delete_many([
                f"user_subscription_{request.user.id}",
                f"dashboard_data_{request.user.id}",
                f"meal_generator_data_{request.user.id}"
            ])

            messages.success(request, f"Successfully subscribed to {tier.name}!")
            return redirect('subscription_success')

        except stripe.error.CardError as e:
            messages.error(request, f"Payment failed: {e.error.message}")
        except Exception as e:
            messages.error(request, "An unexpected error occurred. Please try again.")

        return render(request, 'checkout.html', {
            'tier': tier,
            'stripe_public_key': settings.STRIPE_PUBLIC_KEY
        })


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
    context_object_name = 'recipes'
    paginate_by = 12

    def get_queryset(self):
        cache_key = f"user_recipes_{self.request.user.id}"
        recipes = cache.get(cache_key)

        if not recipes:
            recipes = Recipe.objects.filter(
                user=self.request.user
            ).select_related('user').order_by('-created_at')
            cache.set(cache_key, recipes, CACHE_TIMEOUTS['short'])

        return recipes

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_subscription'] = UserSubscription.get_active_subscription(
            self.request.user.id
        ) is not None
        return context

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

class UserProfileView(LoginRequiredMixin, View):
    def get(self, request):
        cache_key = f"user_profile_{request.user.id}"
        profile_data = cache.get(cache_key)

        if not profile_data:
            profile_data = {
                'meal_plans': MealPlan.objects.filter(
                    user=request.user
                ).order_by('-created_at')[:5],
                'subscription': UserSubscription.get_active_subscription(request.user.id),
                'recent_activity': UserActivity.objects.filter(
                    user=request.user
                ).select_related('user').order_by('-timestamp')[:10]
            }
            cache.set(cache_key, profile_data, CACHE_TIMEOUTS['short'])

        return render(request, 'user_profile.html', {
            'user': request.user,
            **profile_data
        })

class RecipeCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = RecipeForm()
        return render(request, 'recipe_form.html', {
            'form': form,
            'title': 'Add Recipe'
        })

    @rate_limit('recipe_create', max_requests=10, timeout=3600)
    def post(self, request):
        form = RecipeForm(request.POST)
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.user = request.user
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

class RecipeUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
        form = RecipeForm(instance=recipe)
        return render(request, 'recipe_form.html', {
            'form': form,
            'title': 'Edit Recipe'
        })

    @rate_limit('recipe_update', max_requests=10, timeout=3600)
    def post(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
        form = RecipeForm(request.POST, instance=recipe)
        if form.is_valid():
            form.save()

            # Invalidate relevant caches
            cache.delete_many([
                f"recipe_detail_{pk}_{request.user.id}",
                f"user_recipes_{request.user.id}"
            ])

            messages.success(request, "Recipe updated successfully!")
            return redirect('recipe_detail', pk=recipe.pk)

        return render(request, 'recipe_form.html', {
            'form': form,
            'title': 'Edit Recipe'
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



class ExportMealPlanPDFView(LoginRequiredMixin, View):
    @rate_limit('export_pdf', max_requests=5, timeout=3600)
    def get(self, request, pk):
        try:
            meal_plan = get_object_or_404(MealPlan, pk=pk, user=request.user)

            # Create PDF buffer
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                title=f"Meal Plan - {meal_plan.name}"
            )

            # Define styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30
            )
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=18,
                spaceAfter=12
            )
            normal_style = styles['Normal']

            # Build document elements
            elements = []

            # Add title
            elements.append(Paragraph(f"Meal Plan: {meal_plan.name}", title_style))
            elements.append(Spacer(1, 20))

            # Add description
            elements.append(Paragraph("Description:", heading_style))
            elements.append(Paragraph(meal_plan.description, normal_style))
            elements.append(Spacer(1, 20))

            # Add grocery list if available
            grocery_list = GroceryList.objects.filter(
                user=request.user
            ).order_by('-created_at').first()

            if grocery_list:
                elements.append(Paragraph("Grocery List:", heading_style))
                items = grocery_list.items.split('\n')
                for item in items:
                    elements.append(
                        Paragraph(f"• {item.strip()}", normal_style)
                    )

            # Build PDF
            doc.build(elements)

            # Prepare response
            pdf = buffer.getvalue()
            buffer.close()

            # Create response
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = (
                f'attachment; filename="meal_plan_{meal_plan.id}.pdf"'
            )
            response.write(pdf)

            return response

        except Exception as e:
            messages.error(
                request,
                "An error occurred while generating the PDF. Please try again."
            )
            return redirect('dashboard')


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