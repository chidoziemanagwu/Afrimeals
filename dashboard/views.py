from django.views.generic import TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import SubscriptionTier, UserSubscription
import stripe
import os
from openai import OpenAI  # Ensure OpenAI is imported

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),  # Ensure OPENAI_API_KEY is set in your environment
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
        return render(request, 'meal_generator.html')

    def post(self, request):
        # Extract form data
        dietary_preferences = request.POST.get('dietary_preferences')
        preferred_cuisine = request.POST.get('preferred_cuisine')
        health_goals = request.POST.get('health_goals')
        allergies = request.POST.get('allergies')
        meals_per_day = request.POST.get('meals_per_day')
        budget = request.POST.get('budget')
        skill_level = request.POST.get('skill_level')
        family_size = request.POST.get('family_size')

        # Call OpenAI API
        prompt = (
            f"Generate a meal plan and grocery list for a {dietary_preferences} diet with {preferred_cuisine} cuisine. "
            f"Health goals: {health_goals}. Allergies: {allergies}. "
            f"Meals per day: {meals_per_day}. "
            f"Budget: {budget}. Skill level: {skill_level}. "
            f"Family size: {family_size}. "
            f"Please format the response as follows:\n"
            f"MEAL PLAN:\n[meal plan here]\n\n"
            f"GROCERY LIST:\n[grocery list here]"
        )

        try:
            response = client.completions.create(
                model="gpt-3.5-turbo-instruct",  # Ensure this is the correct model
                prompt=prompt,
                max_tokens=1000,
                temperature=0,
            )

            if response:
                full_response = response.choices[0].text.strip()
                parts = full_response.split('GROCERY LIST:')
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
                                'snack': '',
                                'dinner': ''
                            }
                        }
                        structured_meal_plan.append(current_day)
                    elif current_day and ':' in line:
                        meal_type, meal = line.split(': ', 1)
                        current_day['meals'][meal_type.lower()] = meal

                # Process grocery list into structured data
                structured_grocery_list = [
                    item.strip('- ').strip()
                    for item in grocery_list.split('\n')
                    if item.strip()
                ]

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

        # Create subscription (in a real app, you'd integrate with Stripe or another payment processor here)
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