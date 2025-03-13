# Generated by Django 5.1.3 on 2025-03-13 12:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0010_remove_useractivity_user_action_idx_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='useractivity',
            name='action',
            field=models.CharField(choices=[('create_meal', 'Created Meal Plan'), ('update_meal', 'Updated Meal Plan'), ('delete_meal', 'Deleted Meal Plan'), ('create_recipe', 'Created Recipe'), ('update_recipe', 'Updated Recipe'), ('delete_recipe', 'Deleted Recipe'), ('subscription', 'Subscription Change'), ('login', 'Login'), ('logout', 'Logout'), ('feedback', 'Submitted Feedback')], max_length=20),
        ),
    ]
