# dashboard/api/viewsets.py
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from ..models import MealPlan, Recipe, GroceryList
from ..serializers import MealPlanSerializer, RecipeSerializer, GroceryListSerializer
from django.core.exceptions import ObjectDoesNotExist
import json
import logging


logger = logging.getLogger(__name__)

@method_decorator(cache_page(60 * 15), name='dispatch')
class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Recipe.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# dashboard/api/viewsets.py

@method_decorator(cache_page(60 * 15), name='dispatch')
class MealPlanViewSet(viewsets.ModelViewSet):
    serializer_class = MealPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MealPlan.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        try:
            # Get the meal plan instance
            instance = self.get_object()
            
            try:
                # Parse the meal plan data safely
                meal_plan_data = json.loads(instance.description) if instance.description else []
                
                # Get all associated recipes for this meal plan at once
                recipes_dict = {
                    f"{recipe.day_index}-{recipe.meal_type}": recipe
                    for recipe in Recipe.objects.filter(meal_plan=instance)
                }
                
                # Check if any day has snacks
                has_snacks = any(
                    'snack' in day.get('meals', {})
                    for day in meal_plan_data
                )

                # Process each day's data
                processed_days = []
                for day_index, day_data in enumerate(meal_plan_data):
                    # Create new day dictionary
                    processed_day = {
                        'day': f"Day {day_index + 1}",
                        'meals': {}
                    }
                    
                    # Get meals safely
                    meals = day_data.get('meals', {})
                    if isinstance(meals, dict):
                        # Process each meal type
                        for meal_type in ['breakfast', 'lunch', 'dinner', 'snack']:
                            if meal_type in meals:
                                # Add basic meal information
                                processed_day['meals'][meal_type] = meals[meal_type]
                                
                                # Check for associated recipe
                                recipe_key = f"{day_index}-{meal_type}"
                                recipe = recipes_dict.get(recipe_key)
                                
                                if recipe:
                                    processed_day['meals'][f'{meal_type}_recipe'] = {
                                        'id': recipe.id,
                                        'title': recipe.title,
                                        'prep_time': recipe.prep_time,
                                        'cook_time': recipe.cook_time,
                                        'servings': recipe.servings,
                                        'difficulty': recipe.difficulty,
                                        'ingredients': recipe.ingredients_list,
                                        'instructions': recipe.instructions_list,
                                        'nutrition_info': recipe.nutrition_info,
                                        'tips': recipe.tips,
                                        'is_ai_generated': recipe.is_ai_generated
                                    }
                    
                    processed_days.append(processed_day)

                # Prepare the response
                response_data = {
                    'success': True,
                    'meal_plan': {
                        'id': instance.id,
                        'name': instance.name,
                        'created_at': instance.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'include_snacks': has_snacks,  # Add this field
                        'days': processed_days
                    }
                }

                return Response(response_data)

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in meal plan {instance.id}: {str(e)}")
                return Response({
                    'success': False,
                    'error': 'Invalid meal plan data format'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error retrieving meal plan: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Error retrieving meal plan details'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@method_decorator(cache_page(60 * 5), name='dispatch')
class GroceryListViewSet(viewsets.ModelViewSet):
    serializer_class = GroceryListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GroceryList.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def retrieve_by_meal_plan(self, request, pk=None):
        """
        Retrieve grocery list for a specific meal plan
        """
        try:
            meal_plan_id = self.kwargs.get('pk') or request.query_params.get('meal_plan_id')
            if not meal_plan_id:
                return Response({
                    'success': False,
                    'error': 'Meal plan ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            meal_plan = get_object_or_404(MealPlan, id=meal_plan_id, user=request.user)

            # Try to get existing grocery list
            grocery_list = GroceryList.objects.filter(
                user=request.user,
                meal_plan=meal_plan
            ).first()

            if not grocery_list:
                # If no grocery list exists, create one from meal plan recipes
                items = self.generate_grocery_list_from_meal_plan(meal_plan)
                grocery_list = GroceryList.objects.create(
                    user=request.user,
                    meal_plan=meal_plan,
                    items=items
                )

            return Response({
                'success': True,
                'items': grocery_list.items
            })

        except MealPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Meal plan not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving grocery list: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def generate_grocery_list_from_meal_plan(self, meal_plan):
        """
        Generate a grocery list from meal plan recipes
        """
        try:
            # Get all recipes for this meal plan
            recipes = Recipe.objects.filter(meal_plan=meal_plan)

            # Collect all ingredients
            all_ingredients = []
            for recipe in recipes:
                ingredients = recipe.ingredients_list
                if isinstance(ingredients, list):
                    all_ingredients.extend(ingredients)
                else:
                    # Handle case where ingredients might be a string
                    all_ingredients.extend([i.strip() for i in ingredients.split('\n') if i.strip()])

            # Remove duplicates and sort
            unique_ingredients = sorted(set(all_ingredients))

            # Join ingredients with newlines
            return '\n'.join(unique_ingredients)

        except Exception as e:
            logger.error(f"Error generating grocery list: {str(e)}")
            return ''