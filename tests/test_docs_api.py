import json

import pytest
from rest_framework.test import APIClient

SCHEMA = "/api/schema/"
DOCS = "/api/docs/"
LISTA_RESERVAS = "/api/reservas/"
CANCELAR = "/api/reservas/{id}/cancelar/"


def _schema_json(cliente):
    resp = cliente.get(SCHEMA, {"format": "json"})
    assert resp.status_code == 200
    return json.loads(resp.content)


@pytest.fixture
def cliente_anonimo():
    return APIClient()


@pytest.mark.django_db
def test_sa_47_schema_e_publico(cliente_anonimo):
    resp = cliente_anonimo.get(SCHEMA)

    assert resp.status_code == 200
    assert resp.content.startswith(b"openapi:")


@pytest.mark.django_db
def test_sa_47_swagger_e_publico_e_aponta_para_o_schema(cliente_anonimo):
    resp = cliente_anonimo.get(DOCS)

    assert resp.status_code == 200
    assert b"swagger-ui" in resp.content
    assert SCHEMA.encode() in resp.content


@pytest.mark.django_db
def test_sa_47_schema_documenta_o_cancelar_sem_corpo(cliente_anonimo):
    schema = _schema_json(cliente_anonimo)

    operacao = schema["paths"][CANCELAR]["post"]

    assert "requestBody" not in operacao
    assert "200" in operacao["responses"]


@pytest.mark.django_db
def test_sa_47_schema_documenta_os_filtros_da_listagem(cliente_anonimo):
    schema = _schema_json(cliente_anonimo)

    parametros = schema["paths"][LISTA_RESERVAS]["get"].get("parameters", [])

    assert {"sala", "de", "ate"} <= {p["name"] for p in parametros}


@pytest.mark.django_db
def test_sa_47_schema_declara_o_token(cliente_anonimo):
    schema = _schema_json(cliente_anonimo)

    assert "tokenAuth" in schema["components"]["securitySchemes"]


@pytest.mark.django_db
def test_sa_47_schema_gerado_sem_avisos(cliente_anonimo):
    from drf_spectacular.drainage import GENERATOR_STATS

    GENERATOR_STATS.reset()

    _schema_json(cliente_anonimo)

    assert not GENERATOR_STATS, list(GENERATOR_STATS._warn_cache)
