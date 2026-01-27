from django.contrib import admin
from .models import *

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'profile_image')
    search_fields = ('user__username',)

admin.site.register(UserProfile, UserProfileAdmin)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'image', 'is_active', 'created_at']
    list_filter = ['name',]
    search_fields = ['name',]

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'supplier', 'category', 'name', 'description', 'price', 'image', 'created_at']
    list_filter = ['supplier', 'category', 'name']
    search_fields = ['category', 'name']

@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ['id', 'supplier', 'title', 'image', 'content', 'created_at']
    list_filter = ['supplier', 'title']
    search_fields = ['supplier', 'title']

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'comment', 'created_at']
    list_filter = ['product', 'user', 'rating']
    search_fields = ['product', 'user']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('user',)

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'cart', 'product', 'quantity']
    list_filter = ['cart', 'product']
    search_fields = ['product']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'full_name', 'email', 'phone', 'address', 'city', 'country', 'amount', 'payment_type', 'transaction_uuid', 'status', 'created_at']
    list_per_page = 10

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'product', 'quantity', 'price']
    list_filter = ['product', 'price']
    search_fields = ['product',]

@admin.register(DeliveryDocument)
class DeliveryDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'full_name', 'phone', 'address', 'vehicle_type', 'vehicle_number', 'government_id', 'driving_license', 'vehicle_document', 'cv', 'created_at']
    list_filter = ['user', 'address', 'vehicle_type']
    search_fields = ['address', 'vehicle_type']

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'email', 'phone', 'subject', 'message', 'created_at']
    list_filter = ['name', 'subject']
    search_fields = ['name', 'subject']

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_address', 'latitude', 'longitude', 'is_default']
    list_filter = ['user', 'full_address']
    search_fields = ['user__username']