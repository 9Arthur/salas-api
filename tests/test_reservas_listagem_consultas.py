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
# Uma consulta do token (TokenAuthentication) e uma das reservas, com a sala e o
# usuário vindos no mesmo SELECT pelo select_related.
CONSULTAS_DA_LISTAGEM = 2


def _em(hora, minuto=0):
    return datetime(2027, 1, 4, hora, minuto, tzinfo=UTC)


def _cliente_com_token(usuario):
    cliente = APIClient()
    token = Token.objects.create(user=usuario)
    cliente.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return cliente


def _reserva(usuario, sala, inicio, fim):
    return Reserva.objects.create(
        usuario=usuario, sala=sala, inicio=inicio, fim=fim, titulo="Reunião"
    )


@pytest.fixture(autouse=True)
def agora_fixo(monkeypatch):
    monkeypatch.setattr(timezone, "now", lambda: AGORA)


@pytest.fixture
def usuario_a():
    return get_user_model().objects.create_user(
        username="ana", email="ana@exemplo.com", password=SENHA
    )


@pytest.fixture
def sala_a():
    return Sala.objects.create(nome="Sala A", capacidade=10)


@pytest.fixture
def sala_b():
    return Sala.objects.create(nome="Sala B", capacidade=6)


@pytest.fixture
def cliente_a(usuario_a):
    return _cliente_com_token(usuario_a)


@pytest.mark.django_db
def test_sa_48_listagem_mostra_nome_da_sala_e_username(cliente_a, usuario_a, sala_a):
    _reserva(usuario_a, sala_a, _em(10), _em(11))

    resp = cliente_a.get(URL)

    assert resp.status_code == 200
    assert resp.data[0]["sala_nome"] == "Sala A"
    assert resp.data[0]["usuario_username"] == "ana"
    assert resp.data[0]["sala"] == sala_a.id
    assert resp.data[0]["usuario"] == usuario_a.id


@pytest.mark.django_db
def test_sa_48_listagem_sem_n_mais_1(
    cliente_a, usuario_a, sala_a, sala_b, django_assert_num_queries
):
    _reserva(usuario_a, sala_a, _em(10), _em(11))

    with django_assert_num_queries(CONSULTAS_DA_LISTAGEM):
        com_uma = cliente_a.get(URL)

    assert [item["sala_nome"] for item in com_uma.data] == ["Sala A"]

    _reserva(usuario_a, sala_b, _em(12), _em(13))
    _reserva(usuario_a, sala_a, _em(14), _em(15))

    # Mesma contagem com 3 reservas: o número de consultas não cresce com a lista.
    with django_assert_num_queries(CONSULTAS_DA_LISTAGEM):
        com_tres = cliente_a.get(URL)

    assert [item["sala_nome"] for item in com_tres.data] == [
        "Sala A",
        "Sala B",
        "Sala A",
    ]
    assert [item["usuario_username"] for item in com_tres.data] == ["ana"] * 3
