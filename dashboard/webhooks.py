from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta


from .models import (
    PaymentHistory, SubscriptionTier,
    UserSubscription, UserActivity
)

import stripe
from django.conf import settings
import logging
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

# Set up logger
logger = logging.getLogger(__name__)



@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )

        # Handle the event
        if event.type == 'checkout.session.completed':
            session = event.data.object
            logger.info(f"Processing successful checkout for session: {session.id}")

            # Get user and tier from metadata
            user_id = session.metadata.get('user_id')
            tier_id = session.metadata.get('tier_id')

            if not all([user_id, tier_id]):
                logger.error("Missing user_id or tier_id in session metadata")
                return HttpResponse(status=400)

            try:
                user = User.objects.get(id=user_id)
                tier = SubscriptionTier.objects.get(id=tier_id)

                # Create or update subscription
                subscription = UserSubscription.objects.create(
                    user=user,
                    subscription_tier=tier,
                    start_date=timezone.now(),
                    end_date=timezone.now() + {
                        'weekly': timedelta(days=7),
                        'monthly': timedelta(days=30),
                        'one_time': timedelta(days=1),
                    }.get(tier.tier_type, timedelta(days=30)),
                    status='active',
                    payment_status='paid',
                    stripe_subscription_id=session.subscription,
                    payment_id=session.payment_intent
                )

                # Create payment history record
                PaymentHistory.objects.create(
                    user=user,
                    subscription=subscription,
                    amount=session.amount_total / 100,  # Convert from cents
                    currency=session.currency.upper(),
                    payment_method=session.payment_method_types[0],
                    transaction_id=session.payment_intent,
                    status='succeeded'
                )

                # Log activity
                UserActivity.objects.create(
                    user=user,
                    action='subscription',
                    details={
                        'tier_name': tier.name,
                        'amount': session.amount_total / 100,
                        'currency': session.currency.upper(),
                        'subscription_id': subscription.id
                    }
                )

                logger.info(f"Successfully processed subscription for user {user_id}")

            except (User.DoesNotExist, SubscriptionTier.DoesNotExist) as e:
                logger.error(f"Error processing subscription: {str(e)}")
                return HttpResponse(status=400)

        return HttpResponse(status=200)

    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature in Stripe webhook")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return HttpResponse(status=400)