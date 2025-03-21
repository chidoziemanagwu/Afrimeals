# Generated by Django 5.1.3 on 2025-03-10 20:29

import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0002_subscriptiontier_usersubscription'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='grocerylist',
            name='created_at',
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='recipe',
            name='created_at',
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='subscriptiontier',
            name='is_active',
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AlterField(
            model_name='mealplan',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='recipe',
            name='title',
            field=models.CharField(db_index=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='subscriptiontier',
            name='name',
            field=models.CharField(db_index=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='subscriptiontier',
            name='tier_type',
            field=models.CharField(choices=[('one_time', 'Pay As You Go'), ('weekly', 'Weekly Plan'), ('monthly', 'Monthly Plan')], db_index=True, max_length=20),
        ),
        migrations.AlterField(
            model_name='usersubscription',
            name='end_date',
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AlterField(
            model_name='usersubscription',
            name='is_active',
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddIndex(
            model_name='grocerylist',
            index=models.Index(fields=['user', 'created_at'], name='grocery_user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='mealplan',
            index=models.Index(fields=['user', 'created_at'], name='meal_plan_user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='recipe',
            index=models.Index(fields=['user', 'created_at'], name='recipe_user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='subscriptiontier',
            index=models.Index(fields=['tier_type', 'price'], name='tier_type_price_idx'),
        ),
        migrations.AddIndex(
            model_name='usersubscription',
            index=models.Index(fields=['user', 'is_active', 'end_date'], name='sub_user_active_end_idx'),
        ),
    ]
