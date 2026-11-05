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


def _em(hora, minuto=0, dia=4):
    return datetime(2027, 1, dia, hora, minuto, tzinfo=UTC)


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
def sala_b():
    return Sala.objects.create(nome="Sala B", capacidade=6)


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
def test_sa_45_altera_so_o_titulo_de_reserva_ja_comecada_200(
    cliente_a, usuario_a, sala_a
):
    r = _reserva(usuario_a, sala_a, _em(8), _em(10))

    resp = cliente_a.patch(
        URL + f"{r.id}/",
        {"titulo": "Revisão"},
        format="json",
    )

    assert resp.status_code == 200
    assert resp.data["titulo"] == "Revisão"
    r.refresh_from_db()
    assert r.titulo == "Revisão"
    assert r.inicio == _em(8)


@pytest.mark.django_db
def test_sa_44_dono_altera_o_horario_200(cliente_a, usuario_a, sala_a):
    r = _reserva(usuario_a, sala_a, _em(10), _em(11))

    resp = cliente_a.patch(
        URL + f"{r.id}/",
        {"inicio": _em(14).isoformat(), "fim": _em(15).isoformat()},
        format="json",
    )

    assert resp.status_code == 200
    r.refresh_from_db()
    assert r.inicio == _em(14)
    assert r.fim == _em(15)


@pytest.mark.django_db
def test_sa_46_mover_por_cima_da_propria_faixa_200(cliente_a, usuario_a, sala_a):
    r = _reserva(usuario_a, sala_a, _em(10), _em(11))

    resp = cliente_a.patch(
        URL + f"{r.id}/",
        {"inicio": _em(10, 30).isoformat(), "fim": _em(11, 30).isoformat()},
        format="json",
    )

    assert resp.status_code == 200
    r.refresh_from_db()
    assert r.inicio == _em(10, 30)


@pytest.mark.django_db
def test_sa_45_horario_novo_no_passado_da_400(cliente_a, usuario_a, sala_a):
    r = _reserva(usuario_a, sala_a, _em(10), _em(11))

    resp = cliente_a.patch(
        URL + f"{r.id}/",
        {"inicio": _em(8).isoformat()},
        format="json",
    )

    assert resp.status_code == 400
    assert resp.data == {"inicio": ["Reserva não pode começar no passado."]}
    r.refresh_from_db()
    assert r.inicio == _em(10)


@pytest.mark.django_db
def test_sa_45_horario_novo_sobreposto_da_400(cliente_a, usuario_a, usuario_b, sala_a):
    r = _reserva(usuario_a, sala_a, _em(10), _em(11))
    _reserva(usuario_b, sala_a, _em(14), _em(15))

    resp = cliente_a.patch(
        URL + f"{r.id}/",
        {"inicio": _em(14, 30).isoformat(), "fim": _em(15, 30).isoformat()},
        format="json",
    )

    assert resp.status_code == 400
    assert resp.data == {
        "non_field_errors": [
            "Já existe uma reserva confirmada nesta sala nesse horário."
        ]
    }
    r.refresh_from_db()
    assert r.inicio == _em(10)


@pytest.mark.django_db
def test_l_7_reserva_cancelada_nao_pode_ser_alterada_400(cliente_a, usuario_a, sala_a):
    r = Reserva.objects.create(
        usuario=usuario_a,
        sala=sala_a,
        inicio=_em(10),
        fim=_em(11),
        titulo="Reunião",
        status=Reserva.Status.CANCELADA,
    )

    resp = cliente_a.patch(
        URL + f"{r.id}/",
        {"titulo": "Outro"},
        format="json",
    )

    assert resp.status_code == 400
    assert resp.data == {
        "non_field_errors": ["Reserva cancelada não pode ser alterada."]
    }
    r.refresh_from_db()
    assert r.titulo == "Reunião"


@pytest.mark.django_db
def test_sa_37_outro_usuario_nao_altera_404(cliente_a, cliente_b, usuario_b, sala_a):
    r = _reserva(usuario_b, sala_a, _em(10), _em(11))

    # Controle positivo: o dono altera a própria reserva.
    resp = cliente_b.patch(
        URL + f"{r.id}/",
        {"titulo": "Do dono"},
        format="json",
    )
    assert resp.status_code == 200

    resp = cliente_a.patch(
        URL + f"{r.id}/",
        {"titulo": "Intruso"},
        format="json",
    )
    assert resp.status_code == 404

    r.refresh_from_db()
    assert r.titulo == "Do dono"


@pytest.mark.django_db
def test_sa_38_admin_altera_reserva_de_outro_200(cliente_admin, usuario_b, sala_a):
    r = _reserva(usuario_b, sala_a, _em(10), _em(11))

    resp = cliente_admin.patch(
        URL + f"{r.id}/",
        {"titulo": "Pelo admin"},
        format="json",
    )

    assert resp.status_code == 200
    r.refresh_from_db()
    assert r.titulo == "Pelo admin"


@pytest.mark.django_db
def test_l_8_sala_do_corpo_e_ignorada(cliente_a, usuario_a, sala_a, sala_b):
    r = _reserva(usuario_a, sala_a, _em(10), _em(11))

    resp = cliente_a.patch(
        URL + f"{r.id}/",
        {"sala": sala_b.id, "titulo": "Mesmo lugar"},
        format="json",
    )

    assert resp.status_code == 200
    r.refresh_from_db()
    assert r.sala == sala_a
    assert r.titulo == "Mesmo lugar"


@pytest.mark.django_db
def test_sa_45_horario_novo_em_sala_que_ficou_inativa_da_400(
    cliente_a, usuario_a, sala_a
):
    r = _reserva(usuario_a, sala_a, _em(10), _em(11))
    sala_a.ativa = False
    sala_a.save()

    resp = cliente_a.patch(
        URL + f"{r.id}/",
        {"inicio": _em(14).isoformat(), "fim": _em(15).isoformat()},
        format="json",
    )

    assert resp.status_code == 400
    assert resp.data == {"sala": ["Sala inativa não aceita reservas."]}
    r.refresh_from_db()
    assert r.inicio == _em(10)
