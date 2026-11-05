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
def cliente_a(usuario_a):
    return _cliente_com_token(usuario_a)


@pytest.mark.django_db
def test_sa_49_campos_omitidos_vem_da_linha_relida(usuario_a, sala_a):
    from reservas.services import alterar_reserva

    r = _reserva(usuario_a, sala_a, _em(10), _em(11))
    velha = Reserva.objects.get(pk=r.pk)
    # Alteração concorrente de horário: chega ao banco depois da leitura da velha.
    Reserva.objects.filter(pk=r.pk).update(inicio=_em(12), fim=_em(13))

    resultado = alterar_reserva(velha, titulo="Outro")

    banco = Reserva.objects.get(pk=r.pk)
    assert (banco.inicio, banco.fim, banco.titulo) == (_em(12), _em(13), "Outro")
    assert (resultado.inicio, resultado.fim) == (_em(12), _em(13))


@pytest.mark.django_db
def test_sa_49_patch_so_de_titulo_nao_desfaz_horario_concorrente(
    cliente_a, usuario_a, sala_a, monkeypatch
):
    from reservas import views

    r = _reserva(usuario_a, sala_a, _em(10), _em(11))
    servico = views.alterar_reserva

    def _com_patch_concorrente(reserva, **campos):
        # Outro PATCH grava um horário novo depois do get_object desta requisição.
        Reserva.objects.filter(pk=reserva.pk).update(inicio=_em(12), fim=_em(13))
        return servico(reserva, **campos)

    monkeypatch.setattr(views, "alterar_reserva", _com_patch_concorrente)

    resp = cliente_a.patch(f"{URL}{r.id}/", {"titulo": "Outro"}, format="json")

    assert resp.status_code == 200
    banco = Reserva.objects.get(pk=r.pk)
    assert (banco.inicio, banco.fim, banco.titulo) == (_em(12), _em(13), "Outro")
