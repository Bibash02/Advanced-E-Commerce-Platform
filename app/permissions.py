from django.core.exceptions import PermissionDenied
from .models import UserProfile


def is_supplier(user):
    try:
        return user.userprofile.role == "SUPPLIER"
    except UserProfile.DoesNotExist:
        return False


def is_customer(user):
    try:
        return user.userprofile.role == "CUSTOMER"
    except UserProfile.DoesNotExist:
        return False


def is_delivery(user):
    try:
        return user.userprofile.role == "DELIVERY"
    except UserProfile.DoesNotExist:
        return False


def supplier_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and is_supplier(request.user):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return wrapper


def customer_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and is_customer(request.user):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return wrapper


def delivery_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and is_delivery(request.user):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return wrapper