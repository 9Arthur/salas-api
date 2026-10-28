from rest_framework import generics
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from users.serializers import RegistroSerializer


class RegistroView(generics.CreateAPIView):
    serializer_class = RegistroSerializer
    permission_classes = [AllowAny]


class LoginView(ObtainAuthToken):
    permission_classes = [AllowAny]
    # Sem authentication_classes próprio: herda TokenAuthentication do settings.
    # É essa classe que monta o cabeçalho WWW-Authenticate; sem ele o DRF
    # rebaixa o AuthenticationFailed de 401 para 403.

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            # Só credencial inválida vira 401: é o código "authorization" em
            # non_field_errors. Qualquer outro erro (corpo que não é objeto,
            # campo ausente ou vazio) relança e segue como o 400 padrão do DRF.
            codigos = exc.get_codes().get("non_field_errors", [])
            if "authorization" in codigos:
                raise AuthenticationFailed("Usuário ou senha inválidos.") from exc
            raise
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key})
