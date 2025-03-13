# Generated by Django 5.1.3 on 2025-03-13 10:36

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0006_rename_recipe_user_created_idx_dashboard_r_user_id_329110_idx_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='recipe',
            name='is_admin_recipe',
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name='recipe',
            index=models.Index(fields=['is_admin_recipe'], name='recipe_admin_idx'),
        ),
    ]
