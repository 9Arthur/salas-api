from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from reservas.models import Sala

SALAS = [("Sala Azul", 6), ("Sala Verde", 10), ("Auditório", 40)]
USUARIO = "demo"
EMAIL = "demo@exemplo.com"
# Senha pública por definição (vai para o README como credencial de
# demonstração): por isso o demo é sempre um usuário comum, e cada execução o
# rebaixa se alguém o promoveu.
SENHA = "demo1234"


class Command(BaseCommand):
    help = "Cria ou recoloca no lugar as salas e o usuário de demonstração."

    @transaction.atomic
    def handle(self, *args, **options):
        criadas = 0
        for nome, capacidade in SALAS:
            # O índice único é Lower(nome): a busca ignora a caixa, e o nome volta
            # à grafia da demonstração.
            _, criada = Sala.objects.update_or_create(
                nome__iexact=nome,
                defaults={"nome": nome, "capacidade": capacidade, "ativa": True},
            )
            criadas += criada
        usuario, criado = get_user_model().objects.update_or_create(
            username=USUARIO,
            defaults={
                "email": EMAIL,
                "is_staff": False,
                "is_superuser": False,
                "is_active": True,
            },
        )
        usuario.set_password(SENHA)
        usuario.save(update_fields=["password"])
        situacao = "criado" if criado else "atualizado"
        self.stdout.write(
            f"seed_demo: {len(SALAS)} salas ({criadas} criadas) "
            f"e o usuário demo ({situacao})."
        )
