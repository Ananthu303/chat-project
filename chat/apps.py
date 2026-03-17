from django.apps import AppConfig
class ChatConfig(AppConfig):
    name = "chat"

    def ready(self):
        from .models import User
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin", email="admin@gmail.com", password="Testpassword@123"
            )
