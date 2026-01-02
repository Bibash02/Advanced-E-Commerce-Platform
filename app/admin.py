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