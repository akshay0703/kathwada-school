import logging

from rest_framework.views import exception_handler

logger = logging.getLogger("kathwada")


def api_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler so every error response has a
    consistent {"detail": "..."} shape, and unexpected (500-class) errors are
    logged server-side without leaking stack traces to the client.
    """
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled exception in %s", context.get("view"))
        return None
    return response
