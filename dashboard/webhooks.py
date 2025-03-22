
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



# @csrf_exempt
# @require_POST
# def stripe_webhook(request):
#     payload = request.body
#     sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

#     try:
#         event = stripe.Webhook.construct_event(
#             payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
#         )

#         # Handle the event
#         if event.type == 'checkout.session.completed':
#             session = event.data.object
#             logger.info(f"Processing successful checkout for session: {session.id}")

#             # Get user and tier from metadata
#             user_id = session.metadata.get('user_id')
#             tier_id = session.metadata.get('tier_id')
#             tier_type = session.metadata.get('tier_type')

#             if not all([user_id, tier_id]):
#                 logger.error("Missing user_id or tier_id in session metadata")
#                 return HttpResponse(status=400)

#             try:
#                 # Get user and tier
#                 user = User.objects.get(id=user_id)
#                 tier = SubscriptionTier.objects.get(id=tier_id)

#                 # Deactivate any existing active subscriptions
#                 UserSubscription.objects.filter(
#                     user=user,
#                     is_active=True
#                 ).update(
#                     is_active=False,
#                     status='expired',
#                     end_date=timezone.now()
#                 )

#                 # Calculate end date based on tier type
#                 end_date = timezone.now() + {
#                     'weekly': timedelta(days=7),
#                     'monthly': timedelta(days=30),
#                     'one_time': timedelta(days=365),  # or whatever period you want for one-time
#                 }.get(tier_type, timedelta(days=30))

#                 # Create new subscription
#                 subscription = UserSubscription.objects.create(
#                     user=user,
#                     subscription_tier=tier,
#                     start_date=timezone.now(),
#                     end_date=end_date,
#                     is_active=True,
#                     status='active',
#                     payment_status='paid',
#                     stripe_subscription_id=session.subscription or session.payment_intent,
#                     payment_id=session.payment_intent
#                 )

#                 # Create payment history
#                 PaymentHistory.objects.create(
#                     user=user,
#                     subscription=subscription,
#                     amount=session.amount_total / 100,
#                     currency=session.currency.upper(),
#                     payment_method=session.payment_method_types[0],
#                     transaction_id=session.payment_intent,
#                     status='succeeded'
#                 )

#                 # Log activity
#                 UserActivity.objects.create(
#                     user=user,
#                     action='subscription',
#                     details={
#                         'tier_name': tier.name,
#                         'amount': session.amount_total / 100,
#                         'currency': session.currency.upper(),
#                         'subscription_id': subscription.id,
#                         'end_date': end_date.isoformat()
#                     }
#                 )

#                 # Clear relevant caches
#                 cache_keys = [
#                     f"active_subscription_{user.id}",
#                     f"user_subscription_{user.id}",
#                     "active_subscription_tiers"
#                 ]
#                 cache.delete_many(cache_keys)

#                 logger.info(f"Successfully processed subscription for user {user_id}")
#                 return HttpResponse(status=200)

#             except (User.DoesNotExist, SubscriptionTier.DoesNotExist) as e:
#                 logger.error(f"Error processing subscription: {str(e)}")
#                 return HttpResponse(status=400)

#         return HttpResponse(status=200)

#     except stripe.error.SignatureVerificationError as e:
#         logger.error(f"Invalid signature in Stripe webhook: {str(e)}")
#         return HttpResponse(status=400)
#     except Exception as e:
#         logger.error(f"Error processing webhook: {str(e)}")
#         return HttpResponse(status=400)
    

# dashboard/webhooks.py

