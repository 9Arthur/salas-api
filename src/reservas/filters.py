import django_filters

from reservas.models import Reserva


class ReservaFilter(django_filters.FilterSet):
    de = django_filters.DateFilter(field_name="inicio", lookup_expr="date__gte")
    ate = django_filters.DateFilter(field_name="inicio", lookup_expr="date__lte")

    class Meta:
        model = Reserva
        fields = ["sala"]
