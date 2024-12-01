from django.contrib import admin
from django.urls import path, include
from dashboard.views import HomeView, DashboardView, MealGeneratorView

urlpatterns = [
  path('admin/', admin.site.urls),
  path('', HomeView.as_view(), name='home'),
  path('dashboard/', DashboardView.as_view(), name='dashboard'),
  path('accounts/', include('allauth.urls')),
  path('meal-generator/', MealGeneratorView.as_view(), name='meal_generator'),
]