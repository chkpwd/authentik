"""RAC Signals"""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.signals import user_logged_out
from django.core.cache import cache
from django.db.models import Model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import HttpRequest

from authentik.core.models import User
from authentik.enterprise.providers.rac.api.endpoints import user_endpoint_cache_key
from authentik.enterprise.providers.rac.consumer_client import RAC_CLIENT_GROUP_SESSION
from authentik.enterprise.providers.rac.models import Endpoint


@receiver(user_logged_out)
def user_logged_out_session(sender, request: HttpRequest, user: User, **_):
    """Disconnect any open RAC connections"""
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        RAC_CLIENT_GROUP_SESSION
        % {
            "session": request.session.session_key,
        },
        {"type": "event.disconnect", "reason": "logout"},
    )


@receiver(post_save, sender=Endpoint)
def post_save_application(sender: type[Model], instance, created: bool, **_):
    """Clear user's application cache upon application creation"""
    if not created:  # pragma: no cover
        return

    # Delete user endpoint cache
    keys = cache.keys(user_endpoint_cache_key("*"))
    cache.delete_many(keys)