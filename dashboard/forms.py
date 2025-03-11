# dashboard/forms.py
from django import forms
from .models import Recipe, UserFeedback

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['title', 'ingredients', 'instructions']
        widgets = {
            'ingredients': forms.Textarea(attrs={'rows': 5}),
            'instructions': forms.Textarea(attrs={'rows': 8}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if len(title) < 3:
            raise forms.ValidationError("Title must be at least 3 characters long")
        return title
    
# dashboard/forms.py
class FeedbackForm(forms.ModelForm):
    class Meta:
        model = UserFeedback
        fields = ['feedback_type', 'subject', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 5}),
        }