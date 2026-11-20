from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Order, OrderItem, OrderStatusHistory
from products.models import ProductVariant


@transaction.atomic
def cancel_order(order, changed_by=None, allowed_statuses=None):
    order = Order.objects.select_for_update().get(pk=order.pk)

    if order.status == Order.Status.CANCELLED:
        raise ValidationError("Order is already cancelled.")

    if order.status in [
        Order.Status.SHIPPED,
        Order.Status.DELIVERED,
    ]:
        raise ValidationError(
            "Cannot cancel a shipped or delivered order."
        )

    if (
        allowed_statuses is not None
        and order.status not in allowed_statuses
    ):
        raise ValidationError(
            "This order cannot be cancelled in its current status."
        )

    items = list(
        OrderItem.objects.filter(order=order).order_by("variant_id")
    )

    variant_ids = {
        item.variant_id
        for item in items
        if item.variant_id is not None
    }

    variants = {
        variant.id: variant
        for variant in ProductVariant.objects.select_for_update()
        .filter(id__in=variant_ids)
        .order_by("id")
    }

    for item in items:
        variant = variants.get(item.variant_id)

        if variant:
            variant.stock += item.quantity
            variant.save(update_fields=["stock"])

    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])

    OrderStatusHistory.objects.create(
        order=order,
        status=Order.Status.CANCELLED,
        note="Order cancelled.",
        changed_by=changed_by,
    )

    return order