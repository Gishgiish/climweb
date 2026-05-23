from django.http import HttpResponseServerError
from django.db import DatabaseError, OperationalError


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

    def __call__(self, request):
        try:
            return self.get_response(request)
        except (OperationalError, DatabaseError) as exc:
            path = (request.path or "").lower()
            # Only return a safe 503 for the mapviewer path (and its subpaths).
            if path.startswith("/mapviewer"):
                return HttpResponseServerError(
                    "Service temporarily unavailable due to database issues. Please try again later.",
                    content_type="text/plain",
                )
            # For other paths, re-raise so other handlers can manage it.
            raise
