# Generated by Django 4.2.5 on 2025-03-20 16:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0018_usersubscription_payment_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriptiontier',
            name='meal_plan_limit',
            field=models.IntegerField(default=0),
        ),
    ]
