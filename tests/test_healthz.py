import pytest


@pytest.mark.django_db
def test_sa_2_healthz_retorna_200_com_banco_de_pe(client):
    # O endpoint prova que a app está de pé e o banco está alcançável.
    resposta = client.get("/healthz/")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
