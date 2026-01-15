from django.urls import path
from .views import *
from django.contrib.auth.views import *

urlpatterns = [
    path('', home, name='home'),
    path('signin', signin, name='signin'),
    path('signup/', signup, name='signup'),
    path('signout/', signout, name='signout'),
    path('about/', about, name='about'),
    path('contact/', contact, name='contact'),

    path('forgot-password/', PasswordResetView.as_view(), name='password_reset'),
    path('reset-password-sent/', PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset-complete/', PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('customer/dashboard/', customer_dashboard, name='customer_dashboard'),
    path('supplier/dashboard/', supplier_dashboard, name='supplier_dashboard'),
    path('delivery_personnel/dashboard', delivery_personnel_dashboard, name='delivery_personnel_dashboard'),

    path('supplier/profile', supplier_profile, name='supplier_profile'),
    path('supplier/profile/edit', edit_supplier_profile, name='edit_supplier_profile'),
    path('supplier/category/list', supplier_category_list, name='supplier_category_list'),
    path('supplier/product/list', supplier_products, name='product_list'),
    path('supplier/product/add', add_product, name='add_product'),
    path('supplier/product/edit/<int:pk>', edit_product, name='edit_product'),
    path('supplier/product/delete/<int:pk>', delete_product, name='delete_product'),

    path('supplier/blog/list', supplier_blogs, name='blog_list'),
    path('supplier/blog/add', add_blog, name='add_blog'),
    path('supplier/blog/edit/<int:pk>', edit_blog, name='edit_blog'),
    path('supplier/blog/delete/<int:pk>', delete_blog, name='delete_blog'),

    path('customer/profile', customer_profile, name='customer_profile'),
    path('customer/profile/edit', edit_customer_profile, name='edit_customer_profile'),
    path('customer/category/list', category_list_customer, name='customer_category_list'),
    path('customer/product/buy/<int:product_id>', buy_product, name='buy_product'),
    path('customer/blog/list', customer_blog_list, name='customer_blog_list'),
    path('customer/blog/detail/<int:blog_id>', customer_blog_detail, name='customer_blog_detail'),
    path('customer/product/all', all_products, name='all_products'),
    path('customer/cart/add/<int:product_id>', add_to_cart, name='add_to_cart'),
    path('customer/cart/', cart_page, name='cart_page'),
    path('customer/cart/remove/<int:item_id>', remove_from_cart, name='remove_from_cart'),

    path('customer/chekout', checkout, name='checkout'),
    path('customer/esewa/process', process_payment, name='process_payment'),
    path('customer/esewa/success', payment_success, name='payment_success'),
    path('customer/esewa/failed', payment_fail, name='payment_failed'),

    path('delivery/documents/', document_form, name='document_form'),
    path('delivery/documents/view/', document_view, name='document_view'),
    path('delivery/document/edit', document_edit, name='document_edit'),
    path('delivery/profile', delivery_profile, name='delivery_profile'),
    path('delivery/profile/edit', edit_delivery_profile, name='edit_delivery_profile'),
    path('delivery/order/list', delivery_order_list, name='delivery_order_list'),
    path('delivery/order/ok/<int:order_id>', delivery_accept, name='delivery_accept'),
    path('delivery/order/cancel/<int:order_id>', delivery_cancel, name='delivery_cancel'),
]