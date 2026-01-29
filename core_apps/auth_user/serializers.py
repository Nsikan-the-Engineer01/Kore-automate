from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Public representation of the authenticated user."""

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name")
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_email(self, value: str) -> str:
        # Enforce email uniqueness in a case-insensitive way
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(_("A user with this email already exists."))
        return value

    def validate(self, attrs):
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")

        if password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": [_("Password and confirm password do not match.")]}
            )

        # Use Django's built-in password validators
        validate_password(password=password)
        return attrs

    def create(self, validated_data):
        email = validated_data["email"]
        password = validated_data["password"]

        # Use email as username for the default User model.
        # This remains compatible if a custom user model is introduced later.
        username = email

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth.hashers import check_password

        email = attrs.get("email")
        password = attrs.get("password")

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"non_field_errors": [_("Invalid email or password.")]}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"non_field_errors": [_("This account is inactive.")]}
            )

        if not check_password(password, user.password):
            raise serializers.ValidationError(
                {"non_field_errors": [_("Invalid email or password.")]}
            )

        attrs["user"] = user
        return attrs

