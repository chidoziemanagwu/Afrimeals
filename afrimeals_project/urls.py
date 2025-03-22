from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include
from django.views.generic import RedirectView
from dashboard.views import (
    ExportMealPlanPDF, HomeView, DashboardView, MealGeneratorView,
    PricingView, CheckoutView, RecipeDetailsView, SubscriptionManagementView, SubscriptionSuccessView, MySubscriptionView, RecipeDetailView, RecipeListView, SubscriptionUpgradeSuccessView, TermsAndPolicyView,
    UserProfileView, RecipeCreateView, RecipeUpdateView, ShoppingListView, RecipeDeleteView,
    ExportMealPlanView, FeedbackView, check_task_status, custom_logout, detect_user_currency, export_activity_pdf, activity_detail_api, find_stores, gemini_chat, 
    checkout_success, checkout_cancel, get_exchange_rates, mark_feedback_status, meal_plan_history, get_meal_plan_details, update_currency, google_login_redirect
)
from rest_framework.routers import DefaultRouter
from dashboard.api import RecipeViewSet, MealPlanViewSet, GroceryListViewSet
# urls.py
from django.conf import settings
from django.conf.urls.static import static
from dashboard.api.gemini_views import chat
from dashboard.webhooks import stripe_webhook
from django.views.generic import TemplateView  
from dashboard.admin import custom_admin_site  # Your custom admin site# Add this import


def google_login_redirect(request):
    """Redirect all login attempts to Google OAuth"""
    next_url = request.GET.get('next', '')
    return redirect(f'/accounts/google/login/?next={next_url}')

# Create a router and register our API viewsets
router = DefaultRouter()
router.register(r'meal-plans', MealPlanViewSet, basename='mealplan')  # Remove 'api/' prefix
router.register(r'recipes', RecipeViewSet, basename='recipe')
router.register(r'grocery-lists', GroceryListViewSet, basename='grocerylist')

urlpatterns = [
    path('admin/', admin.site.urls),

    path('dashboard-admin/mark-feedback/<int:feedback_id>/', mark_feedback_status, name='mark_feedback_status'),
    path('dashboard-admin/', custom_admin_site.urls),  # Your custom admin
    path('dashboard-admin/dashboard/', custom_admin_site.dashboard_view, name='admin_dashboard'),

    
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),


    path('accounts/social/login/error/', RedirectView.as_view(url='/', permanent=False)),
    path('accounts/login/', google_login_redirect, name='account_login'),
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
    path('webhooks/stripe/', stripe_webhook, name='stripe_webhook'),


    path('checkout/success/', checkout_success, name='checkout_success'),
    path('checkout/cancel/', checkout_cancel, name='checkout_cancel'),


    path('api-auth/', include('rest_framework.urls')),
    path('task-status/<str:task_id>/', check_task_status, name='check_task_status'),
    path('meal-plans/history/', meal_plan_history, name='meal_plan_history'),
    # path('api/meal-plans/<int:meal_plan_id>/', get_meal_plan_details, name='get_meal_plan_details'),
    # In urls.py, add this to your urlpatterns
    path('api/grocery-list/<int:meal_plan_id>/',
        GroceryListViewSet.as_view({'get': 'retrieve_by_meal_plan'}),
        name='grocery-list-detail'),

    path('api/update-currency/', update_currency, name='update_currency'),
    path('api/find-stores/', find_stores, name='find_stores'),
    path('api/exchange-rates/', get_exchange_rates, name='exchange_rates'),
    path('api/detect-currency/', detect_user_currency, name='detect_currency'),
    path('terms-and-policy/', TermsAndPolicyView.as_view(), name='terms_policy'),

    path(
        'subscription/manage/',
        SubscriptionManagementView.as_view(),
        name='subscription_management'
    ),
    path(
        'subscription/upgrade/success/',
        SubscriptionUpgradeSuccessView.as_view(),
        name='subscription_upgrade_success'
    ),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)