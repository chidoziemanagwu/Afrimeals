from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from dashboard.views import (
    HomeView, DashboardView, MealGeneratorView,
    PricingView, CheckoutView, SubscriptionSuccessView, MySubscriptionView, RecipeDetailView, RecipeListView,
    UserProfileView, RecipeCreateView, RecipeUpdateView, ShoppingListView,
    ExportMealPlanPDFView, FeedbackView, check_task_status
)
from rest_framework.routers import DefaultRouter
from dashboard.api import RecipeViewSet, MealPlanViewSet, GroceryListViewSet

# Create a router and register our API viewsets
router = DefaultRouter()
router.register(r'api/recipes', RecipeViewSet, basename='recipe-api')
router.register(r'api/meal-plans', MealPlanViewSet, basename='mealplan-api')
router.register(r'api/grocery-lists', GroceryListViewSet, basename='grocerylist-api')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),


    path('accounts/', include('allauth.urls')),

    path('meal-generator/', MealGeneratorView.as_view(), name='meal_generator'),

    # Subscription routes
    path('pricing/', PricingView.as_view(), name='pricing'),
    path('checkout/<int:tier_id>/', CheckoutView.as_view(), name='checkout'),
    path('subscription/success/', SubscriptionSuccessView.as_view(), name='subscription_success'),
    path('my-subscription/', MySubscriptionView.as_view(), name='my_subscription'),

    # Recipe routes
    path('recipes/<int:pk>/', RecipeDetailView.as_view(), name='recipe_detail'),
    path('recipes/', RecipeListView.as_view(), name='recipe_list'),
    path('recipes/add/', RecipeCreateView.as_view(), name='recipe_add'),
    path('recipes/<int:pk>/edit/', RecipeUpdateView.as_view(), name='recipe_edit'),

    # User routes
    path('account/', UserProfileView.as_view(), name='user_profile'),
    path('shopping-list/', ShoppingListView.as_view(), name='shopping_list'),

    # New feature routes
    path('meal-plans/<int:pk>/export/', ExportMealPlanPDFView.as_view(), name='export_meal_plan'),
    path('feedback/', FeedbackView.as_view(), name='feedback'),

    # Include the API router URLs - moved to a specific prefix to avoid conflicts
    path('api/', include(router.urls)),

    # API authentication
    path('api-auth/', include('rest_framework.urls')),
    path('task-status/<str:task_id>/', check_task_status, name='check_task_status'),
]