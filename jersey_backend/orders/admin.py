from django.contrib import admin

from .models import Order, OrderItem, Cart, CartItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "product_name",
        "size",
        "sku",
        "unit_price",
        "quantity",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "full_name",
        "phone",
        "total_amount",
        "status",
        "payment_method",
        "payment_status",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_method",
        "payment_status",
        "created_at",
    )

    search_fields = (
        "order_number",
        "full_name",
        "email",
        "phone",
    )

    readonly_fields = (
        "order_number",
        "subtotal",
        "delivery_fee",
        "discount_amount",
        "total_amount",
        "created_at",
        "updated_at",
    )

    inlines = [OrderItemInline]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "guest_token",
        "created_at",
    )

    search_fields = ("user__email", "guest_token")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cart",
        "variant",
        "quantity",
    )

@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "order",
        "status",
        "changed_by",
        "created_at",
    ]

    readonly_fields = [
        "order",
        "status",
        "note",
        "changed_by",
        "created_at",
    ]