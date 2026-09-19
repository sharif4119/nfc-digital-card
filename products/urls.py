from django.urls import path

from .views import product_detail, product_list


urlpatterns = [
    path(
        "cards/",
        product_list,
        name="product_list",
    ),

    path(
        "cards/<int:pk>/",
        product_detail,
        name="product_detail",
    ),
]