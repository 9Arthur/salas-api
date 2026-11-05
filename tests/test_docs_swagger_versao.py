import pytest
from rest_framework.test import APIClient

DOCS = "/api/docs/"
VERSAO_SWAGGER_UI = b"swagger-ui-dist@5.34.0/"


@pytest.fixture
def cliente_anonimo():
    return APIClient()


@pytest.mark.django_db
def test_sa_47_swagger_ui_em_versao_fixa(cliente_anonimo):
    resp = cliente_anonimo.get(DOCS)

    assert resp.status_code == 200
    assert VERSAO_SWAGGER_UI in resp.content
    assert b"@latest" not in resp.content
