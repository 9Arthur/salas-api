from datetime import UTC, datetime
from types import SimpleNamespace

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
def sala_inativa():
    return Sala.objects.create(nome="Sala Inativa", capacidade=4, ativa=False)


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
def test_sa_38_listar_reservas_sem_token_da_401(cliente_anonimo):
    resp = cliente_anonimo.get(URL)

    assert resp.status_code == 401


@pytest.mark.django_db
def test_sa_39_cria_reserva_valida_201_e_aparece_na_listagem_do_dono(
    cliente_a, usuario_a, sala_a
):
    resp = cliente_a.post(
        URL,
        {
            "sala": sala_a.id,
            "inicio": _em(10).isoformat(),
            "fim": _em(11).isoformat(),
            "titulo": "Reunião",
        },
        format="json",
    )

    assert resp.status_code == 201
    assert resp.data["sala"] == sala_a.id
    assert resp.data["usuario"] == usuario_a.id
    assert resp.data["status"] == "CONFIRMADA"
    assert resp.data["titulo"] == "Reunião"

    lista = cliente_a.get(URL)

    assert lista.status_code == 200
    assert [item["id"] for item in lista.data] == [resp.data["id"]]


@pytest.mark.django_db
def test_sa_39_usuario_do_corpo_e_ignorado(cliente_a, usuario_a, usuario_b, sala_a):
    resp = cliente_a.post(
        URL,
        {
            "sala": sala_a.id,
            "inicio": _em(10).isoformat(),
            "fim": _em(11).isoformat(),
            "titulo": "Reunião",
            "usuario": usuario_b.id,
        },
        format="json",
    )

    assert resp.status_code == 201
    assert Reserva.objects.get().usuario == usuario_a


@pytest.mark.django_db
def test_sa_39_titulo_vazio_da_400(cliente_a, sala_a):
    resp = cliente_a.post(
        URL,
        {
            "sala": sala_a.id,
            "inicio": _em(10).isoformat(),
            "fim": _em(11).isoformat(),
            "titulo": "",
        },
        format="json",
    )

    assert resp.status_code == 400
    assert "titulo" in resp.data
    assert Reserva.objects.count() == 0


@pytest.mark.django_db
def test_sa_31_inicio_no_passado_pela_api_da_400(cliente_a, sala_a):
    resp = cliente_a.post(
        URL,
        {
            "sala": sala_a.id,
            "inicio": _em(8).isoformat(),
            "fim": _em(10).isoformat(),
            "titulo": "Reunião",
        },
        format="json",
    )

    assert resp.status_code == 400
    assert resp.data == {"inicio": ["Reserva não pode começar no passado."]}


@pytest.mark.django_db
def test_sa_31_sobreposicao_total_pela_api_da_400(cliente_a, usuario_b, sala_a):
    _reserva(usuario_b, sala_a, _em(10), _em(11))

    resp = cliente_a.post(
        URL,
        {
            "sala": sala_a.id,
            "inicio": _em(10).isoformat(),
            "fim": _em(11).isoformat(),
            "titulo": "Reunião",
        },
        format="json",
    )

    assert resp.status_code == 400
    assert resp.data == {
        "non_field_errors": [
            "Já existe uma reserva confirmada nesta sala nesse horário."
        ]
    }


@pytest.mark.django_db
def test_l_5_sala_inativa_pela_api_da_400(cliente_a, sala_inativa):
    resp = cliente_a.post(
        URL,
        {
            "sala": sala_inativa.id,
            "inicio": _em(10).isoformat(),
            "fim": _em(11).isoformat(),
            "titulo": "Reunião",
        },
        format="json",
    )

    assert resp.status_code == 400
    assert resp.data == {"sala": ["Sala inativa não aceita reservas."]}


@pytest.mark.django_db
def test_sa_37_comum_so_ve_as_proprias(cliente_a, usuario_a, usuario_b, sala_a, sala_b):
    ra = _reserva(usuario_a, sala_a, _em(10), _em(11))
    _reserva(usuario_b, sala_b, _em(10), _em(11))

    resp = cliente_a.get(URL)

    assert resp.status_code == 200
    assert [item["id"] for item in resp.data] == [ra.id]


@pytest.mark.django_db
def test_sa_37_admin_ve_todas(cliente_admin, usuario_a, usuario_b, sala_a, sala_b):
    ra = _reserva(usuario_a, sala_a, _em(10), _em(11))
    rb = _reserva(usuario_b, sala_b, _em(10), _em(11))

    resp = cliente_admin.get(URL)

    assert resp.status_code == 200
    assert {item["id"] for item in resp.data} == {ra.id, rb.id}


