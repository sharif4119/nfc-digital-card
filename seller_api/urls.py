from django.urls import path

from . import views


urlpatterns = [
    path(
        "login/",
        views.seller_login,
        name="seller_api_login",
    ),

    path(
        "dashboard/",
        views.dashboard,
        name="seller_api_dashboard",
    ),

    path(
        "orders/",
        views.order_list,
        name="seller_api_orders",
    ),

    path(
        "orders/<int:order_id>/",
        views.order_detail,
        name="seller_api_order_detail",
    ),

    path(
        "orders/<int:order_id>/assign-card/",
        views.assign_card,
        name="seller_api_assign_card",
    ),

    path(
        "cards/available/",
        views.available_cards,
        name="seller_api_available_cards",
    ),

    path(
        "cards/<int:card_id>/",
        views.card_detail,
        name="seller_api_card_detail",
    ),

    path(
        "cards/<int:card_id>/programmed/",
        views.mark_programmed,
        name="seller_api_programmed",
    ),

    path(
        "cards/<int:card_id>/activate/",
        views.activate_card,
        name="seller_api_activate",
    ),
]