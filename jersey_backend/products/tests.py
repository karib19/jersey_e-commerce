from django.test import TestCase
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Category, Product, ProductVariant
from accounts.models import User

class ProductAPITest(APITestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name="Football Jerseys",
            slug="football-jerseys",
            description="Football jerseys",
            is_active=True
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Real Madrid Jersey",
            slug="real-madrid-jersey",
            description="Real Madrid home jersey",
            team="Real Madrid",
            season="2026-27",
            price="2500.00",
            is_active=True
        )

    def test_category_list(self):
        response = self.client.get("/api/categories/")

        self.assertEqual(
        response.status_code,
        status.HTTP_200_OK
        )

        self.assertEqual(
        response.data["count"],
        1
        )

    def test_product_list(self):
        response = self.client.get("/api/products/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(response.data["count"], 1)

    def test_product_detail(self):
        response = self.client.get(
            "/api/products/real-madrid-jersey/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            response.data["name"],
            "Real Madrid Jersey"
        )

    def test_product_search(self):
        response = self.client.get(
            "/api/products/?search=Real"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(response.data["count"], 1)

    def test_inactive_product_not_visible(self):
        self.product.is_active = False
        self.product.save()

        response = self.client.get("/api/products/")

        self.assertEqual(
            response.data["count"],
            0
        )

    def test_product_rejects_zero_price(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Product.objects.create(
                    category=self.category,
                    name="Zero Price Jersey",
                    slug="zero-price-jersey",
                    price="0.00"
            )


    def test_product_rejects_negative_price(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Product.objects.create(
                    category=self.category,
                    name="Negative Price Jersey",
                    slug="negative-price-jersey",
                    price="-500.00"
        )

    def test_product_rejects_invalid_discount_price(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Product.objects.create(
                    category=self.category,
                    name="Invalid Discount Jersey",
                    slug="invalid-discount-jersey",
                    price="2000.00",
                    discount_price="2500.00"
        )

    def test_product_variant_rejects_negative_stock(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductVariant.objects.create(
                    product=self.product,
                    size="M",
                    stock=-1,
                    sku="NEGATIVE-STOCK-001"
                    )

class AdminProductCategoryAPITest(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="Admin123",
            role="admin"
        )

        self.customer = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="Customer123",
            role="customer"
        )

        self.category = Category.objects.create(
            name="Football Jerseys",
            slug="football-jerseys"
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Real Madrid Jersey",
            slug="real-madrid-jersey",
            price="2500.00"
        )

    def test_admin_can_create_product(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/admin/products/",
            {
                "name": "Barcelona Jersey",
                "slug": "barcelona-jersey",
                "category_id": self.category.id,
                "price": "2000.00",
                "team": "Barcelona"
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.assertTrue(
            Product.objects.filter(
                slug="barcelona-jersey"
            ).exists()
        )

    def test_customer_cannot_create_product(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            "/api/admin/products/",
            {
                "name": "Test Jersey",
                "slug": "test-jersey",
                "category_id": self.category.id,
                "price": "1500.00"
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )

    def test_admin_can_update_product(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            f"/api/admin/products/{self.product.slug}/",
            {
                "price": "2200.00"
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.product.refresh_from_db()

        self.assertEqual(
            str(self.product.price),
            "2200.00"
        )

    def test_product_delete_is_soft_delete(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            f"/api/admin/products/{self.product.slug}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT
        )

        self.product.refresh_from_db()

        self.assertFalse(self.product.is_active)

    def test_admin_can_create_category(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/admin/categories/",
            {
                "name": "National Team Jerseys",
                "slug": "national-team-jerseys"
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

    def test_category_delete_is_soft_delete(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            f"/api/admin/categories/{self.category.slug}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT
        )

        self.category.refresh_from_db()

        self.assertFalse(self.category.is_active)

    def test_customer_cannot_access_admin_categories(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.get(
            "/api/admin/categories/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )

class AdminProductVariantAPITest(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="variantadmin",
            email="variantadmin@example.com",
            password="TestPass123!",
            role="admin"
        )

        self.customer = User.objects.create_user(
            username="variantcustomer",
            email="variantcustomer@example.com",
            password="TestPass123!",
            role="customer"
        )

        self.category = Category.objects.create(
            name="Football Jerseys",
            slug="football-jerseys"
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Argentina Home Jersey",
            slug="argentina-home-jersey",
            price="1500.00"
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            size="L",
            stock=10
        )

        self.list_url = (
            f"/api/admin/products/{self.product.id}/variants/"
        )

        self.detail_url = (
            f"/api/admin/products/{self.product.id}/variants/"
            f"{self.variant.id}/"
        )

    def test_admin_can_list_variants(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_create_variant(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.list_url,
            {
                "size": "XL",
                "stock": 20
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(
            ProductVariant.objects.filter(
                product=self.product,
                size="XL",
                stock=20
            ).exists()
        )

    def test_admin_can_update_variant_stock(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.detail_url,
            {"stock": 25},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 25)

    def test_customer_cannot_list_variants(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_cannot_create_variant(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            self.list_url,
            {
                "size": "XXL",
                "stock": 15
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_cannot_update_variant(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.patch(
            self.detail_url,
            {"stock": 50},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)