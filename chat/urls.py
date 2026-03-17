from django.urls import path
from .views import RegisterView, LoginView, LogoutView, UserListView, ChatView

urlpatterns = [
    path("", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("users/", UserListView.as_view(), name="user_list"),
    path("chat/<str:uid>/", ChatView.as_view(), name="chat"),
]
