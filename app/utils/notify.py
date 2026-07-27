# app/utils/notify.py
"""Admin notifications for new print orders.

Two channels, both best-effort and non-blocking for the checkout flow:
  1. In-app Notification rows, polled by the admin sidebar bell every 15s —
     this always works, no setup required, and covers "every admin device
     that's logged into /admin".
  2. Web Push, straight to the OS notification tray on any admin device that
     has clicked "Enable order alerts" — requires VAPID_PUBLIC_KEY /
     VAPID_PRIVATE_KEY to be set (see app/config.py). If they're not set,
     push sends are skipped silently; the in-app bell still works.
"""
import json
import logging

from flask import current_app, url_for

from app.extensions import db
from app.models import User, Notification, PushSubscription

logger = logging.getLogger(__name__)


def notify_admins_new_order(order):
    """Create an in-app notification for every admin and attempt a web push."""
    admins = User.query.filter_by(is_admin=True).all()
    if not admins:
        return

    title = "New print job order"
    message = f"{order.customer.full_name} placed order {order.reference} — ₦{order.total_amount:,.2f}"
    link = f"/admin/orders?highlight={order.id}"

    for admin in admins:
        db.session.add(Notification(
            user_id=admin.id,
            type="new_order",
            title=title,
            message=message,
            link=link,
        ))
    db.session.commit()

    _send_push_to_admins(admins, title, message, link)


def _send_push_to_admins(admins, title, message, link):
    public_key = current_app.config.get("VAPID_PUBLIC_KEY")
    private_key = current_app.config.get("VAPID_PRIVATE_KEY")
    if not public_key or not private_key:
        return  # Web Push not configured — in-app bell still covers this.

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.warning("pywebpush not installed; skipping web push.")
        return

    admin_ids = [a.id for a in admins]
    subs = PushSubscription.query.filter(PushSubscription.user_id.in_(admin_ids)).all()
    payload = json.dumps({"title": title, "body": message, "url": link})

    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={"sub": current_app.config.get("VAPID_CLAIM_EMAIL", "mailto:admin@example.com")},
            )
        except WebPushException as e:
            # Expired/invalid subscription — clean it up so we don't keep retrying it.
            logger.info(f"Push failed for subscription {sub.id}, removing: {e}")
            db.session.delete(sub)
        except Exception as e:
            logger.warning(f"Unexpected push error: {e}")
    db.session.commit()
