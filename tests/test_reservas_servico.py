from datetime import UTC, datetime

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from reservas.models import Reserva, Sala

AGORA = datetime(2027, 1, 4, 9, 0, tzinfo=UTC)


def _em(hora, minuto=0, segundo=0):
    return datetime(2027, 1, 4, hora, minuto, segundo, tzinfo=UTC)


@pytest.fixture(autouse=True)
def agora_fixo(monkeypatch):
    monkeypatch.setattr(timezone, "now", lambda: AGORA)


@pytest.fixture
def usuario():
    return get_user_model().objects.create_user(
        username="ana", email="ana@exemplo.com", password="senha-forte-123"
    )


@pytest.fixture
def sala_a():
    return Sala.objects.create(nome="Sala A", capacidade=10)


@pytest.fixture
def sala_inativa():
    return Sala.objects.create(nome="Sala Inativa", capacidade=4, ativa=False)


@pytest.mark.django_db
def test_sa_30_cria_reserva_valida(usuario, sala_a):
    from reservas.services import criar_reserva

    r = criar_reserva(
        usuario=usuario, sala=sala_a, inicio=_em(10), fim=_em(11), titulo="Reunião"
    )

    assert r.pk is not None
    assert r.status == Reserva.Status.CONFIRMADA
    assert r.sala == sala_a
    assert r.usuario == usuario
    assert r.titulo == "Reunião"
    assert r.inicio == _em(10)
    assert r.fim == _em(11)
    assert Reserva.objects.count() == 1


@pytest.mark.django_db
def test_l_5_sala_inativa_levanta_erro(usuario, sala_inativa):
    from reservas.services import criar_reserva

    with pytest.raises(ValidationError) as exc:
        criar_reserva(
            usuario=usuario,
            sala=sala_inativa,
            inicio=_em(10),
            fim=_em(11),
            titulo="Reunião",
        )

    assert exc.value.detail == {"sala": ["Sala inativa não aceita reservas."]}
    assert Reserva.objects.count() == 0


@pytest.mark.django_db
def test_sa_32_fim_antes_do_inicio_levanta_erro(usuario, sala_a):
    from reservas.services import criar_reserva

    with pytest.raises(ValidationError) as exc:
        criar_reserva(
            usuario=usuario, sala=sala_a, inicio=_em(11), fim=_em(10), titulo="Reunião"
        )

    assert exc.value.detail == {"fim": ["O fim deve ser depois do início."]}
    assert Reserva.objects.count() == 0


@pytest.mark.django_db
def test_sa_32_fim_igual_ao_inicio_levanta_erro(usuario, sala_a):
    from reservas.services import criar_reserva

    with pytest.raises(ValidationError) as exc:
        criar_reserva(
            usuario=usuario, sala=sala_a, inicio=_em(10), fim=_em(10), titulo="Reunião"
        )

    assert exc.value.detail == {"fim": ["O fim deve ser depois do início."]}
    assert Reserva.objects.count() == 0


@pytest.mark.django_db
def test_sa_32_fim_antes_vence_o_passado(usuario, sala_a):
    from reservas.services import criar_reserva

    with pytest.raises(ValidationError) as exc:
        criar_reserva(
            usuario=usuario, sala=sala_a, inicio=_em(8), fim=_em(7), titulo="Reunião"
        )

    assert exc.value.detail == {"fim": ["O fim deve ser depois do início."]}
    assert Reserva.objects.count() == 0


@pytest.mark.django_db
def test_sa_33_inicio_no_passado_levanta_erro(usuario, sala_a):
    from reservas.services import criar_reserva

    with pytest.raises(ValidationError) as exc:
        criar_reserva(
            usuario=usuario,
            sala=sala_a,
            inicio=_em(8, 59),
            fim=_em(10),
            titulo="Reunião",
        )

    assert exc.value.detail == {"inicio": ["Reserva não pode começar no passado."]}
    assert Reserva.objects.count() == 0


@pytest.mark.django_db
def test_sa_33_inicio_igual_ao_agora_grava(usuario, sala_a):
    from reservas.services import criar_reserva

    criar_reserva(
        usuario=usuario, sala=sala_a, inicio=_em(9), fim=_em(10), titulo="Reunião"
    )

    assert Reserva.objects.count() == 1


@pytest.mark.django_db
def test_sa_33_duracao_de_15_minutos_grava(usuario, sala_a):
    from reservas.services import criar_reserva

    criar_reserva(
        usuario=usuario, sala=sala_a, inicio=_em(10), fim=_em(10, 15), titulo="Reunião"
    )

    assert Reserva.objects.count() == 1


@pytest.mark.django_db
def test_sa_33_duracao_abaixo_de_15_minutos_levanta_erro(usuario, sala_a):
    from reservas.services import criar_reserva

    with pytest.raises(ValidationError) as exc:
        criar_reserva(
            usuario=usuario,
            sala=sala_a,
            inicio=_em(10),
            fim=_em(10, 14, 59),
            titulo="Reunião",
        )

    assert exc.value.detail == {"fim": ["A reserva deve durar pelo menos 15 minutos."]}
    assert Reserva.objects.count() == 0


@pytest.mark.django_db
def test_sa_33_duracao_de_8_horas_grava(usuario, sala_a):
    from reservas.services import criar_reserva

    criar_reserva(
        usuario=usuario, sala=sala_a, inicio=_em(10), fim=_em(18), titulo="Reunião"
    )

    assert Reserva.objects.count() == 1


@pytest.mark.django_db
def test_sa_33_duracao_acima_de_8_horas_levanta_erro(usuario, sala_a):
    from reservas.services import criar_reserva

    with pytest.raises(ValidationError) as exc:
        criar_reserva(
            usuario=usuario,
            sala=sala_a,
            inicio=_em(10),
            fim=_em(18, 0, 1),
            titulo="Reunião",
        )

    assert exc.value.detail == {"fim": ["A reserva pode durar no máximo 8 horas."]}
    assert Reserva.objects.count() == 0


@pytest.mark.django_db
def test_sa_30_sobreposicao_levanta_erro_de_validacao(usuario, sala_a):
    from reservas.services import criar_reserva

    criar_reserva(
        usuario=usuario, sala=sala_a, inicio=_em(10), fim=_em(11), titulo="Reunião"
    )

    with pytest.raises(ValidationError) as exc:
        criar_reserva(
            usuario=usuario,
            sala=sala_a,
            inicio=_em(10, 30),
            fim=_em(11, 30),
            titulo="Reunião",
        )

    assert exc.value.detail == {
        "non_field_errors": [
            "Já existe uma reserva confirmada nesta sala nesse horário."
        ]
    }
    assert Reserva.objects.count() == 1


@pytest.mark.django_db
def test_sa_30_outro_integrity_error_sobe(usuario, sala_a, monkeypatch):
    from reservas.services import criar_reserva

    def _falha(**kwargs):
        raise IntegrityError("outra constraint")

    monkeypatch.setattr(Reserva.objects, "create", _falha)

    with pytest.raises(IntegrityError, match="outra constraint"):
        criar_reserva(
            usuario=usuario, sala=sala_a, inicio=_em(10), fim=_em(11), titulo="Reunião"
        )
