# Generated by Django 5.1.3 on 2025-03-14 18:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0014_recipe_is_ai_generated'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipe',
            name='cook_time',
            field=models.CharField(default='45 mins', max_length=200),
        ),
        migrations.AlterField(
            model_name='recipe',
            name='difficulty',
            field=models.CharField(default='Intermediate', max_length=200),
        ),
        migrations.AlterField(
            model_name='recipe',
            name='meal_type',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='recipe',
            name='prep_time',
            field=models.CharField(default='30 mins', max_length=200),
        ),
        migrations.AlterField(
            model_name='recipe',
            name='servings',
            field=models.IntegerField(default=3),
        ),
    ]
