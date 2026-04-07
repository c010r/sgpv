from rest_framework import serializers

from inventory.models import (
    StockCountItem,
    StockCountSession,
    InventoryLocation,
    InventoryMovement,
    InventoryStock,
    Product,
    Recipe,
    RecipeItem,
)


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "sku", "unit", "sale_price", "cost_price", "is_active", "created_at", "updated_at"]


class RecipeItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeItem
        fields = ["id", "ingredient", "quantity"]


class RecipeSerializer(serializers.ModelSerializer):
    items = RecipeItemSerializer(many=True)

    class Meta:
        model = Recipe
        fields = ["id", "name", "sale_product", "items", "created_at", "updated_at"]

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        recipe = Recipe.objects.create(**validated_data)
        RecipeItem.objects.bulk_create([RecipeItem(recipe=recipe, **item) for item in items])
        return recipe

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()

        if items is not None:
            instance.items.all().delete()
            RecipeItem.objects.bulk_create([RecipeItem(recipe=instance, **item) for item in items])
        return instance


class InventoryLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryLocation
        fields = ["id", "name", "location_type", "bar", "is_active", "created_at", "updated_at"]


class InventoryStockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)

    class Meta:
        model = InventoryStock
        fields = ["id", "location", "location_name", "product", "product_name", "quantity", "updated_at"]


class InventoryMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryMovement
        fields = [
            "id",
            "movement_type",
            "product",
            "quantity",
            "source",
            "destination",
            "reason",
            "created_by",
            "created_at",
        ]


class TransferStockSerializer(serializers.Serializer):
    source_id = serializers.IntegerField()
    destination_id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    reason = serializers.CharField(required=False, allow_blank=True)


class BulkTransferItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)


class BulkTransferStockSerializer(serializers.Serializer):
    source_id = serializers.IntegerField()
    destination_id = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True)
    items = BulkTransferItemSerializer(many=True)


class AdjustStockSerializer(serializers.Serializer):
    location_id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    quantity_delta = serializers.DecimalField(max_digits=14, decimal_places=3)
    reason = serializers.CharField(required=False, allow_blank=True)


class StockCountSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockCountSession
        fields = [
            "id",
            "location",
            "status",
            "notes",
            "created_by",
            "closed_by",
            "applied_by",
            "closed_at",
            "applied_at",
            "created_at",
        ]


class StockCountItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = StockCountItem
        fields = [
            "id",
            "session",
            "product",
            "product_name",
            "expected_quantity",
            "counted_quantity",
            "difference_quantity",
        ]


class StartStockCountSerializer(serializers.Serializer):
    location_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True)


class CloseStockCountSerializer(serializers.Serializer):
    counted = serializers.DictField(
        child=serializers.DecimalField(max_digits=14, decimal_places=3),
        help_text="Mapa product_id -> counted_quantity",
    )
