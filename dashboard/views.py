from django.views.generic import TemplateView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from dashboard.decorators import rate_limit
from .models import MealPlan, Recipe, GroceryList, SubscriptionTier, UserSubscription
from django.contrib.auth.models import User
import os
from openai import OpenAI
from django.core.cache import cache
import hashlib
from .forms import FeedbackForm, RecipeForm
import stripe
from django.conf import settings
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from django.contrib.auth import logout
from django.contrib.auth.views import LogoutView


stripe.api_key = settings.STRIPE_SECRET_KEY

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
        # Rate limiting implementation (keep your existing code)
        user_id = request.user.id
        cache_key = f"meal_generator_rate_{user_id}"
        request_count = cache.get(cache_key, 0)

        # Limit to 5 requests per hour
        if request_count >= 5:
            return JsonResponse({
                'success': False,
                'error': 'Rate limit exceeded. Please try again later.'
            }, status=429)

        # Increment the counter
        cache.set(cache_key, request_count + 1, 60*60)  # 1 hour expiry

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

            # Create a cache key based on the prompt
            import hashlib
            cache_key = f"meal_plan_{hashlib.md5(prompt.encode()).hexdigest()}"

            # Try to get cached response
            cached_response = cache.get(cache_key)
            if cached_response:
                # If we have a cached response, return it directly
                return JsonResponse(cached_response)

            # If no cached response, call OpenAI API
            response = client.completions.create(
                model="gpt-3.5-turbo-instruct",
                prompt=prompt,
                max_tokens=2000,
                temperature=0.7,
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

                # Prepare response data
                response_data = {
                    'success': True,
                    'meal_plan': structured_meal_plan,
                    'grocery_list': structured_grocery_list
                }

                # Cache the response for 24 hours (86400 seconds)
                cache.set(cache_key, response_data, 86400)

                return JsonResponse(response_data)

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
    
# In views.py
class RecipeListView(LoginRequiredMixin, ListView):
    model = Recipe
    template_name = 'recipes.html'
    context_object_name = 'recipes'
    paginate_by = 12
    
    def get_queryset(self):
        return Recipe.objects.filter(user=self.request.user).order_by('-id')

class RecipeDetailView(LoginRequiredMixin, DetailView):
    model = Recipe
    template_name = 'recipe_detail.html'
    context_object_name = 'recipe'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional context data here
        return context
    
# In views.py
class UserProfileView(LoginRequiredMixin, View):
    def get(self, request):
        # Get user's meal plans
        meal_plans = MealPlan.objects.filter(user=request.user).order_by('-created_at')[:5]

        # Get user's subscription
        subscription = UserSubscription.objects.filter(
            user=request.user,
            is_active=True,
            end_date__gt=timezone.now()
        ).first()

        return render(request, 'user_profile.html', {
            'user': request.user,
            'meal_plans': meal_plans,
            'subscription': subscription,
        })
    
class RecipeCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = RecipeForm()
        return render(request, 'recipe_form.html', {'form': form, 'title': 'Add Recipe'})


    @rate_limit('recipe_create', max_requests=10, timeout=3600)  # 10 requests per hour
    def post(self, request):
        form = RecipeForm(request.POST)
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.user = request.user
            recipe.save()
            return redirect('recipe_detail', pk=recipe.pk)
        return render(request, 'recipe_form.html', {'form': form, 'title': 'Add Recipe'})

class RecipeUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
        form = RecipeForm(instance=recipe)
        return render(request, 'recipe_form.html', {'form': form, 'title': 'Edit Recipe'})

    @rate_limit('recipe_create', max_requests=10, timeout=3600)  # 10 requests per hour
    def post(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
        form = RecipeForm(request.POST, instance=recipe)
        if form.is_valid():
            form.save()
            return redirect('recipe_detail', pk=recipe.pk)
        return render(request, 'recipe_form.html', {'form': form, 'title': 'Edit Recipe'})
    

# In views.py
class ShoppingListView(LoginRequiredMixin, View):
    def get(self, request):
        # Get user's latest grocery list
        grocery_list = GroceryList.objects.filter(user=request.user).order_by('-created_at').first()

        return render(request, 'shopping_list.html', {
            'grocery_list': grocery_list
        })



class ExportMealPlanPDFView(LoginRequiredMixin, View):
    @rate_limit('recipe_create', max_requests=5, timeout=3600)  # 10 requests per hour
    def get(self, request, pk):
        meal_plan = get_object_or_404(MealPlan, pk=pk, user=request.user)

        # Create a file-like buffer to receive PDF data
        buffer = BytesIO()

        # Create the PDF object, using the buffer as its "file"
        doc = SimpleDocTemplate(buffer, pagesize=letter, title=f"Meal Plan - {meal_plan.name}")

        # Container for the 'Flowable' objects
        elements = []

        # Define styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']

        # Add title
        elements.append(Paragraph(f"Meal Plan: {meal_plan.name}", title_style))
        elements.append(Spacer(1, 12))

        # Add description
        elements.append(Paragraph("Description:", heading_style))
        elements.append(Paragraph(meal_plan.description, normal_style))
        elements.append(Spacer(1, 12))

        # Build the PDF
        doc.build(elements)

        # Get the value of the BytesIO buffer
        pdf = buffer.getvalue()
        buffer.close()

        # Create the HTTP response with PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="meal_plan_{meal_plan.id}.pdf"'
        response.write(pdf)

        return response
    

# dashboard/views.py
class FeedbackView(LoginRequiredMixin, View):
    def get(self, request):
        form = FeedbackForm()
        return render(request, 'feedback.html', {'form': form})

    @rate_limit('feedback', max_requests=3, timeout=3600)  # 3 requests per hour
    def post(self, request):
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.user = request.user
            feedback.save()
            messages.success(request, "Thank you for your feedback!")
            return redirect('dashboard')
        return render(request, 'feedback.html', {'form': form})


        



class CheckoutView(LoginRequiredMixin, View):
    def get(self, request, tier_id):
        tier = get_object_or_404(SubscriptionTier, id=tier_id)
        return render(request, 'checkout.html', {
            'tier': tier,
            'stripe_public_key': settings.STRIPE_PUBLIC_KEY
        })

    @rate_limit('checkout', max_requests=5, timeout=3600)
    def post(self, request, tier_id):
        tier = get_object_or_404(SubscriptionTier, id=tier_id)

        # Get Stripe token
        token = request.POST.get('stripeToken')

        try:
            # Create Stripe customer
            customer = stripe.Customer.create(
                email=request.user.email,
                source=token
            )

            # Create Stripe subscription
            if tier.tier_type == 'monthly':
                # Create a monthly subscription
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{'price': tier.stripe_price_id}],
                )
                end_date = timezone.now() + timedelta(days=30)
            elif tier.tier_type == 'weekly':
                # Create a weekly subscription
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{'price': tier.stripe_price_id}],
                )
                end_date = timezone.now() + timedelta(days=7)
            else:
                # One-time payment
                charge = stripe.Charge.create(
                    customer=customer.id,
                    amount=int(tier.price * 100),  # Convert to cents
                    currency='gbp',
                    description=f'{tier.name} - One-time payment'
                )
                subscription = {'id': charge.id}
                end_date = timezone.now() + timedelta(days=1)

            # Create subscription in database
            UserSubscription.objects.create(
                user=request.user,
                subscription_tier=tier,
                end_date=end_date,
                payment_id=subscription.id
            )

            return redirect('subscription_success')

        except stripe.error.CardError as e:
            # Card was declined
            return render(request, 'checkout.html', {
                'tier': tier,
                'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
                'error': e.error.message
            })