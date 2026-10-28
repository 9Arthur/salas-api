from django.urls import path

from users.views import LoginView, RegistroView

urlpatterns = [
    path("registro/", RegistroView.as_view()),
    path("token/", LoginView.as_view()),
]
