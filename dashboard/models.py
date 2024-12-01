from django.db import models
from django.contrib.auth.models import User

class MealPlan(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  name = models.CharField(max_length=100)
  description = models.TextField()
  created_at = models.DateTimeField(auto_now_add=True)

class Recipe(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  title = models.CharField(max_length=100)
  ingredients = models.TextField()
  instructions = models.TextField()

class GroceryList(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  items = models.TextField()