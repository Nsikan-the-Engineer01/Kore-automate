from django.http import JsonResponse


def health(request):
    """
    Simple health check endpoint.

    Returns HTTP 200 and a minimal JSON payload that can be used by
    load balancers or uptime monitors.
    """
    return JsonResponse({"status": "ok"})
