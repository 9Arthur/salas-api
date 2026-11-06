from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from reservas.models import Sala

SALAS_DEMO = [("Auditório", 40, True), ("Sala Azul", 6, True), ("Sala Verde", 10, True)]


def _seed():
    saida = StringIO()
    call_command("seed_demo", stdout=saida)
    return saida.getvalue()


def _salas():
    return list(
        Sala.objects.order_by("nome").values_list("nome", "capacidade", "ativa")
    )


@pytest.mark.django_db
def test_sa_55_seed_demo_cria_as_salas_e_o_usuario_demo():
    saida = _seed()

    demo = get_user_model().objects.get(username="demo")
    assert saida == "seed_demo: 3 salas (3 criadas) e o usuário demo (criado).\n"
    assert _salas() == SALAS_DEMO
    assert demo.email == "demo@exemplo.com"
    assert demo.check_password("demo1234")
    assert (demo.is_staff, demo.is_superuser, demo.is_active) == (False, False, True)


@pytest.mark.django_db
def test_sa_55_seed_demo_rodado_de_novo_nao_duplica():
    _seed()
    saida = _seed()

    assert saida == "seed_demo: 3 salas (0 criadas) e o usuário demo (atualizado).\n"
    assert _salas() == SALAS_DEMO
    assert get_user_model().objects.filter(username="demo").count() == 1


@pytest.mark.django_db
def test_sa_55_seed_demo_rebaixa_e_recoloca_a_senha_de_um_demo_alterado():
    # Contraste: o demo existe como admin, com outra senha e com uma sala inativa.
    get_user_model().objects.create_user(
        username="demo",
        email="demo@exemplo.com",
        password="outra-senha-qualquer",
        is_staff=True,
        is_superuser=True,
    )
    Sala.objects.create(nome="Sala Azul", capacidade=2, ativa=False)

    _seed()

    demo = get_user_model().objects.get(username="demo")
    assert (demo.is_staff, demo.is_superuser) == (False, False)
    assert demo.check_password("demo1234")
    assert _salas() == SALAS_DEMO


@pytest.mark.django_db
def test_sa_55_demo_do_seed_faz_login_pela_api(client):
    _seed()

    resposta = client.post(
        "/api/auth/token/",
        {"username": "demo", "password": "demo1234"},
        content_type="application/json",
    )

    assert resposta.status_code == 200
    assert set(resposta.json()) == {"token"}
