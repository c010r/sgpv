from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True)
