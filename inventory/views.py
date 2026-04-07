from django.core.exceptions import ValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from inventory.models import InventoryLocation, InventoryMovement, InventoryStock, Product, Recipe
from inventory.serializers import (
    AdjustStockSerializer,
    InventoryLocationSerializer,
    InventoryMovementSerializer,
    InventoryStockSerializer,
    ProductSerializer,
    RecipeSerializer,
    TransferStockSerializer,
)
from inventory.services import adjust_stock, ensure_central_inventory, transfer_stock
from users.permissions import IsCajeroOrAbove, IsSupervisorOrAbove


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("id")
    serializer_class = ProductSerializer
    permission_classes = [IsSupervisorOrAbove]


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.prefetch_related("items").all().order_by("id")
    serializer_class = RecipeSerializer
    permission_classes = [IsSupervisorOrAbove]


class InventoryLocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryLocation.objects.select_related("bar").all().order_by("id")
    serializer_class = InventoryLocationSerializer
    permission_classes = [IsCajeroOrAbove]


class InventoryStockViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryStock.objects.select_related("location", "product").all().order_by("id")
    serializer_class = InventoryStockSerializer
    permission_classes = [IsCajeroOrAbove]


class InventoryMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryMovement.objects.select_related("product", "source", "destination", "created_by").all().order_by("-id")
    serializer_class = InventoryMovementSerializer
    permission_classes = [IsCajeroOrAbove]

    @action(methods=["post"], detail=False, permission_classes=[IsSupervisorOrAbove])
    def transfer(self, request):
        serializer = TransferStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        source = InventoryLocation.objects.filter(id=data["source_id"]).first()
        destination = InventoryLocation.objects.filter(id=data["destination_id"]).first()
        product = Product.objects.filter(id=data["product_id"]).first()
        if not source or not destination or not product:
            return Response({"detail": "source/destination/product invalido"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            transfer_stock(
                source=source,
                destination=destination,
                product=product,
                quantity=data["quantity"],
                user=request.user,
                reason=data.get("reason", ""),
            )
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Transferencia aplicada"})

    @action(methods=["post"], detail=False, permission_classes=[IsSupervisorOrAbove])
    def adjust(self, request):
        serializer = AdjustStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        location = InventoryLocation.objects.filter(id=data["location_id"]).first()
        product = Product.objects.filter(id=data["product_id"]).first()
        if not location or not product:
            return Response({"detail": "location/product invalido"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            adjust_stock(
                location=location,
                product=product,
                quantity_delta=data["quantity_delta"],
                user=request.user,
                reason=data.get("reason", ""),
            )
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Ajuste aplicado"})


class InventorySetupViewSet(viewsets.ViewSet):
    permission_classes = [IsSupervisorOrAbove]

    @action(methods=["post"], detail=False)
    def create_central(self, request):
        location, created = ensure_central_inventory()
        payload = InventoryLocationSerializer(location).data
        return Response({"created": created, "location": payload})
