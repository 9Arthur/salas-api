from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from reservas.models import Sala
from reservas.serializers import SalaSerializer


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
