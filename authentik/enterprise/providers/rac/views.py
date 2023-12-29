"""RAC Views"""
from typing import Any

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from authentik.core.models import Application, AuthenticatedSession
from authentik.core.views.interface import InterfaceView
from authentik.enterprise.policy import EnterprisePolicyAccessView
from authentik.enterprise.providers.rac.models import ConnectionToken, Endpoint, RACProvider
from authentik.flows.challenge import RedirectChallenge
from authentik.flows.exceptions import FlowNonApplicableException
from authentik.flows.models import in_memory_stage
from authentik.flows.planner import FlowPlanner
from authentik.flows.stage import RedirectStage
from authentik.flows.views.executor import SESSION_KEY_PLAN
from authentik.lib.utils.urls import redirect_with_qs
from authentik.policies.engine import PolicyEngine


class RACStartView(EnterprisePolicyAccessView):
    """Start a RAC connection by checking access and creating a connection token"""

    endpoint: Endpoint

    def resolve_provider_application(self):
        self.application = get_object_or_404(Application, slug=self.kwargs["app"])
        # Endpoint permissions are validated in the RACFinalStage below
        self.endpoint = get_object_or_404(Endpoint, pk=self.kwargs["endpoint"])
        self.provider = RACProvider.objects.get(application=self.application)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Start flow planner for RAC provider"""
        planner = FlowPlanner(self.provider.authorization_flow)
        planner.allow_empty_flows = True
        try:
            plan = planner.plan(self.request)
        except FlowNonApplicableException:
            raise Http404
        plan.insert_stage(
            in_memory_stage(
                RACFinalStage,
                endpoint=self.endpoint,
                provider=self.provider,
            )
        )
        request.session[SESSION_KEY_PLAN] = plan
        return redirect_with_qs(
            "authentik_core:if-flow",
            request.GET,
            flow_slug=self.provider.authorization_flow.slug,
        )


class RACInterface(InterfaceView):
    """Start RAC connection"""

    template_name = "if/rac.html"
    token: ConnectionToken

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # Early sanity check to ensure token still exists
        token = ConnectionToken.filter_not_expired(token=self.kwargs["token"]).first()
        if not token:
            return redirect("authentik_core:if-user")
        self.token = token
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        kwargs["token"] = self.token
        return super().get_context_data(**kwargs)


class RACFinalStage(RedirectStage):
    """RAC Connection final stage, set the connection token in the stage"""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        endpoint: Endpoint = self.executor.current_stage.endpoint
        engine = PolicyEngine(endpoint, self.request.user, self.request)
        engine.use_cache = False
        engine.build()
        passing = engine.result
        if not passing.passing:
            return self.executor.stage_invalid(", ".join(passing.messages))
        return super().dispatch(request, *args, **kwargs)

    def get_challenge(self, *args, **kwargs) -> RedirectChallenge:
        endpoint: Endpoint = self.executor.current_stage.endpoint
        provider: RACProvider = self.executor.current_stage.provider
        token = ConnectionToken.objects.create(
            provider=provider,
            endpoint=endpoint,
            settings=self.executor.plan.context.get("connection_settings", {}),
            session=AuthenticatedSession.objects.filter(
                session_key=self.request.session.session_key
            ).first(),
        )
        setattr(
            self.executor.current_stage,
            "destination",
            self.request.build_absolute_uri(
                reverse(
                    "authentik_providers_rac:if-rac",
                    kwargs={
                        "token": str(token.token),
                    },
                )
            ),
        )
        return super().get_challenge(*args, **kwargs)
