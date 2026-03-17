from django.contrib.auth.models import AbstractUser
from django.db import models
from .managers import CustomUserManager
import uuid


class User(AbstractUser):
    class UserType(models.IntegerChoices):
        SUPERADMIN = 0, "SuperAdmin"
        USER = 1, "User"

    username = models.CharField(max_length=150, null=True, blank=True)
    uid = models.CharField(unique=True, default=uuid.uuid4, max_length=50)
    user_type = models.PositiveSmallIntegerField(
        choices=UserType.choices, default=UserType.USER
    )
    email = models.EmailField(unique=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = ["username"]

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class Message(models.Model):
    sender = models.ForeignKey(
        User, related_name="sent_messages", on_delete=models.CASCADE
    )
    receiver = models.ForeignKey(
        User, related_name="received_messages", on_delete=models.CASCADE
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["sender", "receiver", "timestamp"]),
            models.Index(fields=["receiver", "sender", "timestamp"]),
            models.Index(fields=["receiver", "is_read"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return self.content
