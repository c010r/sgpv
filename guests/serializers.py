from rest_framework import serializers

from guests.models import GuestEntry, GuestList


class GuestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestList
        fields = ["id", "name", "event_date", "created_by", "created_at", "updated_at"]
        read_only_fields = ["created_by"]


class GuestEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestEntry
        fields = [
            "id",
            "guest_list",
            "full_name",
            "document_id",
            "qr_code",
            "companions_allowed",
            "companions_used",
            "status",
            "checked_in_at",
            "checked_in_by",
            "created_at",
        ]
        read_only_fields = ["checked_in_at", "checked_in_by"]


class GuestCheckinSerializer(serializers.Serializer):
    qr_code = serializers.CharField()
    companions_used = serializers.IntegerField(default=0)