@pytest.mark.django_db
def test_l_6_dono_ve_o_detalhe_200(cliente_a, usuario_a, sala_a):
    ra = _reserva(usuario_a, sala_a, _em(10), _em(11))

    resp = cliente_a.get(URL + f"{ra.id}/")

    assert resp.status_code == 200
    assert resp.data["id"] == ra.id


@pytest.mark.django_db
def test_l_6_sa_37_detalhe_de_reserva_de_outro_da_404(
    cliente_a, cliente_b, usuario_b, sala_a
):
    rb = _reserva(usuario_b, sala_a, _em(10), _em(11))

    # Controle positivo: a rota existe e o dono vê a própria reserva.
    resp = cliente_b.get(URL + f"{rb.id}/")
    assert resp.status_code == 200

    resp = cliente_a.get(URL + f"{rb.id}/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_l_6_admin_ve_o_detalhe_de_qualquer_uma_200(cliente_admin, usuario_b, sala_a):
    rb = _reserva(usuario_b, sala_a, _em(10), _em(11))

    resp = cliente_admin.get(URL + f"{rb.id}/")

    assert resp.status_code == 200


@pytest.mark.django_db
def test_sa_36_put_e_delete_dao_405(cliente_a, usuario_a, sala_a):
    ra = _reserva(usuario_a, sala_a, _em(10), _em(11))

    resp = cliente_a.put(
        URL + f"{ra.id}/",
        {
            "sala": sala_a.id,
            "inicio": _em(10).isoformat(),
            "fim": _em(11).isoformat(),
            "titulo": "Reunião",
        },
        format="json",
    )
    assert resp.status_code == 405

    resp = cliente_a.delete(URL + f"{ra.id}/")
    assert resp.status_code == 405

    assert Reserva.objects.count() == 1


@pytest.mark.django_db
def test_sa_40_filtro_por_sala(cliente_a, usuario_a, sala_a, sala_b):
    ra = _reserva(usuario_a, sala_a, _em(10), _em(11))
    _reserva(usuario_a, sala_b, _em(10), _em(11))

    resp = cliente_a.get(URL, {"sala": sala_a.id})

    assert resp.status_code == 200
    assert [item["id"] for item in resp.data] == [ra.id]


@pytest.mark.django_db
def test_sa_40_filtro_por_intervalo_de_datas(cliente_a, usuario_a, sala_a):
    _reserva(usuario_a, sala_a, _em(12, dia=4), _em(13, dia=4))
    r5 = _reserva(usuario_a, sala_a, _em(12, dia=5), _em(13, dia=5))
    r6 = _reserva(usuario_a, sala_a, _em(12, dia=6), _em(13, dia=6))

    resp = cliente_a.get(URL, {"de": "2027-01-05", "ate": "2027-01-05"})

    assert resp.status_code == 200
    assert [item["id"] for item in resp.data] == [r5.id]

    resp = cliente_a.get(URL, {"de": "2027-01-05"})

    assert resp.status_code == 200
    assert [item["id"] for item in resp.data] == [r5.id, r6.id]


@pytest.mark.django_db
def test_sa_40_data_invalida_da_400(cliente_a):
    resp = cliente_a.get(URL, {"de": "ontem"})

    assert resp.status_code == 400
    assert "de" in resp.data


@pytest.mark.django_db
def test_sa_41_listagem_em_ordem_de_inicio(cliente_a, usuario_a, sala_a):
    r14 = _reserva(usuario_a, sala_a, _em(14), _em(15))
    r10 = _reserva(usuario_a, sala_a, _em(10), _em(11))

    resp = cliente_a.get(URL)

    assert resp.status_code == 200
    assert [item["id"] for item in resp.data] == [r10.id, r14.id]


@pytest.mark.django_db
def test_sa_38_eh_dono_ou_admin_decide_pelo_objeto(usuario_a, usuario_b, admin, sala_a):
    from reservas.permissions import EhDonoOuAdmin

    r = _reserva(usuario_a, sala_a, _em(10), _em(11))
    p = EhDonoOuAdmin()

    assert p.has_object_permission(SimpleNamespace(user=usuario_a), None, r) is True
    assert p.has_object_permission(SimpleNamespace(user=usuario_b), None, r) is False
    assert p.has_object_permission(SimpleNamespace(user=admin), None, r) is True


@pytest.mark.django_db
def test_sa_42_apagar_sala_com_reserva_da_409(cliente_admin, usuario_a, sala_a):
    _reserva(usuario_a, sala_a, _em(10), _em(11))

    resp = cliente_admin.delete(f"/api/salas/{sala_a.id}/")

    assert resp.status_code == 409
    assert resp.data == {
        "detail": "Sala com reservas não pode ser apagada; desative-a."
    }
    assert Sala.objects.filter(pk=sala_a.pk).exists()
