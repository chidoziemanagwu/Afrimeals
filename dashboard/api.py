# dashboard/api.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import MealPlan, Recipe, GroceryList
from .serializers import MealPlanSerializer, RecipeSerializer, GroceryListSerializer
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator


@method_decorator(cache_page(60 * 15), name='dispatch')  # Cache for 15 minutes
class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Recipe.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@method_decorator(cache_page(60 * 15), name='dispatch')
class MealPlanViewSet(viewsets.ModelViewSet):
    serializer_class = MealPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MealPlan.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@method_decorator(cache_page(60 * 5), name='dispatch')  # Cache for 5 minutes
class GroceryListViewSet(viewsets.ModelViewSet):
    serializer_class = GroceryListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GroceryList.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)