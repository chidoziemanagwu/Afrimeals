from celery import shared_task
from openai import OpenAI
from .models import MealPlan, GroceryList
from django.contrib.auth.models import User
import os
from datetime import timedelta
from django.utils import timezone

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

@shared_task
def generate_meal_plan(user_id, form_data):
    """Asynchronously generate meal plan using OpenAI"""
    try:
        user = User.objects.get(id=user_id)

        # Extract form data with default values for empty fields
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

        # Call OpenAI API - correct format for gpt-3.5-turbo-instruct
        response = client.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=2000,  # Increased for longer plans
            temperature=0.7,  # Slightly increased for more variety
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