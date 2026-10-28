from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

User = get_user_model()

MENSAGEM_EMAIL_DUPLICADO = "Já existe um usuário com este e-mail."


class RegistroSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        max_length=254,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                lookup="iexact",
                message=MENSAGEM_EMAIL_DUPLICADO,
            )
        ],
    )
    # Como no login (AuthTokenSerializer), não apara espaços; 128 é limite de entrada.
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, max_length=128
    )

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        # Instância NÃO salva: dá ao UserAttributeSimilarityValidator os
        # atributos (username, e-mail) com que comparar a senha.
        usuario = User(username=attrs["username"], email=attrs["email"])
        try:
            validate_password(attrs["password"], user=usuario)
        except DjangoValidationError as exc:
            mensagens = list(exc.messages)
            raise serializers.ValidationError({"password": mensagens}) from exc
        return attrs

    # Validador = mensagem amigável; índice = garantia: na corrida ganha e vira 400.
    def create(self, validated_data):
        try:
            with transaction.atomic():
                # create_user grava a senha com hash.
                return User.objects.create_user(**validated_data)
        except IntegrityError as exc:
            if User.objects.filter(email__iexact=validated_data["email"]).exists():
                raise serializers.ValidationError(
                    {"email": [MENSAGEM_EMAIL_DUPLICADO]}
                ) from exc
            raise
