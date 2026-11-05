from datetime import UTC, datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from reservas.models import Reserva, Sala

SENHA = "senha-forte-123"
URL = "/api/reservas/"
AGORA = datetime(2027, 1, 4, 9, 0, tzinfo=UTC)


def _em(hora, minuto=0):
    return datetime(2027, 1, 4, hora, minuto, tzinfo=UTC)


def _url_cancelar(reserva):
    return f"{URL}{reserva.id}/cancelar/"


def _cliente_com_token(usuario):
    cliente = APIClient()
    token = Token.objects.create(user=usuario)
    cliente.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return cliente


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


@pytest.fixture(autouse=True)
def agora_fixo(monkeypatch):
    monkeypatch.setattr(timezone, "now", lambda: AGORA)


@pytest.fixture
def usuario_a():
    return get_user_model().objects.create_user(
        username="ana", email="ana@exemplo.com", password=SENHA
    )


@pytest.fixture
def usuario_b():
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


@pytest.fixture
def cliente_anonimo():
    return APIClient()


@pytest.fixture
def cliente_a(usuario_a):
    return _cliente_com_token(usuario_a)


@pytest.fixture
def cliente_b(usuario_b):
    return _cliente_com_token(usuario_b)


@pytest.fixture
def cliente_admin(admin):
    return _cliente_com_token(admin)


@pytest.mark.django_db
def test_l_12_dono_cancela_pela_api_200(cliente_a, usuario_a, sala_a):
    r = _reserva(usuario_a, sala_a, _em(10), _em(11))

    resp = cliente_a.post(_url_cancelar(r), format="json")

    assert resp.status_code == 200
    assert resp.data["id"] == r.id
    assert resp.data["status"] == "CANCELADA"
    assert _status_no_banco(r) == Reserva.Status.CANCELADA


@pytest.mark.django_db
def test_l_9_admin_cancela_qualquer_uma_pela_api_200(cliente_admin, usuario_a, sala_a):
    r = _reserva(usuario_a, sala_a, _em(10), _em(11))

    resp = cliente_admin.post(_url_cancelar(r), format="json")

    assert resp.status_code == 200
    assert resp.data["status"] == "CANCELADA"
    assert _status_no_banco(r) == Reserva.Status.CANCELADA


@pytest.mark.django_db
def test_sa_37_outro_usuario_nao_cancela_404(cliente_a, cliente_b, usuario_a, sala_a):
    r = _reserva(usuario_a, sala_a, _em(10), _em(11))

    resp = cliente_b.post(_url_cancelar(r), format="json")

    assert resp.status_code == 404
    assert _status_no_banco(r) == Reserva.Status.CONFIRMADA

    # Controle positivo: a mesma rota, pelo dono, cancela.
    resp_dono = cliente_a.post(_url_cancelar(r), format="json")

    assert resp_dono.status_code == 200
    assert _status_no_banco(r) == Reserva.Status.CANCELADA


@pytest.mark.django_db
def test_l_10_ja_cancelada_pela_api_400(cliente_a, usuario_a, sala_a):
    r = _reserva(usuario_a, sala_a, _em(10), _em(11), status=Reserva.Status.CANCELADA)

    resp = cliente_a.post(_url_cancelar(r), format="json")

    assert resp.status_code == 400
    assert resp.data == {"non_field_errors": ["Reserva já cancelada."]}


@pytest.mark.django_db
def test_l_11_terminada_pela_api_400(cliente_a, usuario_a, sala_a):
    r = _reserva(usuario_a, sala_a, _em(7), _em(8))

    resp = cliente_a.post(_url_cancelar(r), format="json")

    assert resp.status_code == 400
    assert resp.data == {
        "non_field_errors": ["Reserva já terminada não pode ser cancelada."]
    }
    assert _status_no_banco(r) == Reserva.Status.CONFIRMADA


@pytest.mark.django_db
def test_l_12_cancelada_libera_a_faixa_201(cliente_a, usuario_a, sala_a):
    r = _reserva(usuario_a, sala_a, _em(10), _em(11))
    corpo = {
        "sala": sala_a.id,
        "inicio": _em(10).isoformat(),
        "fim": _em(11).isoformat(),
        "titulo": "Nova",
    }

    # Controle: antes do cancelamento, a mesma faixa é recusada.
    antes = cliente_a.post(URL, corpo, format="json")

    assert antes.status_code == 400

    resp = cliente_a.post(_url_cancelar(r), format="json")

    assert resp.status_code == 200

    depois = cliente_a.post(URL, corpo, format="json")

    assert depois.status_code == 201
    assert depois.data["status"] == "CONFIRMADA"


@pytest.mark.django_db
def test_l_12_cancelar_sem_token_401(cliente_anonimo, usuario_a, sala_a):
    r = _reserva(usuario_a, sala_a, _em(10), _em(11))

    resp = cliente_anonimo.post(_url_cancelar(r), format="json")

    assert resp.status_code == 401
    assert _status_no_banco(r) == Reserva.Status.CONFIRMADA


@pytest.mark.django_db
def test_l_12_get_em_cancelar_405(cliente_a, usuario_a, sala_a):
    r = _reserva(usuario_a, sala_a, _em(10), _em(11))

    resp = cliente_a.get(_url_cancelar(r))

    assert resp.status_code == 405
    assert _status_no_banco(r) == Reserva.Status.CONFIRMADA

    # Controle positivo: na mesma rota, o POST cancela.
    resp_post = cliente_a.post(_url_cancelar(r), format="json")

    assert resp_post.status_code == 200
