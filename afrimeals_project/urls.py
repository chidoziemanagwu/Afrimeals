from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from dashboard.views import (
    ExportMealPlanPDF, HomeView, DashboardView, MealGeneratorView,
    PricingView, CheckoutView, RecipeDetailsView, SubscriptionSuccessView, MySubscriptionView, RecipeDetailView, RecipeListView,
    UserProfileView, RecipeCreateView, RecipeUpdateView, ShoppingListView, RecipeDeleteView,
    ExportMealPlanView, FeedbackView, check_task_status, export_activity_pdf, activity_detail_api, gemini_chat
)
from rest_framework.routers import DefaultRouter
from dashboard.api import RecipeViewSet, MealPlanViewSet, GroceryListViewSet
# urls.py
from django.conf import settings
from django.conf.urls.static import static
from dashboard.api.gemini_views import chat

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
    path('recipes/<int:pk>/delete/', RecipeDeleteView.as_view(), name='recipe_delete'),
    # User routes
    path('account/', UserProfileView.as_view(), name='user_profile'),
    path('shopping-list/', ShoppingListView.as_view(), name='shopping_list'),

    # urls.py
    path('activity/<int:activity_id>/export/', export_activity_pdf, name='export_activity_pdf'),
    path('activity/<int:activity_id>/detail/', activity_detail_api, name='activity_detail_api'),

    # New feature routes
    path('meal-plans/<int:pk>/export/', ExportMealPlanView.as_view(), name='export_meal_plan'),
    path('feedback/', FeedbackView.as_view(), name='feedback'),

    # Include the API router URLs - moved to a specific prefix to avoid conflicts
    path('api/', include(router.urls)),

    path('api/recipe-details/<int:meal_plan_id>/<int:day_index>/<str:meal_type>/',
            RecipeDetailsView.as_view(),
            name='recipe_details'),

    path('meal-plan/<int:meal_plan_id>/export/',
        ExportMealPlanPDF.as_view(),
        name='export_meal_plan'),

    path('api/gemini/chat/', chat, name='gemini_chat'),
    # path('api/gemini/recommendations/', get_recipe_recommendations, name='recipe_recommendations'),
    # path('api/gemini/substitutes/', find_ingredient_substitutes, name='ingredient_substitutes'),
    # path('api/gemini/cooking-tips/', get_cooking_tips, name='cooking_tips'),
    # API authentication
    path('api-auth/', include('rest_framework.urls')),
    path('task-status/<str:task_id>/', check_task_status, name='check_task_status'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)