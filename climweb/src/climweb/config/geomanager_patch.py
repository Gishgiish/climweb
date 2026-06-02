"""Runtime patch to make geomanager's NextJS map_view resilient to DB failures.

This module is imported from `climweb.config.apps.DbEngineConfig.ready()` so it
runs when Django apps are ready. It wraps `geomanager.views.nextjs.map_view`
to return HTTP 503 on DB OperationalError/DatabaseError instead of crashing the
request.
"""
from django.db import DatabaseError, OperationalError
from django.conf import settings

try:
    from geomanager.views import nextjs as gm_nextjs
    original_map_view = getattr(gm_nextjs, "map_view", None)

    if original_map_view:
        def _safe_map_view(request, *args, **kwargs):
            # If NEXTJS is not configured, avoid calling into the renderer
            # which will attempt to contact an external Next.js server and
            # raise aiohttp InvalidUrl errors. Return 503 immediately.
            if not getattr(settings, "NEXTJS_SERVER_URL", None):
                from django.http import HttpResponse
                return HttpResponse("MapViewer unavailable (NEXTJS not configured)", status=503)

            try:
                return original_map_view(request, *args, **kwargs)
            except (OperationalError, DatabaseError):
                from django.http import HttpResponse
                return HttpResponse("Service temporarily unavailable", status=503)
            except Exception:
                # Best-effort: any other runtime error while rendering NextJS
                # should not crash the whole request pipeline. Return 503 so
                # the reverse-proxy / health checks can react accordingly.
                from django.http import HttpResponse
                return HttpResponse("Service temporarily unavailable", status=503)

        gm_nextjs.map_view = _safe_map_view
except Exception:
    # Best-effort patch: if geomanager is unavailable, silently skip.
    pass
