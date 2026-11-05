from datetime import UTC, datetime

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from reservas.models import Sala


def _em(hora, minuto=0):
    return datetime(2027, 1, 4, hora, minuto, tzinfo=UTC)


@pytest.fixture
def usuario():
    return get_user_model().objects.create_user(
        username="ana", email="ana@exemplo.com", password="senha-forte-123"
    )


@pytest.fixture
def sala_a():
    return Sala.objects.create(nome="Sala A", capacidade=10)


@pytest.fixture
def sala_b():
    return Sala.objects.create(nome="Sala B", capacidade=6)


@pytest.mark.django_db
def test_sa_25_sobreposicao_na_mesma_sala_da_integrity_error(usuario, sala_a):
    from reservas.models import Reserva

    Reserva.objects.create(
        sala=sala_a, usuario=usuario, inicio=_em(10), fim=_em(11), titulo="Reunião"
    )

    with (
        pytest.raises(IntegrityError, match="reserva_sem_sobreposicao"),
        transaction.atomic(),
    ):
        Reserva.objects.create(
            sala=sala_a,
            usuario=usuario,
            inicio=_em(10, 30),
            fim=_em(11, 30),
            titulo="Reunião",
        )

    assert Reserva.objects.count() == 1


@pytest.mark.django_db
def test_sa_27_reserva_encostada_grava(usuario, sala_a):
    from reservas.models import Reserva

    Reserva.objects.create(
        sala=sala_a, usuario=usuario, inicio=_em(10), fim=_em(11), titulo="Reunião"
    )
    Reserva.objects.create(
        sala=sala_a, usuario=usuario, inicio=_em(11), fim=_em(12), titulo="Reunião"
    )

    assert Reserva.objects.count() == 2


@pytest.mark.django_db
def test_sa_25_mesma_faixa_em_outra_sala_grava(usuario, sala_a, sala_b):
    from reservas.models import Reserva

    Reserva.objects.create(
        sala=sala_a, usuario=usuario, inicio=_em(10), fim=_em(11), titulo="Reunião"
    )
    Reserva.objects.create(
        sala=sala_b, usuario=usuario, inicio=_em(10), fim=_em(11), titulo="Reunião"
    )

    assert Reserva.objects.count() == 2


@pytest.mark.django_db
def test_sa_25_reserva_cancelada_libera_a_faixa(usuario, sala_a):
    from reservas.models import Reserva

    Reserva.objects.create(
        sala=sala_a,
        usuario=usuario,
        inicio=_em(10),
        fim=_em(11),
        titulo="Reunião",
        status=Reserva.Status.CANCELADA,
    )
    Reserva.objects.create(
        sala=sala_a, usuario=usuario, inicio=_em(10), fim=_em(11), titulo="Reunião"
    )

    assert Reserva.objects.count() == 2


@pytest.mark.django_db
def test_sa_26_fim_antes_do_inicio_da_integrity_error(usuario, sala_a):
    from reservas.models import Reserva

    with (
        pytest.raises(IntegrityError, match="reserva_fim_apos_inicio"),
        transaction.atomic(),
    ):
        Reserva.objects.create(
            sala=sala_a,
            usuario=usuario,
            inicio=_em(11),
            fim=_em(10),
            titulo="Reunião",
            # explícito: o índice parcial só calcula o TSTZRANGE em CONFIRMADA
            status=Reserva.Status.CONFIRMADA,
        )

    assert Reserva.objects.count() == 0


@pytest.mark.django_db
def test_sa_26_fim_igual_ao_inicio_da_integrity_error(usuario, sala_a):
    from reservas.models import Reserva

    with (
        pytest.raises(IntegrityError, match="reserva_fim_apos_inicio"),
        transaction.atomic(),
    ):
        Reserva.objects.create(
            sala=sala_a,
            usuario=usuario,
            inicio=_em(10),
            fim=_em(10),
            titulo="Reunião",
            status=Reserva.Status.CONFIRMADA,
        )

    assert Reserva.objects.count() == 0
