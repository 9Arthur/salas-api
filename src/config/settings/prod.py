from .base import *

DEBUG = False

# O Fly termina o TLS na borda e repassa o pedido em HTTP, marcando o protocolo
# original neste cabeçalho; sem isso, todo pedido pareceria HTTP (SA-52).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
# O health check do Fly chega direto na máquina, em HTTP; o fly.toml manda nele
# o Host e o X-Forwarded-Proto (SA-58). A isenção é reserva para um check sem
# os cabeçalhos, que com o redirect receberia 301 e nunca daria a máquina como
# saudável.
SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Estáticos (admin) servidos pelo próprio processo, com hash no nome e cache
# longo (SA-51). Lista nova, e não insert(): a lista é a mesma da base.
_depois_da_seguranca = (
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1
)
MIDDLEWARE = [
    *MIDDLEWARE[:_depois_da_seguranca],
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[_depois_da_seguranca:],
]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

# Com DEBUG = False, o logging padrão do Django só manda os erros para o
# mail_admins, que sem ADMINS não faz nada: o traceback de um 500 sumiria. Aqui,
# tudo de WARNING para cima vai para a saída de erro do processo (SA-59).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
