# dashboard/serializers.py
from rest_framework import serializers
from .models import MealPlan, Recipe, GroceryList

class RecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ['id', 'title', 'ingredients', 'instructions', 'created_at']
        read_only_fields = ['created_at']

class MealPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealPlan
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['created_at']

class GroceryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroceryList
        fields = ['id', 'items', 'created_at']
        read_only_fields = ['created_at']