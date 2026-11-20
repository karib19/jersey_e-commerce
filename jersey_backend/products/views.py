from rest_framework import generics
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from accounts.permissions import IsAdminRole
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Product, ProductVariant
from .serializers import CategorySerializer, ProductSerializer, AdminProductSerializer, AdminCategorySerializer, AdminProductVariantSerializer


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True).order_by("id")
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(
        is_active=True,
        category__is_active=True
    ).select_related("category").prefetch_related("variants")

    serializer_class = ProductSerializer
    permission_classes = [AllowAny]


    filter_backends = [
    DjangoFilterBackend,
    SearchFilter,
    OrderingFilter,
    ]

    filterset_fields = ["category", "team", "season", "is_featured"]

    search_fields = ["name", "team", "season", "description"]

    ordering_fields = ["price", "created_at", "name"]

    ordering = ["-created_at"]


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(
        is_active=True,
        category__is_active=True
    ).select_related("category").prefetch_related("variants")

    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"


class AdminProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.select_related("category").prefetch_related("variants").all()
    serializer_class = AdminProductSerializer
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.select_related("category").prefetch_related("variants").all()
    serializer_class = AdminProductSerializer
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = "slug"

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class AdminCategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all().order_by("-created_at")
    serializer_class = AdminCategorySerializer
    permission_classes = [IsAdminRole]


class AdminCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = AdminCategorySerializer
    permission_classes = [IsAdminRole]
    lookup_field = "slug"

    def perform_destroy(self, instance):

        instance.is_active = False
        instance.save(update_fields=["is_active"])

class AdminProductVariantListCreateView(generics.ListCreateAPIView):
    serializer_class = AdminProductVariantSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        return ProductVariant.objects.filter(
            product_id=self.kwargs["product_id"]).order_by("id"
        ).select_related("product")

    def perform_create(self, serializer):
        product = get_object_or_404(
            Product,
            pk=self.kwargs["product_id"]
        )
        serializer.save(product=product)


class AdminProductVariantDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = AdminProductVariantSerializer
    permission_classes = [IsAdminRole]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return ProductVariant.objects.filter(
            product_id=self.kwargs["product_id"]
        ).select_related("product")