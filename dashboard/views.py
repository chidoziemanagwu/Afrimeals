from django.views.generic import TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import MealPlan, Recipe, GroceryList, SubscriptionTier, UserSubscription
from django.contrib.auth.models import User
import os
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

class HomeView(TemplateView):
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().get(request, *args, **kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'


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
            # Extract form data with default values for empty fields
            dietary_preferences = request.POST.get('dietary_preferences') or "balanced"
            preferred_cuisine = request.POST.get('preferred_cuisine') or "Contemporary Nigerian"
            health_goals = request.POST.get('health_goals', '')
            allergies = request.POST.get('allergies', '')
            meals_per_day = request.POST.get('meals_per_day') or "3"
            include_snacks = request.POST.get('include_snacks') == 'on'
            plan_days = request.POST.get('plan_days') or "7"
            budget = request.POST.get('budget') or "moderate"
            skill_level = request.POST.get('skill_level') or "Intermediate"
            family_size = request.POST.get('family_size') or "4"

            # Check if requested features require subscription
            premium_features_requested = False
            for premium_feature in ['detailed_nutrition', 'video_recipes', 'detailed_recipes']:
                if request.POST.get(premium_feature):
                    premium_features_requested = True
                    break

            if premium_features_requested and not self.has_active_subscription(request.user):
                return JsonResponse({
                    'success': False,
                    'requires_upgrade': True,
                    'message': 'This feature requires a subscription. Please upgrade to access it.'
                })

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

            # Call OpenAI API - correct format for gpt-3.5-turbo-instruct
            response = client.completions.create(
                model="gpt-3.5-turbo-instruct",
                prompt=prompt,
                max_tokens=2000,  # Increased for longer plans
                temperature=0.7,  # Slightly increased for more variety
            )

            if response:
                full_response = response.choices[0].text.strip()
                parts = full_response.split('GROCERY LIST:')

                if len(parts) < 2:
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid response format from OpenAI'
                    }, status=400)

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
                    user=request.user,
                    name=f"Meal Plan for {dietary_preferences}",
                    description=meal_plan_text
                )

                # Create grocery list
                grocery_items = "\n".join(structured_grocery_list)
                GroceryList.objects.create(
                    user=request.user,
                    items=grocery_items
                )

                return JsonResponse({
                    'success': True,
                    'meal_plan': structured_meal_plan,
                    'grocery_list': structured_grocery_list
                })

            return JsonResponse({
                'success': False,
                'error': 'Failed to generate meal plan'
            }, status=500)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
        

        
class PricingView(TemplateView):
    template_name = 'pricing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_tiers'] = SubscriptionTier.objects.all().order_by('price')
        return context


class CheckoutView(LoginRequiredMixin, View):
    def get(self, request, tier_id):
        tier = get_object_or_404(SubscriptionTier, id=tier_id)
        return render(request, 'checkout.html', {'tier': tier})

    def post(self, request, tier_id):
        tier = get_object_or_404(SubscriptionTier, id=tier_id)

        # Calculate end date based on tier type
        if tier.tier_type == 'one_time':
            end_date = timezone.now() + timedelta(days=1)  # 24 hour access
        elif tier.tier_type == 'weekly':
            end_date = timezone.now() + timedelta(days=7)
        elif tier.tier_type == 'monthly':
            end_date = timezone.now() + timedelta(days=30)
        else:  # Free tier
            end_date = timezone.now() + timedelta(days=3650)  # ~10 years

        # Create subscription
        subscription = UserSubscription.objects.create(
            user=request.user,
            subscription_tier=tier,
            end_date=end_date,
            payment_id='demo_payment_' + str(timezone.now().timestamp())
        )

        return redirect('subscription_success')


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