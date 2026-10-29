import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

SENHA = "Senha-de-teste-123"


def _cliente_com_token(usuario):
    cliente = APIClient()
    token = Token.objects.create(user=usuario)
    cliente.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return cliente


@pytest.fixture
def cliente_anonimo():
    return APIClient()


@pytest.fixture
def cliente_comum():
    usuario = get_user_model().objects.create_user(
        username="comum", email="comum@exemplo.com", password=SENHA
    )
    return _cliente_com_token(usuario)


@pytest.fixture
def cliente_admin():
    usuario = get_user_model().objects.create_user(
        username="admin", email="admin@exemplo.com", password=SENHA, is_staff=True
    )
    return _cliente_com_token(usuario)


def _cria_sala(cliente_admin, nome, capacidade, ativa=True):
    resp = cliente_admin.post(
        "/api/salas/",
        {"nome": nome, "capacidade": capacidade, "ativa": ativa},
        format="json",
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.django_db
def test_l_1_listar_sem_token_da_401(cliente_anonimo):
    resp = cliente_anonimo.get("/api/salas/")

    assert resp.status_code == 401
    assert resp["WWW-Authenticate"] == "Token"


@pytest.mark.django_db
def test_sa_17_comum_nao_cria_sala_403(cliente_comum):
    resp = cliente_comum.post(
        "/api/salas/", {"nome": "Sala Azul", "capacidade": 8}, format="json"
    )

    assert resp.status_code == 403
    # Import local: sem o app reservas, no topo ele derrubaria a coleta.
    from reservas.models import Sala

    assert Sala.objects.count() == 0


@pytest.mark.django_db
def test_sa_17_admin_cria_sala_201(cliente_admin):
    resp = cliente_admin.post(
        "/api/salas/", {"nome": "Sala Azul", "capacidade": 8}, format="json"
    )

    assert resp.status_code == 201
    corpo = resp.json()
    assert set(corpo) == {"id", "nome", "capacidade", "ativa", "criada_em"}
    assert corpo["nome"] == "Sala Azul"
    assert corpo["capacidade"] == 8
    assert corpo["ativa"] is True


@pytest.mark.django_db
def test_sa_17_put_da_405(cliente_admin):
    sala_id = _cria_sala(cliente_admin, "Sala Azul", 8)

    resp = cliente_admin.put(
        f"/api/salas/{sala_id}/",
        {"nome": "Sala Azul", "capacidade": 8, "ativa": True},
        format="json",
    )

    assert resp.status_code == 405


@pytest.mark.django_db
def test_sa_17_admin_altera_sala_200(cliente_admin):
    sala_id = _cria_sala(cliente_admin, "Sala Azul", 8)

    resp = cliente_admin.patch(
        f"/api/salas/{sala_id}/", {"capacidade": 12}, format="json"
    )

    assert resp.status_code == 200
    assert resp.json()["capacidade"] == 12


@pytest.mark.django_db
def test_sa_17_comum_nao_altera_nem_apaga_403(cliente_admin, cliente_comum):
    sala_id = _cria_sala(cliente_admin, "Sala Azul", 8)

    resp = cliente_comum.patch(
        f"/api/salas/{sala_id}/", {"capacidade": 12}, format="json"
    )
    assert resp.status_code == 403

    resp = cliente_comum.delete(f"/api/salas/{sala_id}/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_sa_19_admin_apaga_sala_204(cliente_admin):
    sala_id = _cria_sala(cliente_admin, "Sala Azul", 8)

    resp = cliente_admin.delete(f"/api/salas/{sala_id}/")
    assert resp.status_code == 204

    resp = cliente_admin.get(f"/api/salas/{sala_id}/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_l_4_comum_nao_ve_sala_inativa_na_listagem(cliente_admin, cliente_comum):
    _cria_sala(cliente_admin, "Sala Azul", 8)
    _cria_sala(cliente_admin, "Sala Verde", 4, ativa=False)

    resp = cliente_comum.get("/api/salas/")

    assert resp.status_code == 200
    assert [s["nome"] for s in resp.json()] == ["Sala Azul"]


@pytest.mark.django_db
def test_l_4_sa_22_admin_ve_todas_em_ordem_de_nome(cliente_admin):
    # A Verde entra primeiro: a ordem da resposta não pode ser a de criação.
    _cria_sala(cliente_admin, "Sala Verde", 4, ativa=False)
    _cria_sala(cliente_admin, "Sala Azul", 8)

    resp = cliente_admin.get("/api/salas/")

    assert resp.status_code == 200
    assert [s["nome"] for s in resp.json()] == ["Sala Azul", "Sala Verde"]


@pytest.mark.django_db
def test_l_3_comum_detalhe_de_sala_inativa_da_404(cliente_admin, cliente_comum):
    azul_id = _cria_sala(cliente_admin, "Sala Azul", 8)
    verde_id = _cria_sala(cliente_admin, "Sala Verde", 4, ativa=False)

    resp = cliente_comum.get(f"/api/salas/{verde_id}/")
    assert resp.status_code == 404

    # Controle positivo: o 404 vem da sala inativa, não da rota.
    resp = cliente_comum.get(f"/api/salas/{azul_id}/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_sa_20_capacidade_zero_da_400(cliente_admin):
    resp = cliente_admin.post(
        "/api/salas/", {"nome": "Sala Zero", "capacidade": 0}, format="json"
    )
    assert resp.status_code == 400
    assert resp.json() == {"capacidade": ["A capacidade deve ser no mínimo 1."]}

    # Controle positivo: o limite é 1, não acima.
    resp = cliente_admin.post(
        "/api/salas/", {"nome": "Sala Um", "capacidade": 1}, format="json"
    )
    assert resp.status_code == 201


@pytest.mark.django_db
def test_sa_20_constraint_barra_capacidade_zero_no_banco():
    from reservas.models import Sala

    # Controle positivo: capacidade 1 passa pela constraint.
    Sala.objects.create(nome="Sala Um", capacidade=1)

    # O atomic isola o erro num savepoint e preserva a transação do teste.
    with pytest.raises(IntegrityError) as excinfo, transaction.atomic():
        Sala.objects.create(nome="Sala Zero", capacidade=0)

    assert "sala_capacidade_minima" in str(excinfo.value)
    assert Sala.objects.count() == 1


@pytest.mark.django_db
def test_sa_21_nome_em_outra_caixa_da_400(cliente_admin):
    _cria_sala(cliente_admin, "Sala Azul", 8)

    resp = cliente_admin.post(
        "/api/salas/", {"nome": "sala azul", "capacidade": 8}, format="json"
    )

    assert resp.status_code == 400
    assert resp.json() == {"nome": ["Já existe uma sala com este nome."]}


@pytest.mark.django_db
def test_sa_21_constraint_barra_nome_em_outra_caixa_no_banco():
    from reservas.models import Sala

    Sala.objects.create(nome="Sala Azul", capacidade=8)

    with pytest.raises(IntegrityError) as excinfo, transaction.atomic():
        Sala.objects.create(nome="SALA AZUL", capacidade=8)

    assert "sala_nome_unico_ci" in str(excinfo.value)
