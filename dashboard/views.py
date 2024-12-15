import os
from django.views.generic import TemplateView, RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import render_to_string
from openai import OpenAI
from django.http import JsonResponse

class HomeView(TemplateView):
  template_name = 'home.html'

  def get(self, request, *args, **kwargs):
      if request.user.is_authenticated:
          return redirect('dashboard')
      return super().get(request, *args, **kwargs)

class DashboardView(LoginRequiredMixin, TemplateView):
  template_name = 'dashboard.html'

class MealGeneratorView(LoginRequiredMixin, TemplateView):
  template_name = 'meal_generator.html'

client = OpenAI(
    api_key = os.getenv("OPENAI_API_KEY"),
)

class MealGeneratorView(View):
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

        # Call ChatGPT API
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
                model="gpt-3.5-turbo-instruct",
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