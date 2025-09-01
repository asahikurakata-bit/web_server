print("servermanager.auth_backend module imported")

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
import logging

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        print(f"EmailBackend authenticate called with username={username}, kwargs={kwargs}")
        logging.debug(f"EmailBackend authenticate called with username={username}, kwargs={kwargs}")
        if username is None:
            username = kwargs.get('email')
        try:
            user = User.objects.get(email=username)
            print(f"User found in EmailBackend: {user}")
            logging.debug(f"User found in EmailBackend: {user}")
        except User.DoesNotExist:
            print("User not found in EmailBackend")
            logging.debug("User not found in EmailBackend")
            return None
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None
