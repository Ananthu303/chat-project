from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from .forms import RegisterForm
from .models import Message, User

channel_layer = get_channel_layer()


class RegisterView(View):
    template_name = "register.html"

    def get(self, request):
        form = RegisterForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.is_online = False
            new_user.save()
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "user_status",
                {
                    "type": "user_status_update",
                    "data": {
                        "uid": new_user.uid,
                        "username": new_user.username,
                        "is_online": new_user.is_online,
                    },
                },
            )

            return redirect("login")

        return render(request, self.template_name, {"form": form})


class LoginView(View):
    template_name = "login.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            user.is_online = True
            user.save()
            async_to_sync(channel_layer.group_send)(
                "user_status",
                {
                    "type": "user_status_update",
                    "data": {"uid": user.uid, "is_online": True},
                },
            )
            return redirect("user_list")
        return render(request, self.template_name, {"error": "Invalid credentials"})


class LogoutView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        user.is_online = False
        user.last_seen = timezone.now()
        user.save()
        logout(request)
        async_to_sync(channel_layer.group_send)(
            "user_status",
            {
                "type": "user_status_update",
                "data": {"uid": user.uid, "is_online": False},
            },
        )
        return redirect("login")


class UserListView(LoginRequiredMixin, View):
    template_name = "user_list.html"

    def get(self, request):
        users = User.objects.exclude(id=request.user.id).filter(
            user_type=User.UserType.USER
        )
        return render(request, self.template_name, {"users": users})


class ChatView(LoginRequiredMixin, View):
    template_name = "chat.html"

    def get(self, request, uid):
        other_user = get_object_or_404(User, uid=uid)
        messages = (
            Message.objects.select_related("sender", "receiver")
            .filter(
                sender__in=[request.user, other_user],
                receiver__in=[request.user, other_user],
            )
            .order_by("timestamp")
        )

        context = {
            "other_user": other_user,
            "messages": messages,
        }
        return render(request, self.template_name, context)
