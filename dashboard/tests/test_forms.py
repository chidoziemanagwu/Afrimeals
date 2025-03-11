# dashboard/tests/test_forms.py
from django.test import TestCase
from django.contrib.auth.models import User
from dashboard.forms import RecipeForm, FeedbackForm
from dashboard.models import Recipe, UserFeedback

class RecipeFormTest(TestCase):
    def test_recipe_form_valid(self):
        """Test recipe form with valid data"""
        form_data = {
            'title': 'Test Recipe',
            'ingredients': 'Test ingredients',
            'instructions': 'Test instructions'
        }
        form = RecipeForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_recipe_form_invalid(self):
        """Test recipe form with invalid data"""
        # Missing title
        form_data = {
            'ingredients': 'Test ingredients',
            'instructions': 'Test instructions'
        }
        form = RecipeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)

    def test_recipe_form_save(self):
        """Test recipe form save"""
        # Create test user
        user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )

        form_data = {
            'title': 'Test Recipe',
            'ingredients': 'Test ingredients',
            'instructions': 'Test instructions'
        }
        form = RecipeForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Save form with user
        recipe = form.save(commit=False)
        recipe.user = user
        recipe.save()

        # Verify recipe was created
        self.assertTrue(Recipe.objects.filter(
            user=user,
            title='Test Recipe'
        ).exists())

class FeedbackFormTest(TestCase):
    def test_feedback_form_valid(self):
        """Test feedback form with valid data"""
        form_data = {
            'feedback_type': 'feature',
            'subject': 'Test Feedback',
            'message': 'This is a test feedback message'
        }
        form = FeedbackForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_feedback_form_invalid(self):
        """Test feedback form with invalid data"""
        # Invalid feedback type
        form_data = {
            'feedback_type': 'invalid',
            'subject': 'Test Feedback',
            'message': 'This is a test feedback message'
        }
        form = FeedbackForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('feedback_type', form.errors)

    def test_feedback_form_save(self):
        """Test feedback form save"""
        # Create test user
        user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )

        form_data = {
            'feedback_type': 'feature',
            'subject': 'Test Feedback',
            'message': 'This is a test feedback message'
        }
        form = FeedbackForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Save form with user
        feedback = form.save(commit=False)
        feedback.user = user
        feedback.save()

        # Verify feedback was created
        self.assertTrue(UserFeedback.objects.filter(
            user=user,
            subject='Test Feedback'
        ).exists())