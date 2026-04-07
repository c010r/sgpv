from zoneinfo import available_timezones

from rest_framework import serializers

from settings_app.models import Bar, BarSession, SystemConfiguration


class SystemConfigurationSerializer(serializers.ModelSerializer):
    def validate_country_code(self, value):
        normalized = (value or "").strip().upper()
        if len(normalized) not in {2, 3} or not normalized.isalpha():
            raise serializers.ValidationError("country_code debe ser ISO alpha-2 o alpha-3 (solo letras).")
        return normalized

    def validate_currency_code(self, value):
        normalized = (value or "").strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise serializers.ValidationError("currency_code debe ser ISO 4217 de 3 letras.")
        return normalized

    def validate_timezone(self, value):
        tz = (value or "").strip()
        if tz not in available_timezones():
            raise serializers.ValidationError("timezone invalida. Ejemplo: America/Montevideo")
        return tz

    class Meta:
        model = SystemConfiguration
        fields = ["id", "country_code", "currency_code", "timezone", "costing_method", "created_at", "updated_at"]


class BarSerializer(serializers.ModelSerializer):
    def validate_name(self, value):
        normalized = (value or "").strip()
        if not normalized:
            raise serializers.ValidationError("name es requerido")
        return normalized

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
