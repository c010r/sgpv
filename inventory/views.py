from django.core.exceptions import ValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from inventory.models import InventoryLocation, InventoryMovement, InventoryStock, Product, Recipe
from inventory.serializers import (
    AdjustStockSerializer,
    BulkTransferStockSerializer,
    CloseStockCountSerializer,
    InventoryLocationSerializer,
    InventoryMovementSerializer,
    InventoryStockSerializer,
    ProductSerializer,
    RecipeSerializer,
    StartStockCountSerializer,
    StockCountItemSerializer,
    StockCountSessionSerializer,
    TransferStockSerializer,
)
from inventory.services import (
    adjust_stock,
    apply_stock_count,
    close_stock_count,
    ensure_central_inventory,
    start_stock_count,
    transfer_stock,
)
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

    @action(methods=["post"], detail=False, permission_classes=[IsSupervisorOrAbove])
    def bulk_transfer(self, request):
        serializer = BulkTransferStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        source = InventoryLocation.objects.filter(id=data["source_id"]).first()
        destination = InventoryLocation.objects.filter(id=data["destination_id"]).first()
        if not source or not destination:
            return Response({"detail": "source/destination invalido"}, status=status.HTTP_400_BAD_REQUEST)

        errors = []
        applied = []
        for item in data["items"]:
            product = Product.objects.filter(id=item["product_id"]).first()
            if not product:
                errors.append(f"Producto {item['product_id']} invalido")
                continue
            try:
                transfer_stock(
                    source=source,
                    destination=destination,
                    product=product,
                    quantity=item["quantity"],
                    user=request.user,
                    reason=data.get("reason", ""),
                )
                applied.append({"product_id": product.id, "quantity": str(item["quantity"])})
            except ValidationError as exc:
                errors.append(f"{product.id}: {exc}")

        status_code = status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS
        return Response({"applied": applied, "errors": errors}, status=status_code)


class InventorySetupViewSet(viewsets.ViewSet):
    permission_classes = [IsSupervisorOrAbove]

    @action(methods=["post"], detail=False)
    def create_central(self, request):
        location, created = ensure_central_inventory()
        payload = InventoryLocationSerializer(location).data
        return Response({"created": created, "location": payload})


class StockCountViewSet(viewsets.ViewSet):
    permission_classes = [IsSupervisorOrAbove]

    @action(methods=["post"], detail=False)
    def start(self, request):
        serializer = StartStockCountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        location = InventoryLocation.objects.filter(id=serializer.validated_data["location_id"]).first()
        if not location:
            return Response({"detail": "location invalido"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            session = start_stock_count(
                location=location,
                user=request.user,
                notes=serializer.validated_data.get("notes", ""),
            )
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StockCountSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @action(methods=["get"], detail=True)
    def items(self, request, pk=None):
        from inventory.models import StockCountSession

        session = StockCountSession.objects.filter(id=pk).first()
        if not session:
            return Response({"detail": "Conteo no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        rows = session.items.select_related("product").all().order_by("product__name")
        return Response(StockCountItemSerializer(rows, many=True).data)

    @action(methods=["post"], detail=True)
    def close(self, request, pk=None):
        from inventory.models import StockCountSession

        serializer = CloseStockCountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = StockCountSession.objects.filter(id=pk).first()
        if not session:
            return Response({"detail": "Conteo no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        try:
            session = close_stock_count(
                session=session,
                counted_map=serializer.validated_data["counted"],
                user=request.user,
            )
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StockCountSessionSerializer(session).data)

    @action(methods=["post"], detail=True)
    def apply(self, request, pk=None):
        from inventory.models import StockCountSession

        session = StockCountSession.objects.filter(id=pk).first()
        if not session:
            return Response({"detail": "Conteo no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        try:
            session = apply_stock_count(session=session, user=request.user)
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StockCountSessionSerializer(session).data)
