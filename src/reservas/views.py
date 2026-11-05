from django.db.models import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from reservas.filters import ReservaFilter
from reservas.models import Reserva, Sala
from reservas.permissions import EhDonoOuAdmin
from reservas.serializers import (
    ReservaAlteracaoSerializer,
    ReservaSerializer,
    SalaSerializer,
)
from reservas.services import alterar_reserva, cancelar_reserva, criar_reserva


class SalaComReservas(APIException):
    status_code = 409
    default_detail = "Sala com reservas não pode ser apagada; desative-a."
    default_code = "sala_com_reservas"


class SalaViewSet(ModelViewSet):
    serializer_class = SalaSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def get_queryset(self):
        queryset = Sala.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(ativa=True)
        return queryset

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as erro:
            raise SalaComReservas from erro


class ReservaViewSet(ModelViewSet):
    serializer_class = ReservaSerializer
    permission_classes = [IsAuthenticated, EhDonoOuAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReservaFilter
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        reservas = Reserva.objects.order_by("inicio", "id")
        if self.request.user.is_staff:
            return reservas
        return reservas.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        serializer.instance = criar_reserva(
            usuario=self.request.user, **serializer.validated_data
        )

    def get_serializer_class(self):
        if self.action == "partial_update":
            return ReservaAlteracaoSerializer
        return ReservaSerializer

    def perform_update(self, serializer):
        reserva = serializer.instance
        dados = serializer.validated_data
        serializer.instance = alterar_reserva(
            reserva,
            inicio=dados.get("inicio", reserva.inicio),
            fim=dados.get("fim", reserva.fim),
            titulo=dados.get("titulo", reserva.titulo),
        )

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        reserva = cancelar_reserva(self.get_object(), por=request.user)
        return Response(self.get_serializer(reserva).data)
