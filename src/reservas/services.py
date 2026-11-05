from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from reservas.models import Reserva

DURACAO_MINIMA = timedelta(minutes=15)
DURACAO_MAXIMA = timedelta(hours=8)
CONSTRAINT_SOBREPOSICAO = "reserva_sem_sobreposicao"


def criar_reserva(usuario, sala, inicio, fim, titulo):
    _validar_horario(sala, inicio, fim)
    return _gravar(
        lambda: Reserva.objects.create(
            sala=sala, usuario=usuario, inicio=inicio, fim=fim, titulo=titulo
        )
    )


def alterar_reserva(reserva, inicio, fim, titulo):
    if reserva.status == Reserva.Status.CANCELADA:
        raise ValidationError(
            {"non_field_errors": ["Reserva cancelada não pode ser alterada."]}
        )
    if (inicio, fim) != (reserva.inicio, reserva.fim):
        _validar_horario(reserva.sala, inicio, fim)
    reserva.inicio = inicio
    reserva.fim = fim
    reserva.titulo = titulo
    _gravar(reserva.save)
    return reserva


def _validar_horario(sala, inicio, fim):
    if not sala.ativa:
        raise ValidationError({"sala": ["Sala inativa não aceita reservas."]})
    if fim <= inicio:
        raise ValidationError({"fim": ["O fim deve ser depois do início."]})
    if inicio < timezone.now():
        raise ValidationError({"inicio": ["Reserva não pode começar no passado."]})
    duracao = fim - inicio
    if duracao < DURACAO_MINIMA:
        raise ValidationError({"fim": ["A reserva deve durar pelo menos 15 minutos."]})
    if duracao > DURACAO_MAXIMA:
        raise ValidationError({"fim": ["A reserva pode durar no máximo 8 horas."]})


def _gravar(operacao):
    try:
        with transaction.atomic():
            return operacao()
    except IntegrityError as erro:
        if _constraint_violada(erro) == CONSTRAINT_SOBREPOSICAO:
            raise ValidationError(
                {
                    "non_field_errors": [
                        "Já existe uma reserva confirmada nesta sala nesse horário."
                    ]
                }
            ) from erro
        raise


def _constraint_violada(erro):
    diag = getattr(erro.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None)
