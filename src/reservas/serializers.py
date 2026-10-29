from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from reservas.models import Sala


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
