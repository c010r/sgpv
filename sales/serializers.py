from rest_framework import serializers

from sales.models import CashRegister, CashSession, Sale, SaleItem, SalePayment


class CashRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashRegister
        fields = ["id", "name", "bar", "is_active", "created_at", "updated_at"]


class CashSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashSession
        fields = [
            "id",
            "register",
            "opened_by",
            "closed_by",
            "opening_amount",
            "expected_amount",
            "closing_amount",
            "expected_breakdown",
            "closing_breakdown",
            "difference_breakdown",
            "difference_amount",
            "close_status",
            "approved_by",
            "approved_at",
            "reopened_by",
            "reopened_at",
            "reopen_reason",
            "is_open",
            "opened_at",
            "closed_at",
        ]
        read_only_fields = [
            "opened_by",
            "closed_by",
            "expected_amount",
            "expected_breakdown",
            "closing_breakdown",
            "difference_breakdown",
            "difference_amount",
            "close_status",
            "approved_by",
            "approved_at",
            "reopened_by",
            "reopened_at",
            "reopen_reason",
            "is_open",
            "opened_at",
            "closed_at",
        ]


class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = ["id", "product", "quantity", "unit_price", "unit_cost", "line_total", "line_cost_total", "line_profit"]
        read_only_fields = ["line_total"]


class SalePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalePayment
        fields = ["id", "method", "amount"]


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)
    payments = SalePaymentSerializer(many=True)

    class Meta:
        model = Sale
        fields = [
            "id",
            "bar_session",
            "cash_session",
            "created_by",
            "status",
            "cancel_reason",
            "idempotency_key",
            "subtotal",
            "discount_amount",
            "surcharge_amount",
            "cost_total",
            "gross_profit",
            "total",
            "items",
            "payments",
            "created_at",
        ]
        read_only_fields = ["created_by", "status", "cancel_reason", "subtotal", "total"]


class OpenCashSessionSerializer(serializers.Serializer):
    register_id = serializers.IntegerField()
    opening_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class CloseCashSessionSerializer(serializers.Serializer):
    breakdown = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=2),
        required=True,
        help_text="Mapa por metodo: CASH/CARD/TRANSFER",
    )


class ApproveCashSessionSerializer(serializers.Serializer):
    approve = serializers.BooleanField(default=True)


class ReopenCashSessionSerializer(serializers.Serializer):
    reason = serializers.CharField()


class SaleCreateItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class SaleCreatePaymentSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=SalePayment.Method.choices)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class SaleCreateSerializer(serializers.Serializer):
    bar_session_id = serializers.IntegerField()
    cash_session_id = serializers.IntegerField()
    idempotency_key = serializers.CharField(required=False, allow_blank=True)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    surcharge_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    items = SaleCreateItemSerializer(many=True)
    payments = SaleCreatePaymentSerializer(many=True)


class CancelSaleSerializer(serializers.Serializer):
    reason = serializers.CharField()
