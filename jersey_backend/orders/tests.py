from django.test import TestCase
from decimal import Decimal
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from products.models import Category, Product, ProductVariant
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory

User = get_user_model()


class CartCheckoutAPITest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="Customer123",
            role="customer"
        )

        self.category = Category.objects.create(
            name="Football",
            slug="football"
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Barcelona Jersey",
            slug="barcelona-jersey",
            price="2000.00",
            is_active=True
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            size="M",
            stock=10,
            sku="BAR-M-001"
        )

        self.cart = Cart.objects.create(
            user=self.user
        )

        self.client.force_authenticate(
            user=self.user
        )

    def test_add_item_to_cart(self):
        response = self.client.post(
            "/api/cart/items/",
            {
                "variant_id": self.variant.id,
                "quantity": 2
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            CartItem.objects.filter(
                cart=self.cart
            ).count(),
            1
        )

    def test_cart_rejects_quantity_above_stock(self):
        response = self.client.post(
            "/api/cart/items/",
            {
                "variant_id": self.variant.id,
                "quantity": 11
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_checkout_success(self):
        CartItem.objects.create(
            cart=self.cart,
            variant=self.variant,
            quantity=2
        )

        response = self.client.post(
            "/api/checkout/",
            {
                "full_name": "Test Customer",
                "email": "customer@example.com",
                "phone": "01700000000",
                "address": "Dhaka",
                "city": "Dhaka",
                "payment_method": "cod"
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.assertEqual(
            Order.objects.count(),
            1
        )

        self.variant.refresh_from_db()

        self.assertEqual(
            self.variant.stock,
            8
        )

    def test_checkout_rejects_unsupported_payment_method(self):
        CartItem.objects.create(
        cart=self.cart,
        variant=self.variant,
        quantity=2
        )

        response = self.client.post(
            "/api/checkout/",
        {
            "full_name": "Test Customer",
            "email": "customer@example.com",
            "phone": "01700000000",
            "address": "Dhaka",
            "city": "Dhaka",
            "payment_method": "bkash"
        },
            format="json"
        )

        self.assertEqual(
        response.status_code,
        status.HTTP_400_BAD_REQUEST
        )

        self.assertEqual(
        Order.objects.count(),
        0
        )

        self.variant.refresh_from_db()

        self.assertEqual(
        self.variant.stock,
        10
        )

        self.assertEqual(
        CartItem.objects.filter(cart=self.cart).count(),
        1
        )

    def test_checkout_empty_cart(self):
        response = self.client.post(
            "/api/checkout/",
            {
                "full_name": "Test Customer",
                "email": "customer@example.com",
                "phone": "01700000000",
                "address": "Dhaka",
                "city": "Dhaka",
                "payment_method": "cod"
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_checkout_ignores_client_sent_price(self):
        CartItem.objects.create(
        cart=self.cart,
        variant=self.variant,
        quantity=2
        )

        response = self.client.post(
            "/api/checkout/",
        {
            "full_name": "Test Customer",
            "email": "customer@example.com",
            "phone": "01700000000",
            "address": "Dhaka",
            "city": "Dhaka",
            "payment_method": "cod",
            "price": "1.00"
        },
            format="json"
        )

        self.assertEqual(
        response.status_code,
        status.HTTP_201_CREATED
        )

        order = Order.objects.get()

        self.assertEqual(order.subtotal, Decimal("4000.00"))


    def test_checkout_uses_discount_price(self):
        self.product.discount_price = "1500.00"
        self.product.save()

        CartItem.objects.create(
        cart=self.cart,
        variant=self.variant,
        quantity=2
        )

        response = self.client.post(
            "/api/checkout/",
        {
            "full_name": "Test Customer",
            "email": "customer@example.com",
            "phone": "01700000000",
            "address": "Dhaka",
            "city": "Dhaka",
            "payment_method": "cod"
        },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        order = Order.objects.get()
        order_item = OrderItem.objects.get(order=order)

        self.assertEqual(order.subtotal, Decimal("3000.00"))
        self.assertEqual(order_item.unit_price, Decimal("1500.00"))

    def test_checkout_rejects_inactive_product(self):
        self.product.is_active = False
        self.product.save()

        CartItem.objects.create(
            cart=self.cart,
            variant=self.variant,
            quantity=2
        )

        response = self.client.post(
            "/api/checkout/",
        {
            "full_name": "Test Customer",
            "email": "customer@example.com",
            "phone": "01700000000",
            "address": "Dhaka",
            "city": "Dhaka",
            "payment_method": "cod"
        },
            format="json"
        )

        self.assertEqual(
        response.status_code,
        status.HTTP_400_BAD_REQUEST
        )

        self.assertEqual(Order.objects.count(), 0)

        self.variant.refresh_from_db()

        self.assertEqual(self.variant.stock, 10)

        self.assertEqual(
        CartItem.objects.filter(cart=self.cart).count(),
        1
        )


    def test_checkout_rejects_inactive_category(self):
        self.category.is_active = False
        self.category.save()

        CartItem.objects.create(
            cart=self.cart,
            variant=self.variant,
            quantity=2
        )

        response = self.client.post(
            "/api/checkout/",
        {
            "full_name": "Test Customer",
            "email": "customer@example.com",
            "phone": "01700000000",
            "address": "Dhaka",
            "city": "Dhaka",
            "payment_method": "cod"
        },
            format="json"
        )

        self.assertEqual(
        response.status_code,
        status.HTTP_400_BAD_REQUEST
        )

        self.assertEqual(Order.objects.count(), 0)

        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)

        self.assertEqual(
        CartItem.objects.filter(cart=self.cart).count(),
        1
        )

    def test_checkout_rejects_quantity_above_current_stock(self):
        CartItem.objects.create(
            cart=self.cart,
            variant=self.variant,
            quantity=5
        )

        self.variant.stock = 3
        self.variant.save()

        response = self.client.post(
            "/api/checkout/",
        {
            "full_name": "Test Customer",
            "email": "customer@example.com",
            "phone": "01700000000",
            "address": "Dhaka",
            "city": "Dhaka",
            "payment_method": "cod"
        },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertEqual(Order.objects.count(), 0)

        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 3)

        self.assertEqual(
        CartItem.objects.filter(cart=self.cart).count(),
        1
        )

class OrderManagementAPITest(APITestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            username="customer1",
            email="customer1@example.com",
            password="Customer123",
            role="customer"
        )

        self.other_customer = User.objects.create_user(
            username="customer2",
            email="customer2@example.com",
            password="Customer123",
            role="customer"
        )

        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="Admin123",
            role="admin"
        )

        self.category = Category.objects.create(
            name="Test Jerseys",
            slug="test-jerseys"
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Test Jersey",
            slug="test-jersey",
            price="2000.00"
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            size="L",
            stock=10,
            sku="TEST-L-001"
        )

        self.order = self.create_order(self.customer)

        self.other_order = self.create_order(
            self.other_customer
        )

    def create_order(self, user):
        order = Order.objects.create(
            user=user,
            full_name="Test Customer",
            email=user.email,
            phone="01700000000",
            address="Dhaka",
            city="Dhaka",
            country="Bangladesh",
            subtotal="2000.00",
            delivery_fee="0.00",
            discount_amount="0.00",
            total_amount="2000.00",
            status=Order.Status.PENDING,
            payment_method=Order.PaymentMethod.COD,
            payment_status=Order.PaymentStatus.PENDING
        )

        OrderItem.objects.create(
            order=order,
            variant=self.variant,
            product_name="Test Jersey",
            size="L",
            sku="TEST-L-001",
            unit_price="2000.00",
            quantity=2
        )

        return order

    def test_customer_can_view_own_order(self):
        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.get(
            f"/api/orders/{self.order.order_number}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    def test_customer_cannot_view_other_order(self):
        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.get(
            f"/api/orders/{self.other_order.order_number}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND
        )

    def test_customer_can_cancel_pending_order(self):
        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.post(
            f"/api/orders/{self.order.order_number}/cancel/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.order.refresh_from_db()
        self.variant.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CANCELLED
        )

        self.assertEqual(
            self.variant.stock,
            12
        )

        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=self.order,
                status=Order.Status.CANCELLED
            ).exists()
        )

    def test_customer_cannot_access_admin_orders(self):
        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.get(
            "/api/admin/orders/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )

    def test_admin_can_view_all_orders(self):
        self.client.force_authenticate(
            user=self.admin
        )

        response = self.client.get(
            "/api/admin/orders/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    def test_admin_can_confirm_pending_order(self):
        self.client.force_authenticate(
            user=self.admin
        )

        response = self.client.patch(
            f"/api/admin/orders/{self.order.order_number}/status/",
            {
                "status": Order.Status.CONFIRMED
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CONFIRMED
        )

        self.assertEqual(
            OrderStatusHistory.objects.filter(
                order=self.order,
                status=Order.Status.CONFIRMED
            ).count(),
            1,
        )

    def test_admin_can_cancel_order_without_duplicate_history(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            f"/api/admin/orders/{self.order.order_number}/status/",
            {"status": Order.Status.CANCELLED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.variant.refresh_from_db()

        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(self.variant.stock, 12)
        self.assertEqual(
            OrderStatusHistory.objects.filter(
                order=self.order,
                status=Order.Status.CANCELLED,
            ).count(),
            1,
        )

    def test_cancelled_order_cannot_be_cancelled_twice(self):
        self.client.force_authenticate(user=self.customer)

        first_response = self.client.post(
        f"/api/orders/{self.order.order_number}/cancel/"
        )

        self.assertEqual(
        first_response.status_code,
        status.HTTP_200_OK
        )

        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 12)

        second_response = self.client.post(
        f"/api/orders/{self.order.order_number}/cancel/"
        )

        self.assertEqual(
        second_response.status_code,
        status.HTTP_400_BAD_REQUEST
        )

        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 12)

        self.assertEqual(
            OrderStatusHistory.objects.filter(
                order=self.order,
                status=Order.Status.CANCELLED
        ).count(),
        1
        )

    def test_customer_cannot_cancel_delivered_order(self):
        self.order.status = Order.Status.DELIVERED
        self.order.save()

        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            f"/api/orders/{self.order.order_number}/cancel/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)

        self.order.refresh_from_db()
        self.assertEqual(
        self.order.status,
        Order.Status.DELIVERED
        )

    def test_order_rejects_negative_subtotal(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.order.subtotal = "-100.00"
                self.order.save()

    def test_order_rejects_negative_delivery_fee(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.order.delivery_fee = "-100.00"
                self.order.save()

    def test_order_rejects_negative_discount(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.order.discount_amount = "-100.00"
                self.order.save()

    def test_order_rejects_incorrect_total_amount(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.order.total_amount = "1500.00"
                self.order.save()

class AdminDashboardAPITest(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="dashboardadmin",
            email="dashboardadmin@example.com",
            password="TestPass123!",
            role="admin"
        )

        self.customer = User.objects.create_user(
            username="dashboardcustomer",
            email="dashboardcustomer@example.com",
            password="TestPass123!",
            role="customer"
        )

        self.url = "/api/admin/dashboard/"

    def test_admin_can_access_dashboard(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_fields = [
            "total_orders",
            "pending_orders",
            "total_products",
            "active_categories",
            "total_customers",
            "low_stock_variants",
            "total_revenue",
            "recent_orders",
        ]

        for field in expected_fields:
            self.assertIn(field, response.data)

    def test_customer_cannot_access_dashboard(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_access_dashboard(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)