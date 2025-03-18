
from django.core.cache import cache
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
            tier_type = session.metadata.get('tier_type')

            if not all([user_id, tier_id]):
                logger.error("Missing user_id or tier_id in session metadata")
                return HttpResponse(status=400)

            try:
                # Get user and tier
                user = User.objects.get(id=user_id)
                tier = SubscriptionTier.objects.get(id=tier_id)

                # Deactivate any existing active subscriptions
                UserSubscription.objects.filter(
                    user=user,
                    is_active=True
                ).update(
                    is_active=False,
                    status='expired',
                    end_date=timezone.now()
                )

                # Calculate end date based on tier type
                end_date = timezone.now() + {
                    'weekly': timedelta(days=7),
                    'monthly': timedelta(days=30),
                    'one_time': timedelta(days=365),  # or whatever period you want for one-time
                }.get(tier_type, timedelta(days=30))

                # Create new subscription
                subscription = UserSubscription.objects.create(
                    user=user,
                    subscription_tier=tier,
                    start_date=timezone.now(),
                    end_date=end_date,
                    is_active=True,
                    status='active',
                    payment_status='paid',
                    stripe_subscription_id=session.subscription or session.payment_intent,
                    payment_id=session.payment_intent
                )

                # Create payment history
                PaymentHistory.objects.create(
                    user=user,
                    subscription=subscription,
                    amount=session.amount_total / 100,
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
                        'subscription_id': subscription.id,
                        'end_date': end_date.isoformat()
                    }
                )

                # Clear relevant caches
                cache_keys = [
                    f"active_subscription_{user.id}",
                    f"user_subscription_{user.id}",
                    "active_subscription_tiers"
                ]
                cache.delete_many(cache_keys)

                logger.info(f"Successfully processed subscription for user {user_id}")
                return HttpResponse(status=200)

            except (User.DoesNotExist, SubscriptionTier.DoesNotExist) as e:
                logger.error(f"Error processing subscription: {str(e)}")
                return HttpResponse(status=400)

        return HttpResponse(status=200)

    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature in Stripe webhook: {str(e)}")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return HttpResponse(status=400)