from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer
from .throttles import LoginThrottle


def success_response(data, status_code=status.HTTP_200_OK):
    return Response({"success": True, "data": data}, status=status_code)


def error_response(errors, status_code=status.HTTP_400_BAD_REQUEST):
    return Response({"success": False, "errors": errors}, status=status_code)


class RegisterView(APIView):
    """
    Register a new user.

    POST /api/v1/auth/register/
    Payload: { "email": "...", "password": "...", "confirm_password": "..." }
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        data = UserSerializer(user).data
        return success_response(data, status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    Log a user in and return JWT access and refresh tokens.

    POST /api/v1/auth/login/
    Payload: { "email": "...", "password": "..." }
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
        return success_response(data, status.HTTP_200_OK)


class TokenRefreshView(APIView):
    """
    Refresh an access token.

    POST /api/v1/auth/token/refresh/
    Payload: { "refresh": "<refresh_token>" }
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = TokenRefreshSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        return success_response(data, status.HTTP_200_OK)


class MeView(APIView):
    """
    Return the authenticated user's profile.

    GET /api/v1/auth/me/
    """

    def get(self, request, *args, **kwargs):
        user = request.user
        data = UserSerializer(user).data
        return success_response(data, status.HTTP_200_OK)


class LogoutView(APIView):
    """
    Log a user out by invalidating the provided refresh token when blacklist
    support is enabled. Otherwise, instruct the client to delete tokens.

    POST /api/v1/auth/logout/
    Payload: { "refresh": "<refresh_token>" }
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return error_response(
                {"refresh": ["This field is required."]},
                status.HTTP_400_BAD_REQUEST,
            )

        blacklist_enabled = (
            "rest_framework_simplejwt.token_blacklist" in settings.INSTALLED_APPS
        )

        if blacklist_enabled:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError as exc:
                return error_response(
                    {"refresh": [str(exc)]},
                    status.HTTP_400_BAD_REQUEST,
                )

            return success_response(
                {"detail": "Refresh token blacklisted. Client should discard tokens."},
                status.HTTP_200_OK,
            )

        # Fallback when blacklist is not enabled
        return success_response(
            {
                "detail": (
                    "Token blacklist is not enabled on the server. "
                    "Client should delete stored access and refresh tokens."
                )
            },
            status.HTTP_200_OK,
        )

