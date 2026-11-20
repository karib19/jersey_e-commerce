from uuid import UUID
from accounts.models import User
from django.db import transaction
from django.db.models import Sum
from rest_framework import generics
from decimal import Decimal
from products.models import Product, Category, ProductVariant
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from .services import cancel_order
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from accounts.permissions import IsAdminRole
from .serializers import (CheckoutSerializer, OrderSerializer,
    CartSerializer,
    AddToCartSerializer,
    AdminOrderStatusSerializer,
    UpdateCartItemSerializer,
    OrderStatusHistorySerializer,
)



def get_user_cart(request):
    # Logged-in user cart
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(
            user=request.user
        )
        return cart

    # Guest cart
    token = request.headers.get("X-Cart-Token")

    if token:
        try:
            token = UUID(token)
        except ValueError:
            return None

        return Cart.objects.filter(
            guest_token=token,
            user__isnull=True
        ).first()

    return None


class CartView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            cart = get_user_cart(request)
        else:
            token = request.headers.get("X-Cart-Token")

            if token:
                cart = get_user_cart(request)

                if cart is None:
                    return Response(
                        {"error": "Invalid cart token."},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                cart = Cart.objects.create()

        serializer = CartSerializer(cart)

        return Response(serializer.data)


class CartItemAddView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        cart = get_user_cart(request)

        if cart is None:
            return Response(
                {"error": "Cart not found. Get a cart first."},
                status=status.HTTP_404_NOT_FOUND
            )

        input_serializer = AddToCartSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        variant_id = input_serializer.validated_data["variant_id"]
        quantity = input_serializer.validated_data["quantity"]

        variant = get_object_or_404(
            ProductVariant.objects.select_related(
                "product",
                "product__category"
            ),
            id=variant_id,
            product__is_active=True,
            product__category__is_active=True
        )

        if variant.stock < 1:
            return Response(
                {"error": "This product is out of stock."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            item, created = CartItem.objects.get_or_create(
                cart=cart,
                variant=variant,
                defaults={"quantity": quantity}
            )

            if not created:
                item.quantity += quantity

            if item.quantity > variant.stock:
                return Response(
                    {
                        "error": "Not enough stock.",
                        "available_stock": variant.stock
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            item.save()

        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_200_OK
        )


class CartItemUpdateDeleteView(APIView):
    permission_classes = [AllowAny]

    def patch(self, request, item_id):
        cart = get_user_cart(request)

        if cart is None:
            return Response(
                {"error": "Cart not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        item = get_object_or_404(
            CartItem,
            id=item_id,
            cart=cart
        )

        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = serializer.validated_data["quantity"]

        if quantity > item.variant.stock:
            return Response(
                {
                    "error": "Not enough stock.",
                    "available_stock": item.variant.stock
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        item.quantity = quantity
        item.save(update_fields=["quantity"])

        return Response(CartSerializer(cart).data)

    def delete(self, request, item_id):
        cart = get_user_cart(request)

        if cart is None:
            return Response(
                {"error": "Cart not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        item = get_object_or_404(
            CartItem,
            id=item_id,
            cart=cart
        )

        item.delete()

        return Response(
            {"message": "Item removed from cart."},
            status=status.HTTP_200_OK
        )


class CartClearView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request):
        cart = get_user_cart(request)

        if cart is None:
            return Response(
                {"error": "Cart not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        cart.items.all().delete()

        return Response(
            {"message": "Cart cleared successfully."},
            status=status.HTTP_200_OK
        )


class CartMergeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.headers.get("X-Cart-Token")

        if not token:
            return Response(
                {"error": "Guest cart token is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = UUID(token)
        except ValueError:
            return Response(
                {"error": "Invalid cart token."},
                status=status.HTTP_400_BAD_REQUEST
            )

        guest_cart = Cart.objects.filter(
            guest_token=token,
            user__isnull=True
        ).first()

        if not guest_cart:
            return Response(
                {"error": "Guest cart not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        with transaction.atomic():
            user_cart, created = Cart.objects.get_or_create(
                user=request.user
            )

            guest_items = guest_cart.items.select_related(
                "variant"
            ).all()

            # Validate stock before merging anything
            for guest_item in guest_items:
                existing_item = CartItem.objects.filter(
                    cart=user_cart,
                    variant=guest_item.variant
                ).first()

                total_quantity = guest_item.quantity

                if existing_item:
                    total_quantity += existing_item.quantity

                if total_quantity > guest_item.variant.stock:
                    return Response(
                        {
                            "error": "Not enough stock to merge cart.",
                            "product": guest_item.variant.product.name,
                            "size": guest_item.variant.size,
                            "available_stock": guest_item.variant.stock,
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Merge guest items into user cart
            for guest_item in guest_items:
                item, created = CartItem.objects.get_or_create(
                    cart=user_cart,
                    variant=guest_item.variant,
                    defaults={"quantity": guest_item.quantity}
                )

                if not created:
                    item.quantity += guest_item.quantity
                    item.save(update_fields=["quantity"])

            guest_cart.delete()

        return Response(
            {
                "message": "Guest cart merged successfully.",
                "cart": CartSerializer(user_cart).data
            },
            status=status.HTTP_200_OK
        )

class CheckoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        cart = get_user_cart(request)

        if cart is None:
            return Response(
                {"error": "Cart not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        checkout_serializer = CheckoutSerializer(data=request.data)
        checkout_serializer.is_valid(raise_exception=True)

        data = checkout_serializer.validated_data

        try:
            with transaction.atomic():
                cart_items = list(
                    cart.items.select_for_update()
                    .select_related(
                        "variant__product",
                        "variant__product__category"
                    ).order_by("variant_id")
                )

                if not cart_items:
                    return Response(
                        {"error": "Your cart is empty."},
                        status=status.HTTP_400_BAD_REQUEST
                    )


                variant_ids = sorted({
                    item.variant_id for item in cart_items
                })

                variants = {
                    variant.id: variant
                    for variant in ProductVariant.objects
                    .select_for_update()
                    .filter(id__in=variant_ids)
                    .order_by("id")
                }

                subtotal = Decimal("0.00")
                order_items_data = []


                for cart_item in cart_items:
                    variant = variants.get(cart_item.variant_id)

                    if variant is None:
                        raise ValueError("A product variant no longer exists.")

                    product = variant.product

                    if not product.is_active or not product.category.is_active:
                        raise ValueError(
                            f"{product.name} is no longer available."
                        )

                    if cart_item.quantity > variant.stock:
                        raise ValueError(
                            f"Not enough stock for {product.name} "
                            f"(Size {variant.size})."
                        )

                    price = (
                        product.discount_price
                        if product.discount_price is not None
                        else product.price
                    )

                    line_total = price * cart_item.quantity
                    subtotal += line_total

                    order_items_data.append({
                        "variant": variant,
                        "product_name": product.name,
                        "size": variant.size,
                        "sku": variant.sku,
                        "unit_price": price,
                        "quantity": cart_item.quantity,
                    })


                delivery_fee = Decimal("0.00")
                discount_amount = Decimal("0.00")
                total_amount = subtotal + delivery_fee - discount_amount


                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    full_name=data["full_name"],
                    email=data["email"],
                    phone=data["phone"],
                    address=data["address"],
                    city=data["city"],
                    postal_code=data.get("postal_code", ""),
                    country=data["country"],
                    payment_method=data["payment_method"],
                    customer_note=data.get("customer_note", ""),
                    subtotal=subtotal,
                    delivery_fee=delivery_fee,
                    discount_amount=discount_amount,
                    total_amount=total_amount,
                )
                OrderStatusHistory.objects.create(
    order=order,
    status=Order.Status.PENDING,
    note="Order placed successfully.",
    changed_by=request.user if request.user.is_authenticated else None,
)


                for item_data in order_items_data:
                    OrderItem.objects.create(
                        order=order,
                        **item_data
                    )

                    variant = item_data["variant"]
                    variant.stock -= item_data["quantity"]
                    variant.save(update_fields=["stock"])

                # Clear cart
                cart.items.all().delete()

        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "message": "Order placed successfully.",
                "order_number": str(order.order_number),
                "total_amount": str(order.total_amount),
                "status": order.status,
                "payment_status": order.payment_status,
            },
            status=status.HTTP_201_CREATED
        )

class OrderHistoryView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            user=self.request.user
        ).prefetch_related("items").order_by("-created_at")


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "order_number"

    def get_queryset(self):
        return Order.objects.filter(
            user=self.request.user
        ).prefetch_related("items", "status_history")

class AdminOrderListView(generics.ListAPIView):
    queryset = Order.objects.all().prefetch_related("items", "status_history").order_by("-created_at","-id")
    serializer_class = OrderSerializer
    permission_classes = [IsAdminRole]


class AdminOrderStatusUpdateView(generics.UpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = AdminOrderStatusSerializer
    permission_classes = [IsAdminRole]
    lookup_field = "order_number"
    http_method_names = ["patch"]

    def perform_update(self, serializer):
        new_status = serializer.validated_data["status"]

        if new_status == Order.Status.CANCELLED:
            cancel_order(
                serializer.instance,
                changed_by=self.request.user,
                allowed_statuses=[
                    Order.Status.PENDING,
                    Order.Status.CONFIRMED,
                Order.Status.PROCESSING,
                ],
            )
            serializer.instance.refresh_from_db()
            return

        order = serializer.save()
        OrderStatusHistory.objects.create(
            order=order,
            status=new_status,
            note=f"Order status changed to {new_status}.",
            changed_by=self.request.user,
        )


class AdminDashboardView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        total_orders = Order.objects.count()

        pending_orders = Order.objects.filter(
            status=Order.Status.PENDING
        ).count()

        total_products = Product.objects.count()

        active_categories = Category.objects.filter(
            is_active=True
        ).count()

        total_customers = User.objects.filter(
            role=User.Role.CUSTOMER
        ).count()

        low_stock_variants = ProductVariant.objects.filter(
            product__is_active=True,
            product__category__is_active=True,
            stock__lte=5
        ).count()

        total_revenue = Order.objects.filter(
            payment_status=Order.PaymentStatus.PAID
        ).aggregate(
            total=Sum("total_amount")
        )["total"] or 0

        recent_orders = Order.objects.prefetch_related(
            "items"
        ).order_by("-created_at")[:5]

        return Response({
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "total_products": total_products,
            "active_categories": active_categories,
            "total_customers": total_customers,
            "low_stock_variants": low_stock_variants,
            "total_revenue": total_revenue,
            "recent_orders": OrderSerializer(
                recent_orders,
                many=True
            ).data
        })

class CustomerOrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_number):
        order = get_object_or_404(
            Order,
            order_number=order_number,
            user=request.user,
        )

        if order.status != Order.Status.PENDING:
            return Response(
                {
                    "error": "Only pending orders can be cancelled."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            cancel_order(
                order,
                changed_by=request.user,
                allowed_statuses=[Order.Status.PENDING],
            )

        except ValidationError as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Order cancelled successfully.",
                "order_number": str(order.order_number),
                "status": order.status,
            },
            status=status.HTTP_200_OK,
        )
