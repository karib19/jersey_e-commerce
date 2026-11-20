from django.urls import path

from .views import (CartView,CartItemAddView, CartItemUpdateDeleteView, CartClearView,
CartMergeView, CheckoutView, OrderHistoryView, OrderDetailView, AdminOrderListView,
AdminOrderStatusUpdateView, AdminDashboardView, CustomerOrderCancelView)


urlpatterns = [
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/", CartItemAddView.as_view(), name="cart-add"),
    path("cart/items/<int:item_id>/",CartItemUpdateDeleteView.as_view(),name="cart-item-detail"),
    path("cart/clear/", CartClearView.as_view(), name="cart-clear"),
    path("cart/merge/", CartMergeView.as_view(), name="cart-merge"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("orders/", OrderHistoryView.as_view(), name="order-history"),
    path("orders/<uuid:order_number>/",OrderDetailView.as_view(),name="order-detail"),
    path("admin/orders/", AdminOrderListView.as_view(), name="admin-orders"),
    path("admin/orders/<uuid:order_number>/status/", AdminOrderStatusUpdateView.as_view(), name="admin-order-status-update"),
    path("admin/dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("orders/<uuid:order_number>/cancel/",CustomerOrderCancelView.as_view(),name="customer-order-cancel",),
]