from rest_framework import serializers

from settings_app.models import Bar, BarSession, SystemConfiguration


class SystemConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfiguration
        fields = ["id", "country_code", "currency_code", "timezone", "created_at", "updated_at"]


class BarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bar
        fields = ["id", "name", "is_active", "created_at", "updated_at"]


class BarSessionSerializer(serializers.ModelSerializer):
    bar_name = serializers.CharField(source="bar.name", read_only=True)

    class Meta:
        model = BarSession
        fields = [
            "id",
            "bar",
            "bar_name",
            "opened_by",
            "closed_by",
            "opened_at",
            "closed_at",
            "is_open",
        ]
        read_only_fields = ["opened_by", "closed_by", "opened_at", "closed_at", "is_open"]
