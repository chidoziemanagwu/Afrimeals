# dashboard/tasks.py
from celery import shared_task
from .models import MealPlan, GroceryList, UserActivity, Recipe
from openai import OpenAI
import os
from django.core.cache import cache
import hashlib
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.utils import timezone

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@shared_task
def generate_meal_plan_async(user_id, form_data):
    """Asynchronous task to generate meal plan using OpenAI API"""
    try:
        # Extract form data
        dietary_preferences = form_data.get('dietary_preferences', 'balanced')
        preferred_cuisine = form_data.get('preferred_cuisine', 'Contemporary Nigerian')
        health_goals = form_data.get('health_goals', '')
        allergies = form_data.get('allergies', '')
        meals_per_day = form_data.get('meals_per_day', '3')
        include_snacks = form_data.get('include_snacks') == 'on'
        plan_days = form_data.get('plan_days', '7')
        budget = form_data.get('budget', 'moderate')
        skill_level = form_data.get('skill_level', 'Intermediate')
        family_size = form_data.get('family_size', '4')

        # Construct prompt
        prompt = (
            f"Generate a meal plan for {plan_days} days and grocery list "
            f"for a {dietary_preferences} diet with {preferred_cuisine} cuisine.\n"
        )

        if health_goals:
            prompt += f"Health goals: {health_goals}.\n"
        if allergies:
            prompt += f"Allergies and restrictions: {allergies}.\n"

        prompt += (
            f"Include {meals_per_day} meals per day.\n"
            f"{'Include a snack for each day.' if include_snacks else ''}\n"
            f"Budget: {budget}.\n"
            f"Skill level: {skill_level}.\n"
            f"Family size: {family_size}.\n\n"
            "Please format the response exactly as follows:\n"
            "MEAL PLAN:\n"
        )

        # Add day-by-day format
        for day in range(1, int(plan_days) + 1):
            prompt += f"Day {day}:\n"
            prompt += "Breakfast: [breakfast meal]\n"
            prompt += "Lunch: [lunch meal]\n"
            if include_snacks:
                prompt += "Snack: [snack food]\n"
            prompt += "Dinner: [dinner meal]\n\n"

        prompt += "GROCERY LIST:\n[List each ingredient on a new line with a - in front]"

        # Generate response
        response = client.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=2000,
            temperature=0.7,
        )

        if not response:
            return {'success': False, 'error': 'Failed to generate meal plan'}

        # Process response
        full_response = response.choices[0].text.strip()
        parts = full_response.split('GROCERY LIST:')

        meal_plan_text = parts[0].replace('MEAL PLAN:', '').strip()
        grocery_list = parts[1].strip() if len(parts) > 1 else ''

        # Create MealPlan
        meal_plan = MealPlan.objects.create(
            user_id=user_id,
            name=f"Meal Plan for {dietary_preferences}",
            description=meal_plan_text
        )

        # Create GroceryList
        grocery_items = "\n".join([
            item.strip('- ').strip()
            for item in grocery_list.split('\n')
            if item.strip()
        ])
        GroceryList.objects.create(
            user_id=user_id,
            items=grocery_items
        )

        # Track activity
        UserActivity.objects.create(
            user_id=user_id,
            action='create_meal',
            details={'meal_plan_type': dietary_preferences}
        )

        return {
            'success': True,
            'meal_plan_id': meal_plan.id,
            'meal_plan_text': meal_plan_text,
            'grocery_list': grocery_items
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}

@shared_task
def generate_pdf_async(meal_plan_id, user_id):
    """Asynchronous task to generate PDF"""
    try:
        meal_plan = MealPlan.objects.select_related('user').get(
            id=meal_plan_id, 
            user_id=user_id
        )
        
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
        elements.append(Paragraph(f"Meal Plan: {meal_plan.name}", title_style))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Description:", heading_style))
        elements.append(Paragraph(meal_plan.description, normal_style))
        elements.append(Spacer(1, 20))

        # Add grocery list
        grocery_list = GroceryList.objects.filter(
            user_id=user_id
        ).order_by('-created_at').first()

        if grocery_list:
            elements.append(Paragraph("Grocery List:", heading_style))
            for item in grocery_list.items.split('\n'):
                elements.append(
                    Paragraph(f"• {item.strip()}", normal_style)
                )

        # Build PDF
        doc.build(elements)
        pdf_data = buffer.getvalue()
        buffer.close()

        return {
            'success': True,
            'pdf_data': pdf_data,
            'filename': f"meal_plan_{meal_plan_id}.pdf"
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}

@shared_task
def process_recipe_async(recipe_id, user_id):
    """Asynchronous task to process recipe data"""
    try:
        recipe = Recipe.objects.select_related('user').get(
            id=recipe_id,
            user_id=user_id
        )

        # Process recipe data (example)
        processed_data = {
            'title': recipe.title,
            'ingredients': recipe.ingredients.split('\n'),
            'instructions': recipe.instructions.split('\n'),
            'created_at': recipe.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

        # Cache the processed data
        cache_key = f'recipe_processed_{recipe_id}'
        cache.set(cache_key, processed_data, timeout=3600)  # Cache for 1 hour

        return {
            'success': True,
            'recipe_data': processed_data
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}