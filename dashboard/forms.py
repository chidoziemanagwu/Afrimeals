# dashboard/forms.py
from django import forms
from .models import Recipe, UserFeedback
from django.core.validators import MinLengthValidator, MaxLengthValidator

# dashboard/forms.py
class RecipeForm(forms.ModelForm):
    title = forms.CharField(
        min_length=3,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full p-3 border border-gray-300 rounded-lg',
            'placeholder': 'Enter recipe title'
        }),
        help_text='Enter a descriptive title for your recipe (3-100 characters)'
    )

    ingredients = forms.CharField(
        min_length=10,
        widget=forms.Textarea(attrs={
            'rows': 5,
            'class': 'form-textarea w-full p-3 border border-gray-300 rounded-lg',
            'placeholder': 'List all ingredients with quantities'
        }),
        help_text='List all ingredients with their measurements'
    )

    instructions = forms.CharField(
        min_length=20,
        widget=forms.Textarea(attrs={
            'rows': 8,
            'class': 'form-textarea w-full p-3 border border-gray-300 rounded-lg',
            'placeholder': 'Enter step-by-step cooking instructions'
        }),
        help_text='Provide detailed cooking instructions'
    )

    is_admin_recipe = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput()
    )

    class Meta:
        model = Recipe
        fields = ['title', 'ingredients', 'instructions', 'is_admin_recipe']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and user.is_staff:
            self.fields['is_admin_recipe'].widget = forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 text-green-600'
            })
            self.fields['is_admin_recipe'].label = "Add as Featured Recipe"

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError("Please provide a recipe title")
        if len(title) < 3:
            raise forms.ValidationError("Recipe title must be at least 3 characters long")
        if len(title) > 100:
            raise forms.ValidationError("Recipe title cannot exceed 100 characters")
        return title

    def clean_ingredients(self):
        ingredients = self.cleaned_data.get('ingredients', '').strip()
        if not ingredients:
            raise forms.ValidationError("Please list the recipe ingredients")
        if len(ingredients) < 10:
            raise forms.ValidationError("Please provide more detailed ingredients (at least 10 characters)")
        return ingredients

    def clean_instructions(self):
        instructions = self.cleaned_data.get('instructions', '').strip()
        if not instructions:
            raise forms.ValidationError("Please provide cooking instructions")
        if len(instructions) < 20:
            raise forms.ValidationError("Please provide more detailed instructions (at least 20 characters)")
        return instructions
class FeedbackForm(forms.ModelForm):
    FEEDBACK_CHOICES = [
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('general', 'General Feedback')
    ]

    feedback_type = forms.ChoiceField(
        choices=FEEDBACK_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select w-full p-3 border border-gray-300 rounded-lg'
        }),
        help_text='Select the type of feedback you want to provide'
    )

    subject = forms.CharField(
        min_length=5,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full p-3 border border-gray-300 rounded-lg',
            'placeholder': 'Brief summary of your feedback'
        }),
        help_text='Provide a brief subject (5-100 characters)'
    )

    message = forms.CharField(
        min_length=10,
        max_length=1000,
        widget=forms.Textarea(attrs={
            'rows': 5,
            'class': 'form-textarea w-full p-3 border border-gray-300 rounded-lg',
            'placeholder': 'Detailed feedback message'
        }),
        help_text='Provide detailed feedback (10-1000 characters)'
    )

    class Meta:
        model = UserFeedback
        fields = ['feedback_type', 'subject', 'message']

    def clean_subject(self):
        subject = self.cleaned_data.get('subject', '').strip()
        if not subject:
            raise forms.ValidationError("Please provide a subject for your feedback")
        if len(subject) < 5:
            raise forms.ValidationError("Subject must be at least 5 characters long")
        if len(subject) > 100:
            raise forms.ValidationError("Subject cannot exceed 100 characters")
        return subject

    def clean_message(self):
        message = self.cleaned_data.get('message', '').strip()
        if not message:
            raise forms.ValidationError("Please provide your feedback message")
        if len(message) < 10:
            raise forms.ValidationError("Please provide more detailed feedback (at least 10 characters)")
        if len(message) > 1000:
            raise forms.ValidationError("Feedback message cannot exceed 1000 characters")
        return message

    def clean(self):
        cleaned_data = super().clean()
        feedback_type = cleaned_data.get('feedback_type')
        if not feedback_type:
            raise forms.ValidationError({
                'feedback_type': "Please select a feedback type"
            })
        return cleaned_data