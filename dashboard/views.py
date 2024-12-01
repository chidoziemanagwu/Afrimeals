import os
from django.views.generic import TemplateView, RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import render_to_string
from openai import OpenAI

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
      snacks_per_day = request.POST.get('snacks_per_day')
      budget = request.POST.get('budget')
      skill_level = request.POST.get('skill_level')
      prep_time = request.POST.get('prep_time')
      family_size = request.POST.get('family_size')
      preferred_ingredients = request.POST.get('preferred_ingredients')
      disliked_ingredients = request.POST.get('disliked_ingredients')
      meal_types = request.POST.get('meal_types')

      # Call ChatGPT API
      prompt = (
          f"Generate a meal plan and grocery list for a {dietary_preferences} diet with {preferred_cuisine} cuisine. "
          f"Health goals: {health_goals}. Allergies: {allergies}. "
          f"Meals per day: {meals_per_day}, Snacks per day: {snacks_per_day}. "
          f"Budget: {budget}. Skill level: {skill_level}. "
          f"Prep time: {prep_time}. Family size: {family_size}. "
          f"Preferred ingredients: {preferred_ingredients}. Disliked ingredients: {disliked_ingredients}. "
          f"Meal types: {meal_types}."
      )
      response = client.completions.create(
          model = "gpt-3.5-turbo-instruct",
          prompt=prompt,
          max_tokens=150,
          temperature = 0,
      )
      
      if response:
          meal_plan = response.choices[0].text.strip()
          grocery_list = "Extracted grocery list from the response"  # Adjust as needed

          # Render the meal plan and grocery list in the template
          return render(request, 'meal_generator.html', {
              'meal_plan': meal_plan,
              'grocery_list': grocery_list,
          })

      return render(request, 'meal_generator.html', {'error': 'Failed to generate meal plan'})