import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

URL_REGISTRO = "/api/auth/registro/"
URL_TOKEN = "/api/auth/token/"
USERNAME = "ana"
EMAIL = "ana@exemplo.com"
SENHA = "Senha-Forte-123"
MENSAGEM_LOGIN_INVALIDO = "Usuário ou senha inválidos."


def test_sa_9_modelo_de_usuario_e_customizado():
    assert get_user_model()._meta.label == "users.User"


@pytest.mark.django_db
def test_sa_9_email_duplicado_barrado_no_banco():
    get_user_model().objects.create_user(username=USERNAME, email=EMAIL, password=SENHA)

    # O atomic isola o erro num savepoint e preserva a transação do teste.
    with pytest.raises(IntegrityError), transaction.atomic():
        get_user_model().objects.create_user(
            username="bia", email=EMAIL, password=SENHA
        )


@pytest.mark.django_db
def test_sa_10_registro_cria_usuario_e_devolve_201(client):
    resposta = client.post(
        URL_REGISTRO,
        {"username": USERNAME, "email": EMAIL, "password": SENHA},
        content_type="application/json",
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert set(corpo) == {"id", "username", "email"}
    assert corpo["username"] == USERNAME
    assert corpo["email"] == EMAIL
    usuario = get_user_model().objects.get(username=USERNAME)
    assert corpo["id"] == usuario.id
    assert usuario.check_password(SENHA) is True


@pytest.mark.django_db
def test_sa_10_registro_com_email_duplicado_devolve_400(client):
    # O username é diferente de propósito: isola a causa da rejeição no e-mail.
    get_user_model().objects.create_user(username="bia", email=EMAIL, password=SENHA)
    resposta = client.post(
        URL_REGISTRO,
        {"username": USERNAME, "email": EMAIL, "password": SENHA},
        content_type="application/json",
    )

    assert resposta.status_code == 400
    assert resposta.json() == {"email": ["Já existe um usuário com este e-mail."]}
    assert get_user_model().objects.count() == 1


@pytest.mark.django_db
def test_sa_10_registro_com_senha_fraca_devolve_400(client):
    resposta = client.post(
        URL_REGISTRO,
        {"username": USERNAME, "email": EMAIL, "password": "12345678"},
        content_type="application/json",
    )

    assert resposta.status_code == 400
    # O texto da mensagem é dos validadores do Django; só a chave é fixada.
    assert "password" in resposta.json()
    assert get_user_model().objects.count() == 0


@pytest.mark.django_db
def test_sa_11_login_correto_devolve_token(client):
    usuario = get_user_model().objects.create_user(
        username=USERNAME, email=EMAIL, password=SENHA
    )
    resposta = client.post(
        URL_TOKEN,
        {"username": USERNAME, "password": SENHA},
        content_type="application/json",
    )

    assert resposta.status_code == 200
    # Import local: sem o app authtoken instalado, no topo ele derrubaria a coleta.
    from rest_framework.authtoken.models import Token

    assert resposta.json() == {"token": Token.objects.get(user=usuario).key}


@pytest.mark.django_db
def test_sa_11_login_com_senha_errada_devolve_401(client):
    get_user_model().objects.create_user(username=USERNAME, email=EMAIL, password=SENHA)
    resposta = client.post(
        URL_TOKEN,
        {"username": USERNAME, "password": "Senha-Errada-999"},
        content_type="application/json",
    )

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": MENSAGEM_LOGIN_INVALIDO}
    assert resposta["WWW-Authenticate"] == "Token"
    from rest_framework.authtoken.models import Token

    assert Token.objects.count() == 0


@pytest.mark.django_db
def test_sa_11_login_com_usuario_inexistente_devolve_401(client):
    # Mesma mensagem da senha errada: a resposta não revela quais usuários existem.
    get_user_model().objects.create_user(username=USERNAME, email=EMAIL, password=SENHA)
    resposta = client.post(
        URL_TOKEN,
        {"username": "zeca", "password": SENHA},
        content_type="application/json",
    )

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": MENSAGEM_LOGIN_INVALIDO}
    assert resposta["WWW-Authenticate"] == "Token"


@pytest.mark.django_db
def test_sa_11_login_sem_senha_devolve_400(client):
    # Campo ausente é erro de requisição (400), não de credencial (401).
    get_user_model().objects.create_user(username=USERNAME, email=EMAIL, password=SENHA)
    resposta = client.post(
        URL_TOKEN,
        {"username": USERNAME},
        content_type="application/json",
    )

    assert resposta.status_code == 400
    assert "password" in resposta.json()


@pytest.mark.django_db
def test_sa_14_registro_com_email_em_outra_caixa_devolve_400(client):
    # E-mail não diferencia maiúsculas.
    get_user_model().objects.create_user(username=USERNAME, email=EMAIL, password=SENHA)
    resposta = client.post(
        URL_REGISTRO,
        {"username": "bia", "email": "Ana@Exemplo.com", "password": SENHA},
        content_type="application/json",
    )

    assert resposta.status_code == 400
    assert resposta.json() == {"email": ["Já existe um usuário com este e-mail."]}
    assert get_user_model().objects.count() == 1


@pytest.mark.django_db
def test_sa_14_registro_em_corrida_devolve_400_e_nao_500():
    from rest_framework.exceptions import ValidationError

    from users.serializers import RegistroSerializer

    serializer = RegistroSerializer(
        data={"username": USERNAME, "email": EMAIL, "password": SENHA}
    )
    assert serializer.is_valid(), serializer.errors
    # Simula a outra requisição gravando entre a validação e o save.
    get_user_model().objects.create_user(username="bia", email=EMAIL, password=SENHA)

    with pytest.raises(ValidationError) as erro:
        serializer.save()

    assert erro.value.detail == {"email": ["Já existe um usuário com este e-mail."]}
    assert get_user_model().objects.count() == 1


@pytest.mark.django_db
def test_sa_14_registro_com_email_acima_de_254_caracteres_devolve_400(client):
    email_longo = "a" * 243 + "@exemplo.com"
    assert len(email_longo) == 255
    resposta = client.post(
        URL_REGISTRO,
        {"username": USERNAME, "email": email_longo, "password": SENHA},
        content_type="application/json",
    )

    assert resposta.status_code == 400
    assert "email" in resposta.json()
    assert get_user_model().objects.count() == 0


@pytest.mark.django_db
def test_sa_15_senha_com_espacos_nas_bordas_e_preservada(client):
    # O registro e o login têm de tratar a senha igual.
    senha_com_espacos = "  Senha-Forte-123  "
    resposta = client.post(
        URL_REGISTRO,
        {"username": USERNAME, "email": EMAIL, "password": senha_com_espacos},
        content_type="application/json",
    )
    assert resposta.status_code == 201

    resposta = client.post(
        URL_TOKEN,
        {"username": USERNAME, "password": senha_com_espacos},
        content_type="application/json",
    )
    assert resposta.status_code == 200


@pytest.mark.django_db
def test_sa_11_login_com_corpo_que_nao_e_objeto_devolve_400(client):
    # Corpo malformado é erro de requisição, não de credencial.
    resposta = client.post(URL_TOKEN, [], content_type="application/json")

    assert resposta.status_code == 400
    assert "non_field_errors" in resposta.json()


@pytest.mark.django_db
def test_sa_9_registro_sem_email_devolve_400(client):
    resposta = client.post(
        URL_REGISTRO,
        {"username": USERNAME, "password": SENHA},
        content_type="application/json",
    )

    assert resposta.status_code == 400
    assert "email" in resposta.json()
    assert get_user_model().objects.count() == 0


@pytest.mark.django_db
def test_sa_10_registro_com_senha_igual_ao_email_devolve_400(client):
    # Prova que o validador de similaridade recebe o usuário.
    resposta = client.post(
        URL_REGISTRO,
        {"username": USERNAME, "email": EMAIL, "password": EMAIL},
        content_type="application/json",
    )

    assert resposta.status_code == 400
    assert "password" in resposta.json()
    assert get_user_model().objects.count() == 0
