from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    email = models.EmailField("e-mail")

    class Meta(AbstractUser.Meta):
        # Unicidade sobre Lower(email): "Ana@x" e "ana@x" são o mesmo e-mail.
        constraints = [
            models.UniqueConstraint(Lower("email"), name="users_email_unico_ci")
        ]
