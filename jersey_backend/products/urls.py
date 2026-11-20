from django.urls import path
from .views import  (CategoryListView, ProductListView, ProductDetailView,
AdminProductListCreateView, AdminProductDetailView, AdminCategoryListCreateView, AdminCategoryDetailView,
AdminProductVariantListCreateView, AdminProductVariantDetailView)


urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/",ProductDetailView.as_view(),name="product-detail"),
    path("admin/products/", AdminProductListCreateView.as_view(), name="admin-product-list-create"),
    path("admin/products/<slug:slug>/", AdminProductDetailView.as_view(), name="admin-product-detail"),
    path("admin/categories/", AdminCategoryListCreateView.as_view(), name="admin-category-list-create"),
    path("admin/categories/<slug:slug>/", AdminCategoryDetailView.as_view(), name="admin-category-detail"),
    path("admin/products/<int:product_id>/variants/",AdminProductVariantListCreateView.as_view(),name="admin-product-variant-list-create"),
    path("admin/products/<int:product_id>/variants/<int:pk>/",AdminProductVariantDetailView.as_view(),name="admin-product-variant-detail"),
]