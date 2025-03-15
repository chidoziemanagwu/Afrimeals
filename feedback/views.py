# feedback/views.py

from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from dashboard.models import UserFeedback
from .forms import UserFeedbackForm

class FeedbackCreateView(LoginRequiredMixin, CreateView):
    model = UserFeedback
    form_class = UserFeedbackForm
    template_name = 'feedback/feedback_form.html'
    success_url = reverse_lazy('feedback-thank-you')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)