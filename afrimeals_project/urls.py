from django.contrib import admin
from django.urls import path, include
from dashboard.views import (
    HomeView, DashboardView, MealGeneratorView,
    PricingView, CheckoutView, SubscriptionSuccessView, MySubscriptionView
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('accounts/', include('allauth.urls')),
    path('meal-generator/', MealGeneratorView.as_view(), name='meal_generator'),

    # New URL routes
    path('pricing/', PricingView.as_view(), name='pricing'),
    path('checkout/<int:tier_id>/', CheckoutView.as_view(), name='checkout'),
    path('subscription/success/', SubscriptionSuccessView.as_view(), name='subscription_success'),
    path('my-subscription/', MySubscriptionView.as_view(), name='my_subscription'),
]