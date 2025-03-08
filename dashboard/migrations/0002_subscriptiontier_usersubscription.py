# Generated by Django 5.1.3 on 2025-03-08 15:40

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SubscriptionTier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('tier_type', models.CharField(choices=[('one_time', 'Pay As You Go'), ('weekly', 'Weekly Plan'), ('monthly', 'Monthly Plan')], max_length=20)),
                ('price', models.DecimalField(decimal_places=2, max_digits=6)),
                ('description', models.TextField()),
                ('features', models.JSONField(default=dict)),
            ],
        ),
        migrations.CreateModel(
            name='UserSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateTimeField(auto_now_add=True)),
                ('end_date', models.DateTimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('payment_id', models.CharField(blank=True, max_length=100, null=True)),
                ('subscription_tier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dashboard.subscriptiontier')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
