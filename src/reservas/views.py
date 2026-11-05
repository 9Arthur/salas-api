from django.db.models import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
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
        reservas = Reserva.objects.select_related("sala", "usuario").order_by(
            "inicio", "id"
        )
        # SA-47: o drf-spectacular chama get_queryset sem usuário ao gerar o schema.
        if getattr(self, "swagger_fake_view", False):
            return reservas.none()
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
        # SA-49: só o que veio no corpo; o serviço completa o resto sob a trava.
        serializer.instance = alterar_reserva(
            serializer.instance, **serializer.validated_data
        )

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        reserva = cancelar_reserva(self.get_object(), por=request.user)
        return Response(self.get_serializer(reserva).data)
