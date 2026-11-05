from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from reservas.models import Reserva, Sala


class SalaSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(
        max_length=80,
        validators=[
            UniqueValidator(
                queryset=Sala.objects.all(),
                lookup="iexact",
                message="Já existe uma sala com este nome.",
            )
        ],
    )

    class Meta:
        model = Sala
        fields = ["id", "nome", "capacidade", "ativa", "criada_em"]
        # extra_kwargs, e não campo declarado: preserva o max_value que o DRF
        # deriva do PositiveSmallIntegerField.
        extra_kwargs = {
            "capacidade": {
                "min_value": 1,
                "error_messages": {"min_value": "A capacidade deve ser no mínimo 1."},
            }
        }


class ReservaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reserva
        fields = [
            "id",
            "sala",
            "usuario",
            "inicio",
            "fim",
            "titulo",
            "status",
            "criada_em",
        ]
        read_only_fields = ["usuario", "status", "criada_em"]


class ReservaAlteracaoSerializer(ReservaSerializer):
    class Meta(ReservaSerializer.Meta):
        read_only_fields = ["sala", "usuario", "status", "criada_em"]