@require_POST
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        handle_checkout_session(event['data']['object'])
    elif event['type'] == 'customer.subscription.updated':
        handle_subscription_updated(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_cancelled(event['data']['object'])

    return HttpResponse(status=200)

def handle_checkout_session(session):
    try:
        user_id = session['metadata']['user_id']
        user = User.objects.get(id=user_id)
        subscription = UserSubscription.objects.get(
            stripe_subscription_id=session['id']
        )

        # Update subscription status
        subscription.status = 'active'
        subscription.stripe_customer_id = session['customer']
        subscription.save()

        # Create payment record
        PaymentHistory.objects.create(
            user=user,
            subscription=subscription,
            amount=session['amount_total'] / 100,
            currency=session['currency'].upper(),
            payment_method='card',
            transaction_id=session['payment_intent'],
            status='completed'
        )

    except Exception as e:
        logger.error(f"Error handling checkout session: {str(e)}")

# dashboard/webhooks.py

def handle_subscription_updated(subscription_data):
    """Handle Stripe subscription update webhook"""
    try:
        # Get subscription from database
        subscription = UserSubscription.objects.get(
            stripe_subscription_id=subscription_data['id']
        )

        # Update subscription status
        subscription.status = subscription_data['status']

        # Update end date based on current_period_end
        if subscription_data.get('current_period_end'):
            subscription.end_date = datetime.fromtimestamp(
                subscription_data['current_period_end']
            ).replace(tzinfo=timezone.utc)

        # Update other relevant fields
        if subscription_data.get('cancel_at_period_end'):
            subscription.cancel_at_period_end = True

        subscription.save()

        # Create activity log
        UserActivity.objects.create(
            user=subscription.user,
            action='subscription_updated',
            details={
                'subscription_id': subscription.id,
                'status': subscription.status,
                'end_date': subscription.end_date.isoformat() if subscription.end_date else None
            }
        )

        # Clear subscription cache
        cache.delete(f'user_subscription_{subscription.user.id}')

        logger.info(f"Subscription {subscription.id} updated successfully")

    except UserSubscription.DoesNotExist:
        logger.error(f"Subscription not found for stripe_subscription_id: {subscription_data['id']}")
    except Exception as e:
        logger.error(f"Error handling subscription update: {str(e)}")


def handle_subscription_cancelled(subscription_data):
    """Handle Stripe subscription cancellation webhook"""
    try:
        # Get subscription from database
        subscription = UserSubscription.objects.get(
            stripe_subscription_id=subscription_data['id']
        )

        # Update subscription status
        subscription.status = 'cancelled'
        subscription.is_active = False
        subscription.end_date = timezone.now()
        subscription.save()

        # Create activity log
        UserActivity.objects.create(
            user=subscription.user,
            action='subscription_cancelled',
            details={
                'subscription_id': subscription.id,
                'cancellation_date': timezone.now().isoformat(),
                'reason': subscription_data.get('cancellation_reason', 'Not specified')
            }
        )

        # Clear subscription cache
        cache.delete(f'user_subscription_{subscription.user.id}')

        # Send cancellation email
        send_cancellation_email(subscription.user, subscription)

        logger.info(f"Subscription {subscription.id} cancelled successfully")

    except UserSubscription.DoesNotExist:
        logger.error(f"Subscription not found for stripe_subscription_id: {subscription_data['id']}")
    except Exception as e:
        logger.error(f"Error handling subscription cancellation: {str(e)}")


def send_cancellation_email(user, subscription):
    """Send subscription cancellation email"""
    try:
        mailjet = Client(
            auth=(settings.MAILJET_API_KEY, settings.MAILJET_API_SECRET),
            version='v3.1'
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .button {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                    margin: 10px 0;
                }}
                .feedback-section {{
                    background-color: #f9f9f9;
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Subscription Cancelled</h1>
                </div>
                <div class="content">
                    <p>Dear {user.get_full_name() or user.username},</p>

                    <p>We're sorry to see you go! Your subscription has been cancelled.</p>

                    <p>Your access to premium features will continue until {subscription.end_date.strftime('%B %d, %Y')}.</p>

                    <div class="feedback-section">
                        <h3>We'd Love Your Feedback</h3>
                        <p>Your feedback helps us improve. Please take a moment to tell us why you cancelled:</p>
                        <a href="{settings.SITE_URL}/feedback/" class="button">
                            Share Your Feedback
                        </a>
                    </div>

                    <p>If you change your mind, you can resubscribe at any time:</p>
                    <a href="{settings.SITE_URL}/pricing/" class="button">
                        View Plans
                    </a>

                    <p>Thank you for being part of NaijaPlate!</p>

                    <p>Best regards,<br>The NaijaPlate Team</p>
                </div>
            </div>
        </body>
        </html>
        """

        data = {
            'Messages': [{
                "From": {
                    "Email": settings.DEFAULT_FROM_EMAIL,
                    "Name": "NaijaPlate"
                },
                "To": [{
                    "Email": user.email,
                    "Name": user.get_full_name() or user.username
                }],
                "Subject": "Subscription Cancelled - NaijaPlate",
                "HTMLPart": html_content
            }]
        }

        response = mailjet.send.create(data=data)
        if response.status_code != 200:
            logger.error(f"Failed to send cancellation email: {response.json()}")

    except Exception as e:
        logger.error(f"Error sending cancellation email: {str(e)}")