from django.urls import path, include
from .views import *
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('customer/products', CustomerProductListAPIView.as_view()),
    path('customer/blogs', CustomerBlogListAPIView.as_view()),
    path('customer/orders', CustomerOrderCreateAPIView.as_view()),
    path('customer/profile', CustomerProfileAPIView.as_view()),
    path('customer/cart', CartAPIView.as_view(), name='cutomer-cart'),
    path('customer/checkout', CheckoutAPIView.as_view(), name='customer-checkout'),

    path('supplier/products', SupplierProductAPIView.as_view()),
    path('supplier/products/<int:pk>', SupplierProductDetailAPIView.as_view()),
    path('supplier/blogs', SupplierBlogAPIView.as_view()),
    path('supplier/blogs/<int:pk>', SupplierBlogDetailAPIView.as_view()),
    path('supplier/profile', SupplierProfileAPIView.as_view()),
]