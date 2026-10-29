from django.db import models
from django.db.models.functions import Lower


class Sala(models.Model):
    nome = models.CharField(max_length=80)
    capacidade = models.PositiveSmallIntegerField()
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(Lower("nome"), name="sala_nome_unico_ci"),
            models.CheckConstraint(
                condition=models.Q(capacidade__gte=1), name="sala_capacidade_minima"
            ),
        ]
