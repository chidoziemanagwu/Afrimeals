# Generated by Django 5.1.3 on 2025-03-11 11:29

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0005_userfeedback_useractivity'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='recipe',
            new_name='dashboard_r_user_id_329110_idx',
            old_name='recipe_user_created_idx',
        ),
        migrations.AlterField(
            model_name='mealplan',
            name='name',
            field=models.CharField(db_index=True, max_length=100),
        ),
        migrations.AddIndex(
            model_name='recipe',
            index=models.Index(fields=['title'], name='recipe_title_idx'),
        ),
    ]
