from rest_framework import generics, permissions

from apps.users.serializers import UserRegistrationSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
