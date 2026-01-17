from django.urls import path, include
from .views import *
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'userprofiles', UserProfileViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'blogs', BlogViewSet)

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
]