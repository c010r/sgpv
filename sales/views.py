from django.core.exceptions import ValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from inventory.models import Product
from sales.models import CashRegister, CashSession, Sale
from sales.serializers import (
    CancelSaleSerializer,
    CashRegisterSerializer,
    CashSessionSerializer,
    CloseCashSessionSerializer,
    OpenCashSessionSerializer,
    SaleCreateSerializer,
    SaleSerializer,
)
from sales.services import cancel_sale, close_cash_session, create_sale, open_cash_session
from settings_app.models import BarSession
from users.permissions import IsCajeroOrAbove, IsSupervisorOrAbove


class CashRegisterViewSet(viewsets.ModelViewSet):
    queryset = CashRegister.objects.select_related("bar").all().order_by("id")
    serializer_class = CashRegisterSerializer
    permission_classes = [IsSupervisorOrAbove]


class CashSessionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CashSession.objects.select_related("register", "opened_by", "closed_by").all().order_by("-id")
    serializer_class = CashSessionSerializer
    permission_classes = [IsCajeroOrAbove]

    def get_permissions(self):
        if self.action in {"list", "retrieve", "open", "close"}:
            return [IsCajeroOrAbove()]
        return super().get_permissions()

    @action(methods=["post"], detail=False)
    def open(self, request):
        serializer = OpenCashSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        register = CashRegister.objects.filter(id=serializer.validated_data["register_id"], is_active=True).first()
        if not register:
            return Response({"detail": "Caja no encontrada o inactiva"}, status=status.HTTP_404_NOT_FOUND)

        if CashSession.objects.filter(register=register, is_open=True).exists():
            return Response({"detail": "Ya existe una sesion abierta para esta caja"}, status=status.HTTP_400_BAD_REQUEST)

        session = open_cash_session(
            register=register,
            opening_amount=serializer.validated_data["opening_amount"],
            user=request.user,
        )
        return Response(self.get_serializer(session).data, status=status.HTTP_201_CREATED)

    @action(methods=["post"], detail=True)
    def close(self, request, pk=None):
        serializer = CloseCashSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = self.get_object()
        try:
            session = close_cash_session(
                session=session,
                closing_amount=serializer.validated_data["closing_amount"],
                user=request.user,
            )
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.get_serializer(session).data)


class SaleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sale.objects.select_related("bar_session", "cash_session", "created_by").prefetch_related("items", "payments").all().order_by("-id")
    serializer_class = SaleSerializer
    permission_classes = [IsCajeroOrAbove]

    def get_permissions(self):
        if self.action in {"cancel"}:
            return [IsSupervisorOrAbove()]
        if self.action in {"list", "retrieve", "create_sale"}:
            return [IsCajeroOrAbove()]
        return super().get_permissions()

    @action(methods=["post"], detail=False)
    def create_sale(self, request):
        serializer = SaleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        bar_session = BarSession.objects.filter(id=data["bar_session_id"]).first()
        cash_session = CashSession.objects.filter(id=data["cash_session_id"]).first()
        if not bar_session or not cash_session:
            return Response({"detail": "Sesion de barra o caja invalida"}, status=status.HTTP_400_BAD_REQUEST)

        items = []
        for item in data["items"]:
            product = Product.objects.filter(id=item["product_id"], is_active=True).first()
            if not product:
                return Response({"detail": f"Producto {item['product_id']} invalido"}, status=status.HTTP_400_BAD_REQUEST)
            items.append(
                {
                    "product": product,
                    "quantity": item["quantity"],
                    "unit_price": item.get("unit_price"),
                }
            )

        try:
            sale = create_sale(
                bar_session=bar_session,
                cash_session=cash_session,
                items=items,
                payments=data["payments"],
                user=request.user,
            )
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payload = SaleSerializer(sale).data
        return Response(payload, status=status.HTTP_201_CREATED)

    @action(methods=["post"], detail=True)
    def cancel(self, request, pk=None):
        serializer = CancelSaleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sale = self.get_object()
        try:
            sale = cancel_sale(sale=sale, reason=serializer.validated_data["reason"], user=request.user)
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(SaleSerializer(sale).data)
