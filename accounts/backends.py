from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Authenticate legacy usernames first, then a unique email address."""

    def authenticate(
        self,
        request,
        username=None,
        password=None,
        **kwargs,
    ):
        UserModel = get_user_model()
        login_value = username or kwargs.get(
            UserModel.USERNAME_FIELD
        )

        if login_value is None or password is None:
            return None

        user = None

        try:
            user = UserModel._default_manager.get_by_natural_key(
                login_value
            )
        except UserModel.DoesNotExist:
            try:
                user = UserModel._default_manager.get(
                    email__iexact=login_value.strip()
                )
            except (
                UserModel.DoesNotExist,
                UserModel.MultipleObjectsReturned,
            ):
                UserModel().set_password(password)
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
