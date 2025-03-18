# admin.py

from django.contrib import admin
from .models import MealPlan, PaymentHistory, Recipe, SubscriptionTier, UserSubscription, UserActivity, UserFeedback, User
from django.urls import path
from django.template.response import TemplateResponse
from django.contrib.admin import AdminSite
from django.db.models import Count
from datetime import timedelta
from django.utils import timezone
from django.db.models.functions import TruncDay

from django.core.cache import cache


@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    search_fields = ('name', 'user__username')
    list_filter = ('created_at',)

@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'tier_type', 'price', 'created_at')
    search_fields = ('name', 'created_at')
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

        # Limit to last 30 days instead of 6 months to reduce data volume
        thirty_days_ago = now - timedelta(days=30)

        # Use caching for expensive queries
        cache_key = "dashboard_subscription_trends"
        daily_trends = cache.get(cache_key)

        if daily_trends is None:
            # Optimize the query - use TruncDay and annotate in a single query
            from django.db.models.functions import TruncDay

            subscription_trends = UserSubscription.objects.filter(
                start_date__gte=thirty_days_ago
            ).annotate(
                day=TruncDay('start_date')
            ).values('day').annotate(
                count=Count('id')
            ).order_by('day')

            # Convert to dictionary for faster lookups
            trend_dict = {item['day'].date(): item['count'] for item in subscription_trends}

            # Create a complete list of days with proper counts
            daily_trends = []
            current_date = thirty_days_ago.date()
            end_date = now.date()

            while current_date <= end_date:
                daily_trends.append({
                    'day': current_date.isoformat(),
                    'count': trend_dict.get(current_date, 0)
                })
                current_date += timedelta(days=1)

            # Cache the result for 1 hour
            cache.set(cache_key, daily_trends, 3600)

        # Use select_related and only fetch what's needed
        context = {
            # Use count() instead of fetching all objects
            'total_users': User.objects.count(),
            'new_users_count': User.objects.filter(date_joined__gte=month_ago).count(),
            'active_subscriptions': UserSubscription.objects.filter(is_active=True).count(),
            'expiring_soon': UserSubscription.objects.filter(
                is_active=True,
                end_date__lte=now + timedelta(days=7)
            ).count(),
            'total_recipes': Recipe.objects.count(),
            'ai_generated_recipes': Recipe.objects.filter(is_ai_generated=True).count(),
            'active_meal_plans': MealPlan.objects.count(),
            'new_meal_plans': MealPlan.objects.filter(created_at__gte=week_ago).count(),
            'total_activities': UserActivity.objects.filter(
                timestamp__gte=now - timedelta(days=1)
            ).count(),
            'feedback_stats': {
                'total': UserFeedback.objects.count(),
                'resolved': UserFeedback.objects.filter(is_resolved=True).count(),
                'unresolved': UserFeedback.objects.filter(is_resolved=False).count(),
            },
            'subscription_trends': daily_trends,
            # Limit the number of feedback items and use select_related
            'recent_feedback': UserFeedback.objects.select_related('user').order_by('-created_at')[:50],
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
custom_admin_site.register(SubscriptionTier, SubscriptionTierAdmin)