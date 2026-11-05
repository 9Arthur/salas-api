from datetime import UTC, datetime

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from reservas.models import Reserva, Sala

AGORA = datetime(2027, 1, 4, 9, 0, tzinfo=UTC)
SENHA = "senha-forte-123"
MSG_PERMISSAO = "Só o dono da reserva ou um admin pode cancelá-la."
MSG_JA_CANCELADA = "Reserva já cancelada."
MSG_TERMINADA = "Reserva já terminada não pode ser cancelada."
MSG_ALTERAR_CANCELADA = "Reserva cancelada não pode ser alterada."


def _em(hora, minuto=0):
    return datetime(2027, 1, 4, hora, minuto, tzinfo=UTC)


def _reserva(usuario, sala, inicio, fim, status=Reserva.Status.CONFIRMADA):
    return Reserva.objects.create(
        usuario=usuario,
        sala=sala,
        inicio=inicio,
        fim=fim,
        titulo="Reunião",
        status=status,
    )


def _status_no_banco(reserva):
    return Reserva.objects.get(pk=reserva.pk).status


def _travou(contexto):
    return any("FOR UPDATE" in q["sql"] for q in contexto.captured_queries)


@pytest.fixture(autouse=True)
def agora_fixo(monkeypatch):
    monkeypatch.setattr(timezone, "now", lambda: AGORA)


@pytest.fixture
def usuario():
    return get_user_model().objects.create_user(
        username="ana", email="ana@exemplo.com", password=SENHA
    )


@pytest.fixture
def outro():
    return get_user_model().objects.create_user(
        username="bia", email="bia@exemplo.com", password=SENHA
    )


@pytest.fixture
def admin():
    return get_user_model().objects.create_user(
        username="chefe", email="chefe@exemplo.com", password=SENHA, is_staff=True
    )


@pytest.fixture
def sala_a():
    return Sala.objects.create(nome="Sala A", capacidade=10)


@pytest.mark.django_db
def test_l_9_dono_cancela_a_propria_reserva(usuario, sala_a):
    from reservas.services import cancelar_reserva

    r = _reserva(usuario, sala_a, _em(10), _em(11))

    resultado = cancelar_reserva(r, por=usuario)

    assert resultado.pk == r.pk
    assert resultado.status == Reserva.Status.CANCELADA
    assert _status_no_banco(r) == Reserva.Status.CANCELADA


@pytest.mark.django_db
def test_l_9_admin_cancela_reserva_de_outro(usuario, admin, sala_a):
    from reservas.services import cancelar_reserva

    r = _reserva(usuario, sala_a, _em(10), _em(11))

    resultado = cancelar_reserva(r, por=admin)

    assert resultado.status == Reserva.Status.CANCELADA
    assert _status_no_banco(r) == Reserva.Status.CANCELADA


@pytest.mark.django_db
def test_l_9_outro_usuario_nao_cancela(usuario, outro, sala_a):
    from reservas.services import cancelar_reserva

    r = _reserva(usuario, sala_a, _em(10), _em(11))

    with pytest.raises(PermissionDenied) as exc:
        cancelar_reserva(r, por=outro)

    assert exc.value.detail == MSG_PERMISSAO
    assert _status_no_banco(r) == Reserva.Status.CONFIRMADA

    # Controle positivo: a mesma reserva, pelo dono, cancela.
    cancelar_reserva(r, por=usuario)

    assert _status_no_banco(r) == Reserva.Status.CANCELADA


@pytest.mark.django_db
def test_l_9_permissao_vem_antes_do_status(usuario, outro, sala_a):
    from reservas.services import cancelar_reserva

    r = _reserva(usuario, sala_a, _em(10), _em(11), status=Reserva.Status.CANCELADA)

    with pytest.raises(PermissionDenied) as exc:
        cancelar_reserva(r, por=outro)

    assert exc.value.detail == MSG_PERMISSAO


@pytest.mark.django_db
def test_l_10_reserva_ja_cancelada_da_erro(usuario, sala_a):
    from reservas.services import cancelar_reserva

    r = _reserva(usuario, sala_a, _em(10), _em(11), status=Reserva.Status.CANCELADA)

    with pytest.raises(ValidationError) as exc:
        cancelar_reserva(r, por=usuario)

    assert exc.value.detail == {"non_field_errors": [MSG_JA_CANCELADA]}


@pytest.mark.django_db
def test_l_10_cancelada_e_terminada_responde_ja_cancelada(usuario, sala_a):
    from reservas.services import cancelar_reserva

    r = _reserva(usuario, sala_a, _em(7), _em(8), status=Reserva.Status.CANCELADA)

    with pytest.raises(ValidationError) as exc:
        cancelar_reserva(r, por=usuario)

    assert exc.value.detail == {"non_field_errors": [MSG_JA_CANCELADA]}


