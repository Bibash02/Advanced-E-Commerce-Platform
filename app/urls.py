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

    path('supplier/permission', supplier_permission, name='supplier_permission'),
    path('supplier/profile', supplier_profile, name='supplier_profile'),
    path('supplier/profile/edit', edit_supplier_profile, name='edit_supplier_profile'),
    path('supplier/category/list', supplier_category_list, name='supplier_category_list'),
    path('supplier/product/list', supplier_products, name='product_list'),
    path('supplier/product/add', add_product, name='add_product'),
    path('supplier/product/edit/<int:pk>', edit_product, name='edit_product'),
    path('supplier/product/delete/<int:pk>', delete_product, name='delete_product'),

    path('supplier/products/category/<int:category_id>', supplier_products_by_category, name = 'supplier_products_by_category'),
    path('supplier/product/reviews', supplier_product_reviews, name='supplier_product_reviews'),
    path('supplier/orders', supplier_orders, name='supplier_orders'),
    path('supplier/cancel-orders', supplier_cancel_orders, name='supplier_cancel_orders'),
    path('supplier/earnings', supplier_earning, name='supplier_earnings'),
    path('supplier/assign-delivery/<int:order_id>', assign_delivery, name='assign_delivery'),
    path('supplier/delivery-list', delivery_person_list, name='delivery_person_list'),
    path('supplier/orders/assign-ajax/', assign_delivery_ajax, name='assign_delivery_ajax'),

    path('supplier/graph', supplier_graph, name='supplier_graph'),
 
    path('supplier/blog/list', supplier_blogs, name='blog_list'),
    path('supplier/blog/add', add_blog, name='add_blog'),
    path('supplier/blog/edit/<int:pk>', edit_blog, name='edit_blog'),
    path('supplier/blog/delete/<int:pk>', delete_blog, name='delete_blog'),

    path('customer/permission', customer_permission, name='customer_permission'),
    path('customer/profile', customer_profile, name='customer_profile'),
    path('customer/profile/edit', edit_customer_profile, name='edit_customer_profile'),
    path('customer/category/list', category_list_customer, name='customer_category_list'),
    path('customer/products/category/<int:category_id>', products_by_category, name='products_by_category'),
    path('customer/product/buy/<int:product_id>', buy_product, name='buy_product'),
    path('customer/blog/list', customer_blog_list, name='customer_blog_list'),
    path('customer/blog/detail/<int:blog_id>', customer_blog_detail, name='customer_blog_detail'),
    path('customer/product/all', all_products, name='all_products'),
    path('customer/cart/add/<int:product_id>', add_to_cart, name='add_to_cart'),
    path('customer/cart/', cart_page, name='cart_page'),
    path('customer/cart/remove/<int:item_id>', remove_from_cart, name='remove_from_cart'),

    path('customer/add-address', add_address, name='add_address'),

    path('customer/top-rated/products', top_rated_products, name='top_rated_products'),
    path('customer/product/search', search_products, name='search_products'),
    path('customer/product/detail/<int:product_id>', product_detail, name='product_detail'),
    path('customer/spending', customer_spending, name='customer_spending'),
    path('customer/order/history', customer_order_history, name='customer_order_history'),

    path('customer/graph', customer_graph, name='customer_graph'),

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
    path('delivery/order/detail/<order_id>', delivery_order_detail, name='order_detail'),
    path('delivery/order/ok/<int:order_id>', delivery_accept, name='delivery_accept'),
    path('delivery/order/cancel/<int:order_id>', delivery_cancel, name='delivery_cancel'),
    path('delivery/order/<int:order_id>/delivered/', delivery_mark_delivered, name='delivery_mark_delivered'),
    path('delivery/history/', delivery_history, name='delivery_history'),

    path('guidelines', guidelines, name='guidelines'),  
    path('customer/guidelines', customer_guidelines, name='customer_guidelines'),
    path('supplier/guidelines', supplier_guidelines, name='supplier_guidelines'),
    path('delivery/guidelines', delivery_guidelines, name='delivery_guidelines'),

    path('admin/sales-dashboard', sales_dashboard, name='sales_dashboard'),
]