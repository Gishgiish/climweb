from django.http import HttpResponseServerError
from django.db import DatabaseError, OperationalError
import asyncio


class DBFailureResilientMiddleware:
    """Catch DB OperationalErrors during view execution and return a
    simple 503 response for paths that are known to be fragile (e.g.
    /mapviewer/). This avoids cascade failures when the DB is down.

    The middleware is intentionally conservative: it only swallows
    database errors and returns a readable 503 page. Other exceptions
    are re-raised so normal error handling applies.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._is_coroutine = asyncio.iscoroutinefunction(get_response)

    def __call__(self, request):
        if self._is_coroutine:
            return self._call_async(request)
        return self._call_sync(request)

    def _call_sync(self, request):
        try:
            return self.get_response(request)
        except (OperationalError, DatabaseError):
            path = (request.path or "").lower()
            if path.startswith("/mapviewer"):
                return HttpResponseServerError(
                    "Service temporarily unavailable due to database issues. Please try again later.",
                    content_type="text/plain",
                )
            raise

    async def _call_async(self, request):
        try:
            return await self.get_response(request)
        except (OperationalError, DatabaseError):
            path = (request.path or "").lower()
            if path.startswith("/mapviewer"):
                return HttpResponseServerError(
                    "Service temporarily unavailable due to database issues. Please try again later.",
                    content_type="text/plain",
                )
            raise
