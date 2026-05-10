from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import redirect, render

from .models import UserProfile


def register_page(request):
    """
    Страница регистрации.

    Что делает:
    - принимает email, username, password и password_repeat
    - проверяет корректность данных
    - создаёт пользователя в auth_user
    - создаёт профиль в habits_userprofile
    - сразу авторизует пользователя
    - перенаправляет в приложение
    """

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        password_repeat = request.POST.get("password_repeat", "").strip()

        context = {
            "email": email,
            "username": username,
        }

        if not email or not username or not password or not password_repeat:
            context["error"] = "Заполни все поля."
            return render(request, "habits/register.html", context)

        try:
            validate_email(email)
        except ValidationError:
            context["error"] = "Введи корректную почту."
            return render(request, "habits/register.html", context)

        if len(username) < 3:
            context["error"] = "Логин должен быть минимум 3 символа."
            return render(request, "habits/register.html", context)

        if " " in username:
            context["error"] = "Логин не должен содержать пробелы."
            return render(request, "habits/register.html", context)

        if len(password) < 6:
            context["error"] = "Пароль должен быть минимум 6 символов."
            return render(request, "habits/register.html", context)

        if password != password_repeat:
            context["error"] = "Пароли не совпадают."
            return render(request, "habits/register.html", context)

        User = get_user_model()

        if User.objects.filter(username=username).exists():
            context["error"] = "Пользователь с таким логином уже существует."
            return render(request, "habits/register.html", context)

        if User.objects.filter(email=email).exists():
            context["error"] = "Пользователь с такой почтой уже существует."
            return render(request, "habits/register.html", context)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

        UserProfile.objects.get_or_create(user=user)

        login(request, user)

        return redirect("/api/app/")

    return render(request, "habits/register.html")


def login_page(request):
    """
    Страница входа.

    Что делает:
    - позволяет войти по логину или email
    - проверяет пароль
    - авторизует через Django session
    - перенаправляет в приложение
    """

    if request.method == "POST":
        login_value = request.POST.get("login", "").strip()
        password = request.POST.get("password", "").strip()

        User = get_user_model()

        user_obj = User.objects.filter(
            Q(username=login_value) | Q(email=login_value.lower())
        ).first()

        if user_obj is None:
            return render(
                request,
                "habits/login.html",
                {
                    "error": "Пользователь не найден.",
                    "login": login_value,
                },
            )

        user = authenticate(
            request,
            username=user_obj.username,
            password=password,
        )

        if user is None:
            return render(
                request,
                "habits/login.html",
                {
                    "error": "Неверный пароль.",
                    "login": login_value,
                },
            )

        UserProfile.objects.get_or_create(user=user)

        login(request, user)

        return redirect("/api/app/")

    return render(request, "habits/login.html")


def logout_page(request):
    """
    Выход из аккаунта.
    """

    logout(request)

    return redirect("/api/login/")