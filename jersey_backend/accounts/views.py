from rest_framework import generics
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenBlacklistView
from rest_framework.throttling import AnonRateThrottle

from .models import User
from .serializers import RegisterSerializer, CustomTokenObtainPairSerializer, UserProfileSerializer


class RegisterRateThrottle(AnonRateThrottle):
    scope = "register"

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]



class UserProfileView(RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class LogoutView(TokenBlacklistView):
    pass