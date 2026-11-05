from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
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


class TsTzRange(models.Func):
    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class Reserva(models.Model):
    class Status(models.TextChoices):
        CONFIRMADA = "CONFIRMADA"
        CANCELADA = "CANCELADA"

    sala = models.ForeignKey(Sala, on_delete=models.PROTECT, related_name="reservas")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    inicio = models.DateTimeField()
    fim = models.DateTimeField()
    titulo = models.CharField(max_length=120)
    status = models.CharField(choices=Status.choices, default=Status.CONFIRMADA)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fim__gt=models.F("inicio")),
                name="reserva_fim_apos_inicio",
            ),
            ExclusionConstraint(
                name="reserva_sem_sobreposicao",
                expressions=[
                    ("sala", RangeOperators.EQUAL),
                    (TsTzRange("inicio", "fim"), RangeOperators.OVERLAPS),
                ],
                condition=models.Q(status="CONFIRMADA"),
            ),
        ]
