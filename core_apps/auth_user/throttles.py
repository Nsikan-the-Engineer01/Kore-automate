from rest_framework.throttling import AnonRateThrottle


class LoginThrottle(AnonRateThrottle):
    """
    Throttle class for login (and OTP) endpoints.

    The actual rate is configured via the REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
    setting using the 'login' scope, e.g.:

        THROTTLE_RATE_LOGIN=10/min
    """

    scope = "login"

