"""RAC Client consumer"""
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.exceptions import ChannelFull, DenyConnection
from channels.generic.websocket import AsyncWebsocketConsumer
from django.http import Http404
from django.http.request import QueryDict
from django.shortcuts import get_object_or_404
from structlog.stdlib import BoundLogger, get_logger

from authentik.enterprise.providers.rac.models import ConnectionToken, RACProvider
from authentik.outposts.consumer import OUTPOST_GROUP_INSTANCE
from authentik.outposts.models import Outpost, OutpostState, OutpostType

RAC_CLIENT_GROUP = "group_enterprise_rac_client"
RAC_CLIENT_GROUP_SESSION = "group_enterprise_rac_client_%(session)s"

# Step 1: Client connects to this websocket endpoint
# Step 2: We prepare all the connection args for Guac
# Step 3: Send a websocket message to a single outpost that has this provider assigned
#         (Currently sending to all of them)
#         (Should probably do different load balancing algorithms)
# Step 4: Outpost creates a websocket connection back to authentik
#         with /ws/outpost_rac/<our_channel_id>/
# Step 5: This consumer transfers data between the two channels


def get_object_or_deny(*args, **kwargs):
    """get_object_or_404 compatible with websockets"""
    try:
        return get_object_or_404(*args, **kwargs)
    except Http404 as exc:
        raise DenyConnection() from exc


class RACClientConsumer(AsyncWebsocketConsumer):
    """RAC client consumer the browser connects to"""

    dest_channel_id: str = ""
    provider: RACProvider
    logger: BoundLogger

    async def connect(self):
        await self.accept("guacamole")
        await self.channel_layer.group_add(RAC_CLIENT_GROUP, self.channel_name)
        await self.channel_layer.group_add(
            RAC_CLIENT_GROUP_SESSION % {"session": self.scope["session"].session_key},
            self.channel_name,
        )
        await self.init_outpost_connection()

    async def disconnect(self, code):
        self.logger.debug("Disconnecting")
        # Tell the outpost we're disconnecting
        await self.channel_layer.send(
            self.dest_channel_id,
            {
                "type": "event.disconnect",
            },
        )

    @database_sync_to_async
    def init_outpost_connection(self):
        """Initialize guac connection settings"""
        token: ConnectionToken = get_object_or_deny(
            ConnectionToken, token=self.scope["url_route"]["kwargs"]["token"]
        )
        self.provider = token.provider
        params = token.get_settings()
        self.logger = get_logger().bind(
            endpoint=token.endpoint.name, user=self.scope["user"].username
        )
        msg = {
            "type": "event.provider.specific",
            "sub_type": "init_connection",
            "dest_channel_id": self.channel_name,
            "params": params,
            "protocol": self.provider.protocol,
        }
        query = QueryDict(self.scope["query_string"].decode())
        for key in ["screen_width", "screen_height", "screen_dpi", "audio"]:
            value = query.get(key, None)
            if not value:
                continue
            msg[key] = str(value)
        for outpost in Outpost.objects.filter(
            type=OutpostType.RAC,
            providers__in=[self.provider],
        ):
            # Sort all states for the outpost by connection count
            states = sorted(
                OutpostState.for_outpost(outpost),
                key=lambda state: int(state.args.get("active_connections", 0)),
            )
            if len(states) < 1:
                continue
            self.logger.debug("Sending out connection broadcast")
            async_to_sync(self.channel_layer.group_send)(
                OUTPOST_GROUP_INSTANCE % {"outpost_pk": str(outpost.pk), "instance": states[0].uid},
                msg,
            )

    async def receive(self, text_data=None, bytes_data=None):
        """Mirror data received from client to the dest_channel_id
        which is the channel talking to guacd"""
        if self.dest_channel_id == "":
            return
        try:
            await self.channel_layer.send(
                self.dest_channel_id,
                {
                    "type": "event.send",
                    "text_data": text_data,
                    "bytes_data": bytes_data,
                },
            )
        except ChannelFull:
            pass

    async def event_outpost_connected(self, event: dict):
        """Handle event broadcasted from outpost consumer, and check if they
        created a connection for us"""
        if event.get("client_channel") != self.channel_name:
            return
        self.logger.debug("Connected to a single outpost instance")
        self.dest_channel_id = event.get("outpost_channel")

    async def event_send(self, event: dict):
        """Handler called by outpost websocket that sends data to this specific
        client connection"""
        await self.send(text_data=event.get("text_data"), bytes_data=event.get("bytes_data"))

    async def event_disconnect(self, event: dict):
        """Disconnect when the session ends"""
        await self.close()
