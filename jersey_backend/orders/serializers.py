from decimal import Decimal
from rest_framework import serializers

from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory
from products.models import ProductVariant


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="variant.product.name",
        read_only=True
    )

    product_image = serializers.ImageField(
        source="variant.product.image",
        read_only=True
    )

    size = serializers.CharField(
        source="variant.size",
        read_only=True
    )

    original_price = serializers.DecimalField(
        source="variant.product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    price = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()

    stock = serializers.IntegerField(
        source="variant.stock",
        read_only=True
    )

    class Meta:
        model = CartItem
        fields = [
            "id",
            "variant",
            "product_name",
            "product_image",
            "size",
            "original_price",
            "price",
            "stock",
            "quantity",
            "line_total",
        ]

    def get_price(self, obj):
        product = obj.variant.product

        if product.discount_price is not None:
            return product.discount_price

        return product.price

    def get_line_total(self, obj):
        return self.get_price(obj) * obj.quantity


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "guest_token",
            "items",
            "total_items",
            "subtotal",
            "created_at",
            "updated_at",
        ]

    def get_total_items(self, obj):
        return sum(item.quantity for item in obj.items.all())

    def get_subtotal(self, obj):
        total = Decimal("0.00")

        for item in obj.items.select_related(
            "variant__product"
        ).all():
            product = item.variant.product

            price = (
                product.discount_price
                if product.discount_price is not None
                else product.price
            )

            total += price * item.quantity

        return total

class AddToCartSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class CheckoutSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)

    address = serializers.CharField()
    city = serializers.CharField(max_length=100)
    postal_code = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True
    )

    country = serializers.CharField(
        max_length=100,
        default="Bangladesh"
    )

    payment_method = serializers.ChoiceField(
    choices=[
        (Order.PaymentMethod.COD, "Cash on Delivery")
    ],
    default=Order.PaymentMethod.COD
    )

    customer_note = serializers.CharField(
        required=False,
        allow_blank=True
    )

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_name",
            "size",
            "sku",
            "unit_price",
            "quantity",
            "line_total",
        ]

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(
        source="changed_by.username",
        read_only=True,
        default=None
    )

    class Meta:
        model = OrderStatusHistory
        fields = [
            "id",
            "status",
            "note",
            "changed_by_name",
            "created_at",
        ]



class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    status_history = OrderStatusHistorySerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "user",
            "full_name",
            "email",
            "phone",
            "address",
            "city",
            "postal_code",
            "country",
            "subtotal",
            "delivery_fee",
            "discount_amount",
            "total_amount",
            "status",
            "payment_method",
            "payment_status",
            "customer_note",
            "items",
            "status_history",
            "created_at",
            "updated_at",
        ]


class AdminOrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["status"]

class AdminOrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["status"]

    def validate_status(self, new_status):
        order = self.instance

        allowed_transitions = {
            "pending": ["confirmed", "cancelled"],
            "confirmed": ["processing", "cancelled"],
            "processing": ["shipped", "cancelled"],
            "shipped": ["delivered"],
            "delivered": [],
            "cancelled": [],
        }

        if new_status not in allowed_transitions[order.status]:
            raise serializers.ValidationError(
                f"Cannot change order status from {order.status} to {new_status}."
            )

        return new_status
