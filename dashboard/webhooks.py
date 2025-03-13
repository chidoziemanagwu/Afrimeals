from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from .models import SubscriptionTier
from .views import CheckoutView
import stripe
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )

        if event.type in ['checkout.session.completed', 'payment_intent.succeeded']:
            session = event.data.object
            logger.info(f"Processing successful payment for session: {session.id}")

            # Get user and tier from metadata
            user_id = session.metadata.get('user_id')
            tier_id = session.metadata.get('tier_id')

            user = User.objects.get(id=user_id)
            tier = SubscriptionTier.objects.get(id=tier_id)

            view = CheckoutView()
            view._handle_successful_payment(
                user=user,
                tier=tier,
                payment_id=session.payment_intent or session.subscription
            )
            logger.info(f"Successfully processed payment for user {user_id}")

        return HttpResponse(status=200)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature in Stripe webhook")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return HttpResponse(status=400)