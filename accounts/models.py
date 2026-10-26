from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.db.models.functions import Lower


class UserManager(DjangoUserManager):
    """Stores emails lowercased and looks users up by email case-insensitively."""

    def _create_user(self, username, email, password, **extra_fields):
        email = (email or "").strip().lower()
        return super()._create_user(username, email, password, **extra_fields)

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)


class User(AbstractUser):
    username = models.CharField(
        "kullanıcı adı",
        max_length=20,
        unique=True,
        validators=[
            MinLengthValidator(3),
            RegexValidator(
                r"^[A-Za-z0-9_]+$",
                "Kullanıcı adı yalnızca harf, rakam ve alt çizgi içerebilir.",
            ),
        ],
        help_text="3–20 karakter; harf, rakam ve alt çizgi.",
        error_messages={"unique": "Bu kullanıcı adı zaten alınmış."},
    )
    email = models.EmailField(
        "e-posta",
        unique=True,
        error_messages={"unique": "Bu e-posta adresiyle zaten bir hesap var."},
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        verbose_name = "kullanıcı"
        verbose_name_plural = "kullanıcılar"
        constraints = [
            models.UniqueConstraint(Lower("email"), name="unique_user_email_ci"),
            models.UniqueConstraint(Lower("username"), name="unique_user_username_ci"),
        ]

    def clean(self):
        super().clean()
        self.email = (self.email or "").strip().lower()

    def __str__(self):
        return self.username
