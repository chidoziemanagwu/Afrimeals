# admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import MealPlan, PaymentHistory, Recipe, GroceryList, SubscriptionTier, UserSubscription, UserActivity, UserFeedback, User
from django.urls import path
from django.template.response import TemplateResponse
from django.contrib.admin import AdminSite
from django.db.models import Count
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta
from django.utils import timezone

@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    search_fields = ('name', 'user__username')
    list_filter = ('created_at',)

@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscription', 'amount', 'payment_date')
    search_fields = ('transaction_id', 'user__username', 'subscription', 'payment_date')
    list_filter = ('payment_date',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'meal_plan', 'created_at', 'is_ai_generated')
    search_fields = ('title', 'user__username')
    list_filter = ('is_ai_generated', 'created_at')

@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ('subject', 'feedback_type', 'user', 'created_at', 'is_resolved')
    list_filter = ('feedback_type', 'is_resolved', 'created_at')
    search_fields = ('subject', 'message', 'user__username')
    actions = ['mark_as_resolved']

    def mark_as_resolved(self, request, queryset):
        queryset.update(is_resolved=True)
        self.message_user(request, "Selected feedback marked as resolved.")
    mark_as_resolved.short_description = "Mark selected feedback as resolved"

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscription_tier', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'subscription_tier', 'end_date')
    search_fields = ('user__username', 'subscription_tier__name')

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'details')


# admin.py
class CustomAdminSite(AdminSite):
    site_header = 'Afrimeals Admin'
    site_title = 'Afrimeals Admin Portal'
    index_title = 'Welcome to Afrimeals Admin Portal'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='admin_dashboard'),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        now = timezone.now()
        month_ago = now - timedelta(days=30)
        week_ago = now - timedelta(days=7)
        six_months_ago = now - timedelta(days=180)

        # Subscription trends for the last 6 months
        subscription_trends = UserSubscription.objects.filter(
            start_date__gte=six_months_ago
        ).annotate(
            month=TruncMonth('start_date')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        # User metrics
        total_users = User.objects.count()
        new_users_count = User.objects.filter(date_joined__gte=month_ago).count()

        # Subscription metrics
        active_subscriptions = UserSubscription.objects.filter(is_active=True).count()
        expiring_soon = UserSubscription.objects.filter(
            is_active=True,
            end_date__lte=now + timedelta(days=7)
        ).count()

        # Recipe metrics
        total_recipes = Recipe.objects.count()
        ai_generated_recipes = Recipe.objects.filter(is_ai_generated=True).count()

        # Meal plan metrics
        active_meal_plans = MealPlan.objects.count()
        new_meal_plans = MealPlan.objects.filter(created_at__gte=week_ago).count()

        # Activity metrics
        total_activities = UserActivity.objects.filter(
            timestamp__gte=now - timedelta(days=1)
        ).count()

        # Feedback metrics and data
        feedback_stats = {
            'total': UserFeedback.objects.count(),
            'resolved': UserFeedback.objects.filter(is_resolved=True).count(),
            'unresolved': UserFeedback.objects.filter(is_resolved=False).count(),
        }

        # Get recent feedback for the tables
        recent_feedback = UserFeedback.objects.all().select_related('user').order_by('-created_at')

        context = {
            'total_users': total_users,
            'new_users_count': new_users_count,
            'active_subscriptions': active_subscriptions,
            'expiring_soon': expiring_soon,
            'total_recipes': total_recipes,
            'ai_generated_recipes': ai_generated_recipes,
            'active_meal_plans': active_meal_plans,
            'new_meal_plans': new_meal_plans,
            'total_activities': total_activities,
            'feedback_stats': feedback_stats,
            'subscription_trends': list(subscription_trends),
            'recent_feedback': recent_feedback,  # Add this line
            'title': 'Dashboard',
            'site_title': self.site_title,
            'site_header': self.site_header,
            'has_permission': True,
        }
        return TemplateResponse(request, "admin/dashboard.html", context)

# Create an instance of CustomAdminSite
custom_admin_site = CustomAdminSite(name='custom_admin')

# Register your models with both admin sites
custom_admin_site.register(MealPlan, MealPlanAdmin)
custom_admin_site.register(Recipe, RecipeAdmin)
custom_admin_site.register(UserFeedback, UserFeedbackAdmin)
custom_admin_site.register(UserSubscription, UserSubscriptionAdmin)
custom_admin_site.register(UserActivity, UserActivityAdmin)
custom_admin_site.register(User)
custom_admin_site.register(PaymentHistory, PaymentHistoryAdmin)