@pytest.mark.django_db
def test_l_11_reserva_terminada_da_erro(usuario, sala_a):
    from reservas.services import cancelar_reserva

    r = _reserva(usuario, sala_a, _em(7), _em(8))

    with pytest.raises(ValidationError) as exc:
        cancelar_reserva(r, por=usuario)

    assert exc.value.detail == {"non_field_errors": [MSG_TERMINADA]}
    assert _status_no_banco(r) == Reserva.Status.CONFIRMADA


@pytest.mark.django_db
def test_l_11_fim_igual_a_agora_conta_como_terminada(usuario, sala_a):
    from reservas.services import cancelar_reserva

    r = _reserva(usuario, sala_a, _em(8), _em(9))

    with pytest.raises(ValidationError) as exc:
        cancelar_reserva(r, por=usuario)

    assert exc.value.detail == {"non_field_errors": [MSG_TERMINADA]}
    assert _status_no_banco(r) == Reserva.Status.CONFIRMADA


@pytest.mark.django_db
def test_l_11_reserva_em_andamento_pode_ser_cancelada(usuario, sala_a):
    from reservas.services import cancelar_reserva

    r = _reserva(usuario, sala_a, _em(8, 30), _em(10))

    resultado = cancelar_reserva(r, por=usuario)

    assert resultado.status == Reserva.Status.CANCELADA
    assert _status_no_banco(r) == Reserva.Status.CANCELADA


@pytest.mark.django_db
def test_sa_49_alterar_com_instancia_velha_nao_descancela(usuario, sala_a):
    from reservas.services import alterar_reserva

    r = _reserva(usuario, sala_a, _em(10), _em(11))
    velha = Reserva.objects.get(pk=r.pk)
    # Cancelamento concorrente: chega ao banco depois da leitura da instância velha.
    Reserva.objects.filter(pk=r.pk).update(status=Reserva.Status.CANCELADA)

    with pytest.raises(ValidationError) as exc:
        alterar_reserva(velha, inicio=_em(10), fim=_em(11), titulo="Outro")

    assert exc.value.detail == {"non_field_errors": [MSG_ALTERAR_CANCELADA]}
    banco = Reserva.objects.get(pk=r.pk)
    assert banco.status == Reserva.Status.CANCELADA
    assert banco.titulo == "Reunião"

    # Controle positivo: sem o cancelamento, a instância velha altera.
    r2 = _reserva(usuario, sala_a, _em(12), _em(13))
    velha2 = Reserva.objects.get(pk=r2.pk)

    resultado = alterar_reserva(velha2, inicio=_em(12), fim=_em(13), titulo="Outro")

    assert resultado.titulo == "Outro"
    assert Reserva.objects.get(pk=r2.pk).titulo == "Outro"


@pytest.mark.django_db
def test_sa_49_cancelar_com_instancia_velha_nao_desfaz_alteracao(usuario, sala_a):
    from reservas.services import cancelar_reserva

    r = _reserva(usuario, sala_a, _em(10), _em(11))
    velha = Reserva.objects.get(pk=r.pk)
    # Alteração concorrente: chega ao banco depois da leitura da instância velha.
    Reserva.objects.filter(pk=r.pk).update(titulo="Novo")

    resultado = cancelar_reserva(velha, por=usuario)

    banco = Reserva.objects.get(pk=r.pk)
    assert banco.status == Reserva.Status.CANCELADA
    assert banco.titulo == "Novo"
    assert resultado.titulo == "Novo"


@pytest.mark.django_db
def test_sa_49_alterar_trava_a_linha(usuario, sala_a):
    from reservas.services import alterar_reserva

    r = _reserva(usuario, sala_a, _em(10), _em(11))

    # Controle do detector: uma leitura comum não tem FOR UPDATE.
    with CaptureQueriesContext(connection) as leitura:
        Reserva.objects.get(pk=r.pk)

    assert leitura.captured_queries
    assert not _travou(leitura)

    with CaptureQueriesContext(connection) as contexto:
        alterar_reserva(r, inicio=_em(10), fim=_em(11), titulo="Outro")

    assert _travou(contexto)


@pytest.mark.django_db
def test_sa_49_cancelar_trava_a_linha(usuario, sala_a):
    from reservas.services import cancelar_reserva

    r = _reserva(usuario, sala_a, _em(10), _em(11))

    with CaptureQueriesContext(connection) as leitura:
        Reserva.objects.get(pk=r.pk)

    assert leitura.captured_queries
    assert not _travou(leitura)

    with CaptureQueriesContext(connection) as contexto:
        cancelar_reserva(r, por=usuario)

    assert _travou(contexto)
