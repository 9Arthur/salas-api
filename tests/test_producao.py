import re
from operator import ne

import pytest
from django.conf import settings
from django.core.checks import WARNING, run_checks
from django.core.management import call_command
from django.templatetags.static import static
from django.test import Client, override_settings

from config.settings import base, prod

# Chave só para o check deste teste (50+ caracteres, sem o prefixo
# django-insecure-); a de produção vem do fly secrets.
CHAVE_DE_TESTE = "chave-de-teste-do-check-deploy-sem-uso-em-producao-0123456789"
WHITENOISE = "whitenoise.middleware.WhiteNoiseMiddleware"
SEGURANCA = "django.middleware.security.SecurityMiddleware"


def _producao():
    # Os settings em que o prod.py difere dos settings em uso nos testes. Os
    # ALLOWED_HOSTS ficam de fora: vazios, o "testserver" do cliente daria 400.
    diferencas = {
        nome: getattr(prod, nome)
        for nome in dir(prod)
        if nome.isupper() and ne(getattr(prod, nome), getattr(settings, nome, None))
    }
    diferencas.pop("ALLOWED_HOSTS", None)
    return diferencas


def _avisos():
    mensagens = run_checks(include_deployment_checks=True)
    return sorted(m.id for m in mensagens if m.level >= WARNING)


def test_sa_51_prod_poe_o_whitenoise_logo_depois_da_seguranca_sem_mexer_na_base():
    assert WHITENOISE not in base.MIDDLEWARE
    assert prod.MIDDLEWARE == [SEGURANCA, WHITENOISE, *base.MIDDLEWARE[1:]]


def test_sa_52_check_deploy_sem_avisos_com_os_settings_de_producao():
    hosts = ["salas-api.fly.dev"]
    # Contraste: com os settings dos testes, o mesmo check acusa os avisos.
    with override_settings(SECRET_KEY=CHAVE_DE_TESTE, ALLOWED_HOSTS=hosts):
        avisos_sem_prod = _avisos()
    with override_settings(
        **{**_producao(), "SECRET_KEY": CHAVE_DE_TESTE, "ALLOWED_HOSTS": hosts}
    ):
        avisos_com_prod = _avisos()

    assert avisos_sem_prod == [
        "security.W004",
        "security.W008",
        "security.W012",
        "security.W016",
    ]
    assert avisos_com_prod == []


@pytest.mark.django_db
def test_sa_52_redireciona_para_https_menos_o_healthz(client, tmp_path):
    with override_settings(**{**_producao(), "STATIC_ROOT": tmp_path}):
        api_http = client.get("/api/salas/")
        api_via_proxy = client.get("/api/salas/", HTTP_X_FORWARDED_PROTO="https")
        saude_http = client.get("/healthz/")
        saude_https = client.get("/healthz/", secure=True)

    assert api_http.status_code == 301
    assert api_http["Location"] == "https://testserver/api/salas/"
    # Atrás do proxy o pedido já é HTTPS: sem redirect, cai na autenticação.
    assert api_via_proxy.status_code == 401
    assert saude_http.status_code == 200
    assert "Strict-Transport-Security" not in saude_http
    assert (
        saude_https["Strict-Transport-Security"]
        == "max-age=31536000; includeSubDomains; preload"
    )


@pytest.mark.django_db  # o close() da resposta dispara o request_finished, que mexe no banco
def test_sa_51_whitenoise_serve_o_estatico_com_hash_e_cache_longo(tmp_path):
    sem_whitenoise = _producao()
    sem_whitenoise.pop("MIDDLEWARE", None)
    with override_settings(**{**sem_whitenoise, "STATIC_ROOT": tmp_path}):
        call_command("collectstatic", "--noinput", verbosity=0)
        url = static("admin/css/base.css")
        resposta_sem = Client().get(url, secure=True)
    with override_settings(**{**_producao(), "STATIC_ROOT": tmp_path}):
        resposta_com = Client().get(url, secure=True)
        resposta_com.close()  # fecha o arquivo que o whitenoise abriu

    # O ManifestStaticFilesStorage põe 12 dígitos hexadecimais do md5 no nome.
    assert re.fullmatch(r"/static/admin/css/base\.[0-9a-f]{12}\.css", url)
    # Contraste: sem o middleware, ninguém serve o arquivo em produção.
    assert resposta_sem.status_code == 404
    assert resposta_com.status_code == 200
    assert resposta_com["Cache-Control"] == "max-age=315360000, public, immutable"
