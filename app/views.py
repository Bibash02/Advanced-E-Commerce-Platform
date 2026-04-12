from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import UserProfile
from django.contrib.auth.models import User
from .permissions import *
from .models import *
from .forms import *
import re
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
import uuid
from django.urls import reverse
from django.conf import settings
from .utils import generate_signature
from django.core.mail import send_mail
from .recommendation import *
from django.db.models import Q, Sum, Count, F
from django.http import HttpResponse, JsonResponse
import pandas as pd
import base64
import json
import threading
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.db.models.functions import TruncMonth, TruncDay
from django.utils.timezone import now
from collections import defaultdict
from calendar import month_name, monthrange
from itertools import chain
from django.views.decorators.csrf import csrf_exempt
from django.db.models.functions import TruncDate

from django.contrib.auth import get_user_model
User = get_user_model()

def async_send_mail(subject, message, recipient_list):
    threading.Thread(
        target=send_mail,
        args=(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list),
        kwargs={"fail_silently": True},
    ).start()

def home(request):
    latest_products = Product.objects.order_by('-created_at')[:4]
    latest_categories = Category.objects.order_by('-created_at')[:3]

    context = {
        'products': latest_products,
        'categories': latest_categories
    }
    return render(request, 'home.html', context)

def about(request):
    return render(request, 'about.html')

def signup(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        phone = request.POST.get('phone')
        password = request.POST.get('password')  
        confirm_password = request.POST.get('confirm_password')
        role = request.POST.get('role')
        profile_image = request.FILES.get('profile_image')
        
        # password match validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('signup')
        
        # password length validation
        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return redirect('signup')
        
        # email format validation
        email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_regex, email):
            messages.error(request, "Invalid email format.")
            return redirect('signup')

        # phone validation need 10 digits
        if not phone.isdigit() or len(phone) != 10:
            messages.error(request, "Phone number must be 10 digits.")
            return redirect('signup')
        
        # image validation (.jpg, .jpeg, .png)
        if profile_image:
            allowed_extensions = ['jpg', 'jpeg', 'png']
            file_extension = profile_image.name.lower()

            if not any(file_extension.endswith(ext) for ext in allowed_extensions):
                messages.error(request, "Profile image must be a .jpg, .jpeg, or .png file.")
                return redirect('signup')

        # unique username and email validation
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect('signup')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect('signup')

        role_map = {
            'supplier': 'SUPPLIER',
            'customer': 'CUSTOMER',
            'delivery_personnel': 'DELIVERY'
        }

        if role not in role_map:
            messages.error(request, "Invalid role selected.")
            return redirect('signup')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        UserProfile.objects.create(
            user=user,
            role=role_map[role],
            profile_image=profile_image
        )

        messages.success(request, "Account created successfully. Please sign in.")
        return redirect('signin')

    return render(request, 'signup.html')

def signin(request):
    if request.method == 'POST':
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(
                request,
                username=user_obj.username,
                password=password
            )
        except User.DoesNotExist:
            user = None

        if user is None:
            messages.error(request, "Invalid email or password!")
            return redirect('signin')

        login(request, user)

        # SAFE UserProfile access
        try:
            profile = user.userprofile
        except UserProfile.DoesNotExist:
            messages.error(request, "User profile not found. Contact admin.")
            return redirect('signin')

        role = profile.role

        if role == 'CUSTOMER':
            return redirect('customer_dashboard')

        elif role == 'SUPPLIER':
            return redirect('supplier_dashboard')

        elif role == 'DELIVERY':
            # document check
            if DeliveryDocument.objects.filter(user=user).exists():
                return redirect('delivery_personnel_dashboard')
            else:
                return redirect('document_form')

        # final fallback
        messages.error(request, "Invalid user role.")
        return redirect('signin')

    return render(request, 'signin.html')

def signout(request):
    logout(request)
    return redirect('home')

def delivery_personnel_dashboard(request):
    orders = Order.objects.filter(
        delivery_person=request.user
    ).exclude(
        status__in=["Delivered", "Cancelled"]
    ).order_by("-created_at")

    return render(request, 'delivery_dashboard.html', {'orders': orders})

@login_required
@delivery_required
def delivery_history(request):

    orders = Order.objects.filter(
        delivery_person=request.user,
        status="Delivered"
    ).prefetch_related("items__product").order_by("-created_at")

    return render(request, "delivery_history.html", {"orders": orders})

@login_required
@customer_required
def customer_dashboard(request):

    query = request.GET.get('q')

    recommended_products = recommend_products_for_user(request.user)
    
    item_based_products = None

    last_view = ProductView.objects.filter(
        user=request.user
    ).order_by('-viewed_at').first()

    if last_view:
        item_based_products = get_item_based_recommendations(last_view.product_id)

    categories = Category.objects.all().order_by('-created_at')[:3]

    products = Product.objects.annotate(
        total_orders=Count('orderitem')
    ).filter(
        total_orders__gt=0
    ).order_by('-total_orders')[:4]

    productss = Product.objects.order_by('-created_at')[:4]

    latest_blogs = Blog.objects.order_by('-created_at')[:4]


    # SEARCH ALGORITHM
    search_results = None
    if query:
        search_results = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()


    context = {
        'recommended_products': recommended_products,
        'item_based_products': item_based_products,
        'categories': categories,
        'products': products,
        'productss': productss,
        'latest_blogs': latest_blogs,
        'search_results': search_results,
        'query': query
    }

    return render(request, 'customer_dashboard.html', context)  

def products_by_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    products = Product.objects.filter(category = category).annotate(
        avg_rating=Avg('reviews__rating'),
        rating_count=Count('reviews')
    ).order_by('-created_at')

    context = {
        'category': category,
        'products': products
    }

    return render(request, 'products_by_category.html', context)

@customer_required
def top_rated_products(request):
    products = Product.objects.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews', distinct=True)
    ).filter(
        review_count__gt=0
    ).order_by(
        '-avg_rating',
        '-review_count'
    )

    context = {
        'products': products
    }

    return render(request, 'top_rated_products.html', context)

@login_required
@supplier_required
def supplier_dashboard(request):
    products = Product.objects.filter(supplier = request.user).order_by('-created_at')[:4]
    blogs = Blog.objects.filter(supplier = request.user).order_by('-created_at')[:3]
    categories = Category.objects.all().order_by('-created_at')[:3]

    context = {
        'products': products,
        'blogs': blogs,
        'categories': categories
    }
    return render(request, 'supplier_dashboard.html', context)

@supplier_required
def supplier_profile(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = None
    context = {
        'profile': profile
    }
    return render(request, 'supplier_profile.html', context)

@supplier_required
def supplier_products_by_category(request, category_id):
    category = get_object_or_404(Category, id = category_id)

    products = Product.objects.filter(
        category = category,
        supplier = request.user
    ).order_by('-created_at')

    context = {
        'category': category,
        'products': products
    }

    return render(request, 'supplier_product_by_category.html', context)

@supplier_required
def supplier_product_reviews(request):
    supplier = request.user

    seven_days_ago = timezone.now() - timedelta(days=7)

    # Get Supplier products
    supplier_products = Product.objects.filter(supplier=supplier)

    # Reviews only from last 7 days
    reviews = ProductReview.objects.filter(
        product__in=supplier_products,
        created_at__gte=seven_days_ago  
    ).select_related(
        'product',
        'user'
    ).order_by('-created_at')

    context = {
        'reviews': reviews
    }

    return render(request, 'supplier_product_reviews.html', context)

@supplier_required
def edit_supplier_profile(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        profile_image = request.FILES.get('profile_image')

        # Update User fields
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()

        # Update UserProfile fields
        profile.phone = phone
        if profile_image:
            profile.profile_image = profile_image
        profile.save()

        messages.success(request, "Profile updated successfully!")
        return redirect('supplier_profile')

    context = {
        'profile': profile
    }
    return render(request, 'edit_supplier_profile.html', context)

@supplier_required
def supplier_category_list(request):
    categories = Category.objects.all().order_by('created_at')
    return render(request, 'category_list.html', {'categories': categories})

@supplier_required
def supplier_products(request):
    products = Product.objects.filter(supplier = request.user)
    return render(request, 'product_list.html', {'products': products})

@supplier_required
def add_product(request):
    form = ProductForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        product = form.save(commit=False)
        product.supplier = request.user
        product.save()
        return redirect('supplier_dashboard')

    return render(request, 'add_product.html', {
        'form': form
    })

@supplier_required
def edit_product(request, pk):
    product = get_object_or_404(
        Product,
        pk=pk,
        supplier=request.user
    )

    form = ProductForm(
        request.POST or None,
        request.FILES or None,
        instance=product
    )

    if form.is_valid():
        form.save()
        return redirect('supplier_dashboard')

    return render(request, 'edit_product.html', {
        'form': form,
        'product': product
    })

@supplier_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk = pk, supplier = request.user)
    product.delete()
    return redirect('supplier_dashboard')

@supplier_required
def supplier_blogs(request):
    blogs = Blog.objects.filter(supplier = request.user)
    return render(request, 'blog_list.html', {'blogs': blogs})

@supplier_required
def supplier_orders(request):

    supplier = request.user
    seven_days_ago = timezone.now() - timedelta(days=7)

    orders = OrderItem.objects.filter(
        product__supplier=supplier,
        order__created_at__gte=seven_days_ago
    ).select_related(
        "order",
        "product",
        "order__user"
    )

    # -------- FILTERS --------
    product_id = request.GET.get("product")
    city = request.GET.get("city")
    min_amount = request.GET.get("min_amount")
    max_amount = request.GET.get("max_amount")

    if product_id:
        orders = orders.filter(product__id=product_id)

    if city:
        orders = orders.filter(order__city__icontains=city)

    if min_amount:
        orders = orders.filter(order__amount__gte=min_amount)

    if max_amount:
        orders = orders.filter(order__amount__lte=max_amount)

    orders = orders.order_by("-order__created_at")

    supplier_products = (
        orders.values("product__id", "product__name")
        .distinct()
    )

    # DELIVERY USERS
    delivery_users = UserProfile.objects.filter(role="DELIVERY")

    context = {
        "orders": orders,
        "supplier_products": supplier_products,
        "delivery_users": delivery_users
    }

    return render(request, "supplier_ordered.html", context)

@supplier_required
def supplier_cancel_orders(request):
    supplier = request.user
    seven_days_ago = timezone.now() - timedelta(days=7)

    # Base queryset: last 7 days orders for this supplier
    base_orders = OrderItem.objects.filter(
        product__supplier=supplier,
        order__created_at__gte=seven_days_ago
    ).select_related(
        "order", "product", "order__user", "order__delivery_person"
    )

    # GET filters
    product_id = request.GET.get("product")
    city = request.GET.get("city")
    min_amount = request.GET.get("min_amount")
    max_amount = request.GET.get("max_amount")
    delivery_person_id = request.GET.get("delivery_person")  # optional filter for cancelled orders

    # Filter Cancelled orders
    cancelled_orders = base_orders.filter(order__status="Cancelled")
    if delivery_person_id:
        cancelled_orders = cancelled_orders.filter(order__delivery_person__id=delivery_person_id)

    # Filter other orders (Pending, Assigned, Delivered)
    other_orders = base_orders.filter(order__status__in=["Pending", "Delivered"])
    if product_id:
        other_orders = other_orders.filter(product__id=product_id)
    if city:
        other_orders = other_orders.filter(order__city__icontains=city)
    if min_amount:
        other_orders = other_orders.filter(order__amount__gte=min_amount)
    if max_amount:
        other_orders = other_orders.filter(order__amount__lte=max_amount)

    # Combine both querysets
    orders = list(chain(cancelled_orders, other_orders))
    orders.sort(key=lambda x: x.order.created_at, reverse=True)

    # Products for filter dropdown
    supplier_products = base_orders.values("product__id", "product__name").distinct()

    # Delivery users for assign dropdown
    delivery_users = UserProfile.objects.filter(role="DELIVERY")

    context = {
        "orders": orders,
        "supplier_products": supplier_products,
        "delivery_users": delivery_users,
    }

    return render(request, "supplier_cancel_ordered.html", context)

@supplier_required
@csrf_exempt
def assign_delivery(request, order_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            delivery_person_id = data.get("delivery_person_id")
            
            # Get order that belongs to this supplier
            order = Order.objects.get(id=order_id, items__product__supplier=request.user)
            
            # Get delivery person (UserProfile)
            delivery_person = UserProfile.objects.get(user__id=delivery_person_id, role="DELIVERY")
            
            # Assign delivery person
            order.delivery_person = delivery_person.user
            
            # Update order status if it was Cancelled or Pending
            if order.status in ["Cancelled", "Pending"]:
                order.status = "Assigned"
            
            order.save()
            
            return JsonResponse({"success": True})
        
        except UserProfile.DoesNotExist:
            return JsonResponse({"success": False, "message": "Delivery person not found"})
        except Order.DoesNotExist:
            return JsonResponse({"success": False, "message": "Order not found"})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})
    
    return JsonResponse({"success": False, "message": "Invalid request"})

@supplier_required
@require_POST
def assign_delivery_ajax(request):
    order_id = request.POST.get("order_id")
    delivery_person_id = request.POST.get("delivery_person_id")

    order = get_object_or_404(Order, id=order_id)
    delivery_user = get_object_or_404(User, id=delivery_person_id, userprofile__role='DELIVERY')

    # Assign the order
    order.delivery_person = delivery_user
    order.status = "Assigned"
    order.save(update_fields=["delivery_person", "status"])

    send_mail(
            subject="New Delivery Assigned",
            message=f"You have been assigned to deliver Order #{order.id}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[delivery_user.user.email],
            fail_silently=False
        )

    return JsonResponse({"success": True})

@supplier_required
def delivery_person_list(request):
    delivery_users = UserProfile.objects.filter(role='DELIVERY').select_related('user')

    delivery_persons = []
    for user_profile in delivery_users:
        try:
            documents = DeliveryDocument.objects.get(user=user_profile.user)
        except DeliveryDocument.DoesNotExist:
            documents = None

        # All orders for display
        orders = Order.objects.filter(delivery_person=user_profile.user)

        # Count only NOT delivered orders
        active_orders = orders.exclude(status='Delivered')

        delivery_persons.append({
            'profile': user_profile,
            'documents': documents,
            'orders': orders,
            'assigned_count': active_orders.count()
        })

    unassigned_orders = Order.objects.filter(
        delivery_person__isnull=True,
        status__in=['Paid', 'Pending']
    ).order_by('-created_at')

    return render(request, 'delivery_person_list.html', {
        'delivery_persons': delivery_persons,
        'unassigned_orders': unassigned_orders
    })

@supplier_required
def add_blog(request):  
    form = BlogForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        blog = form.save(commit=False)
        blog.supplier = request.user
        blog.save()
        return redirect('supplier_dashboard')
    return render(request, 'add_blog.html', {
        'form': form
    })

@supplier_required
def edit_blog(request, pk):
    blog = get_object_or_404(Blog, pk = pk, supplier = request.user)
    form = BlogForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        form.save()
        return redirect('supplier_dashboard')
    return render(request, 'edit_blog.html', {
        'form': form,
        'blog': blog
    })

@supplier_required
def delete_blog(request, pk):
    blog = get_object_or_404(Blog, pk = pk, supplier = request.user)
    blog.delete()
    return redirect('supplier_dashboard')

@customer_required
def customer_profile(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = None
    context = {
        'profile': profile
    }
    return render(request, 'customer_profile.html', context)

@customer_required
def edit_customer_profile(request):
    return render(request, 'edit_customer_profile.html')

@customer_required
def category_list_customer(request):
    categories = Category.objects.all().order_by('created_at')
    return render(request, 'category_list_customer.html', {'categories': categories})

@customer_required
def buy_product(request, product_id):

    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.select_related('user').order_by('-created_at')

    has_purchased = False

    if request.user.is_authenticated:
        has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            product_id=product,
            order__status="Delivered"  
        ).exists()

    if request.method == 'POST':
        size = request.POST.get('size')  # get the selected size
        # now save 'size' in cart model or use as needed
        print("Selected size:", size)

        if not has_purchased:
            return redirect('buy_product', product_id=product.id)

        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if rating:
            ProductReview.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={
                'rating': rating,
                'comment': comment
            }
        )
            
            pv, created = ProductView.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'time_spent': 0}
        )

        if not created:
            pv.time_spent += 1
            pv.save()
            
        return redirect('buy_product', product_id=product.id)

    context = {
        'product': product,
        'reviews': reviews,
        'has_purchased': has_purchased
    }

    return render(request, 'buy_product.html', context)

@customer_required
def all_products(request):
    products = (
        Product.objects
        .all()
        .annotate(avg_rating=Avg('reviews__rating'))
        .order_by('-created_at')
    )

    return render(request, 'all_products.html', {
        'products': products
    })

@customer_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    size = request.POST.get('size')
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product, size = size)

    if not item_created:
        cart_item.quantity += 1
    else:
        cart_item.quantity = 1
    cart_item.save()
    
    # Reduce product stock < 5
    if product.stock > 0:
        product.stock -= 1
        product.save()
    
    # Send email if stock < 5
    if product.stock < 5:
        try:
            supplier_profile = UserProfile.objects.get(user = product.supplier)
            if supplier_profile.role == "SUPPLIER":
                send_mail(
                    subject="Low Stock Alert",
                    message=f"""
                        Hello {product.supplier.username},

                        Your product "{product.name}" is running low in stock.

                        Remaining stock: {product.stock}

                        Please restock the product soon.

                        Thank you.
                        """,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[product.supplier.email],
                    fail_silently=True,
                )
        except UserProfile.DoesNotExist:
            pass

    return redirect('cart_page')

@customer_required
def cart_page(request):
    # Get or create cart for the user
    cart, created = Cart.objects.get_or_create(user=request.user)

    # If cart exists, fetch items
    items = cart.items.all() if cart else []

    # Calculate grand total (as property in Cart model)
    # Make sure your Cart model has grand_total as a @property
    grand_total = cart.grand_total if cart else 0

    return render(request, 'cart.html', {
        'cart': cart,
        'items': items,
        'grand_total': grand_total
    })

@customer_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product = item.product

    # Update or remove ProductView
    pv = ProductView.objects.filter(user=request.user, product=product).first()

    if pv:
        if pv.time_spent > 1:
            pv.time_spent -= 1   
            pv.save()
        else:
            pv.delete()        

    # Delete cart item
    item.delete()

    return redirect('cart_page')

@customer_required
def checkout(request):
    cart = Cart.objects.filter(user = request.user).first()

    if not cart or not cart.items.exists():
        return redirect('cart_page')
    
    addresses = Address.objects.filter(user = request.user)

    total_amount = cart.grand_total

    return render(request, 'esewa_checkout.html', {
        'cart': cart,
        'total_amount': total_amount,
        'addresses': addresses
     })

@login_required
@customer_required
def process_payment(request):
    if request.method != "POST":
        return redirect("checkout")

    cart = Cart.objects.filter(user=request.user).first()
    if not cart or not cart.items.exists():
        return redirect("cart_page")
    
    address_id = request.POST.get('address_id')

    if not address_id:
        messages.error(request, "Please select a delivery address.")
        return redirect('checkout')
    
    address = Address.objects.filter(id = address_id, user = request.user).first()

    if not address:
        messages.error(request, "Invalid address selected.")
        return redirect('checkout')

    total_amount = cart.grand_total
    payment_type = request.POST.get("payment_type")

    transaction_uuid = str(uuid.uuid4())

    order = Order.objects.create(
        user=request.user,
        full_name=request.POST.get("name"),
        email=request.POST.get("email"),
        phone=request.POST.get("phone"),
        address=address,
        city=request.POST.get("city"),
        country="Nepal",
        amount=total_amount,
        payment_type=payment_type,
        transaction_uuid=transaction_uuid,
        status="Pending"
    )

    for cart_item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            quantity=cart_item.quantity,
            price=cart_item.product.price  # <-- assign price here
        )

    request.session["current_order_id"] = order.id

    # CASH ON DELIVERY 
    if payment_type == "cod":
        cart.items.all().delete()
        return render(request, "payment_success.html", {"order": order})

    # ESEWA (FIXED 
    if payment_type == "esewa":
        product_code = getattr(settings, "ESEWA_PRODUCT_CODE", "EPAYTEST")
        secret_key = getattr(settings, "ESEWA_SECRET_KEY", "")

        signature = generate_signature(
            total_amount,
            transaction_uuid,
            product_code,
            secret_key
        )

        context = {
            "order": order,
            "total_amount": total_amount,
            "transaction_uuid": transaction_uuid,
            "product_code": product_code,
            "signature": signature,
            "success_url": request.build_absolute_uri(reverse("payment_success")),
            "failure_url": request.build_absolute_uri(reverse("payment_failed")),
        }

        return render(request, "esewa_payment.html", context)

    return redirect("checkout")

def payment_success(request):
    encoded_data = request.GET.get("data")

    if not encoded_data:
        return redirect("customer_dashboard")

    try:
        decoded_data = base64.b64decode(encoded_data).decode("utf-8")
        payment_data = json.loads(decoded_data)

        transaction_uuid = payment_data.get("transaction_uuid")
        status = payment_data.get("status")

        order = get_object_or_404(Order, transaction_uuid=transaction_uuid)

        if status == "COMPLETE" and order.status != "Paid":

            # DATABASE OPERATIONS
            with transaction.atomic():

                order.status = "Paid"
                order.save(update_fields=["status"])

                for item in order.items.all():
                    product = item.product

                    if product.stock >= item.quantity:
                        product.stock -= item.quantity
                        product.save(update_fields=["stock"])
                    else:
                        print("Not enough stock for:", product.name)

                # Clear cart
                Cart.objects.filter(user=order.user).delete()

            # SEND EMAIL (OUTSIDE TRANSACTION)
            product_details = ""
            for item in order.items.all():
                product_details += f"{item.product.name} (Qty: {item.quantity}) - Rs.{item.price}\n"

            customer_message = f"""
Hello {order.full_name},

Your payment was successful!

Order ID: {order.id}

Products:
{product_details}

Total Paid: Rs.{order.amount}

Thank you for shopping with us!
"""

            send_mail(
                subject="Order Confirmation - Payment Successful",
                message=customer_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.email],
                fail_silently=False,
            )

        return render(request, "payment_success.html", {"order": order})

    except Exception as e:
        print("Payment Success Error:", e)
        return redirect("customer_dashboard")

@customer_required
def payment_fail(request):
    order_id = request.session.get('order_id')
    order = get_object_or_404(Order, id=order_id)

    order.status = "Failed"
    order.save()

    return render(request, 'payment_fail.html', {'order': order})

def customer_blog_list(request):
    blogs = Blog.objects.all().order_by('-created_at')
    return render(request, 'customer_blog_list.html', {'blogs': blogs})

def customer_blog_detail(request, blog_id):
    blog = Blog.objects.get(id = blog_id)
    return render(request, 'customer_blog_detail.html', {'blog': blog})

@delivery_required
def document_form(request):
    if request.user.userprofile.role != 'DELIVERY':
        return redirect('signin')

    try:
        document = DeliveryDocument.objects.get(user=request.user)
        form = DeliveryDocumentForm(instance=document)
    except DeliveryDocument.DoesNotExist:
        document = None
        initial_data = {
            'full_name': f"{request.user.first_name} {request.user.last_name}",
            'phone': request.user.userprofile.phone,
        }
        form = DeliveryDocumentForm(initial=initial_data)

    if request.method == 'POST':
        if document:
            form = DeliveryDocumentForm(request.POST, request.FILES, instance=document)
        else:
            form = DeliveryDocumentForm(request.POST, request.FILES)

        if form.is_valid():
            doc = form.save(commit=False)
            doc.user = request.user
            doc.save()
            return redirect('delivery_personnel_dashboard')
        else:
            print("FORM ERRORS:", form.errors)  # DEBUG

    return render(request, 'document_form.html', {'form': form})

@delivery_required
def document_view(request):
    try:
        document = DeliveryDocument.objects.get(user=request.user)
    except DeliveryDocument.DoesNotExist:
        messages.error(request, "No document found. Please upload first.")
        return redirect('document_form')

    return render(request, 'document_view.html', {
        'document': document
    })

@delivery_required
def delivery_profile(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = None
    context = {
        'profile': profile
    }
    return render(request, 'delivery_profile.html', context)

@delivery_required
def edit_delivery_profile(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        profile_image = request.FILES.get('profile_image')

        # Update User fields
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()

        # Update UserProfile fields
        profile.phone = phone
        if profile_image:
            profile.profile_image = profile_image
        profile.save()

        messages.success(request, "Profile updated successfully!")
        return redirect('delivery_profile')

    context = {
        'profile': profile
    }
    return render(request, 'edit_delivery_profile.html', context)

@delivery_required
def document_edit(request):
    document = DeliveryDocument.objects.get(user=request.user)

    if request.method == 'POST':
        form = DeliveryDocumentForm(
            request.POST,
            request.FILES,
            instance=document
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Documents updated successfully.")
            return redirect('document_view')
    else:
        form = DeliveryDocumentForm(instance=document)

    return render(request, 'document_edit.html', {'form': form})

def contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        ContactMessage.objects.create(
            name = name,
            email = email,
            phone = phone,
            subject = subject,
            message = message,
        )
        messages.success(request, "Your message has been sent successfully.")
        return redirect('contnact')
    return render(request, 'contact.html')

def is_delivery_user(user):
    try:
        return user.userprofile.role == 'DELIVERY'
    except:
        return False

@delivery_required
def delivery_order_list(request):
    if not is_delivery_user(request.user):
        return redirect('signin')

    orders = Order.objects.filter(
        delivery_person=request.user
    ).exclude(
        status__in=['Delivered', 'Cancelled']
    ).order_by('-created_at')

    return render(request, 'order_list.html', {
        'orders': orders
    })

@delivery_required
def delivery_order_detail(request, order_id):
    order = get_object_or_404(Order, id = order_id)

    # security: only assigned delivery person can see
    if order.delivery_person != request.user:
        return redirect('delivery_order_list')

    return render(request, 'order_detail.html', {
        'order': order
    })

@delivery_required
def delivery_accept(request, order_id):
    if not is_delivery_user(request.user):
        return redirect('signin')
    
    order = get_object_or_404(Order, id = order_id)
    order.delivery_person = request.user
    order.status = 'Assigned'
    order.save()

    product_list = "\n".join([
        f"{item.product.name} (x{item.quantity})"
        for item in order.items.all()
    ])

    send_mail(
        subject="Your Order is Out for Delivery",
        message=f"""
            Hello {order.full_name},

            Your order #{order.id} has been assigned to a delivery person.

            Delivery Person Details:
            Name: {request.user.get_full_name() or request.user.username}
            Phone: {request.user.userprofile.phone}

            Order Items:
            {product_list}

            Delivery Address:
            {order.address}, {order.city}, {order.country}

            Thank you for shopping with Shop Sphere!
            """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[order.email],
                    fail_silently=False,
                )
    
    return redirect('delivery_order_list')

@delivery_required
def delivery_cancel(request, order_id):
    if not is_delivery_user(request.user):
        return redirect('signin')
    
    order = get_object_or_404(Order, id = order_id)
    order.status = 'Cancelled'
    order.save()

    send_mail(
        subject="Order Delivery Cancelled",
        message=f"""
        Hello {order.full_name},

        Your order #{order.id} delivery has been cancelled by the delivery person.

        Don't worry! We are reassigning a new delivery person.

        You will receive your order soon.

        If you have any issues, please contact our support team.

        Thank you for shopping with Shop Sphere!
                """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[order.email],
                    fail_silently=False,
                )

    return redirect('delivery_order_list')

@delivery_required
def delivery_mark_delivered(request, order_id):

    order = get_object_or_404(Order, id=order_id)

    # security check
    if order.delivery_person != request.user:
        return redirect('delivery_order_list')

    if request.method == "POST":
        proof = request.FILES.get('delivery_proof')

        if proof:
            order.delivery_proof = proof

        order.status = "Delivered"
        order.save()

        # ─────────────────────────────────────
        # EMAIL NOTIFICATION
        # ─────────────────────────────────────

        customer_email = order.user.email if order.user else None

        supplier_email_list = OrderItem.objects.filter(
            order=order
        ).values_list('product__supplier__email', flat=True).distinct()

        subject = "Order Delivered Successfully 🎉"

        message = f"""
            Hi,

            Your order (ID: {order.id}) has been successfully delivered.

            Thank you for using our platform.

            Regards,
            Delivery Team
        """

        # send email to customer
        if customer_email:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [customer_email],
                fail_silently=True,
            )

        # send email to suppliers
        for email in supplier_email_list:
            if email:
                send_mail(
                    subject,
                    f"""
                        Hi Supplier,

                        Your product from Order ID: {order.id} has been successfully delivered to the customer.

                        Regards,
                        Delivery System
                    """,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=True,
                )

        return redirect('delivery_order_list')

    return redirect('order_detail', order_id=order.id)

@login_required
@customer_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Category-based related products
    category_related_products = Product.objects.filter(
        category=product.category
    ).exclude(
        id=product.id
    )[:8]

    # Content-based recommendations
    recommended_products = get_similar_products(product.id)

    # Item-based collaborative filtering
    collaborative_products = get_item_based_recommendations(product.id)

    if request.method == 'POST' and request.is_ajax():
        time_spent = int(request.POST.get('time_spent', 0))

        pv, created = ProductView.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'time_spent': time_spent}
        )

        if not created:
            pv.time_spent += time_spent
            pv.save()

        return JsonResponse({'status': 'success'})

    return render(request, 'product_detail.html', {
        'product': product,
        'category_related_products': category_related_products,
        'recommended_products': recommended_products,
        'collaborative_products': collaborative_products,   # NEW
    })

@login_required
@customer_required
def search_products(request):
    query = request.GET.get('q', '')

    search_results = Product.objects.none()
    category_related_products = Product.objects.none()
    related_products = Product.objects.none()

    if query:
        # Save search history if user is logged in
        if request.user.is_authenticated:
            SearchHistory.objects.create(user=request.user, query=query)

        # Direct search matches
        search_results = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query) |
            Q(supplier__username__icontains=query)
        ).select_related('category').distinct()

        # Category-based related products
        categories = search_results.values_list('category_id', flat=True)

        if categories:
            category_related_products = Product.objects.filter(
                category_id__in=categories
            ).exclude(
                id__in=search_results.values_list('id', flat=True)
            ).distinct()[:12]

        # Content-based recommendations 
        related_products = get_similar_products_by_text(query)

    return render(request, 'search_results.html', {
        'query': query,
        'search_results': search_results,
        'category_related_products': category_related_products,
        'related_products': related_products,
    })

@customer_required
def add_address(request):
    if request.method == 'POST':
        full_address = request.POST.get('full_address')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')

        Address.objects.create(
            user = request.user,
            full_address = full_address,
            latitude = latitude,
            longitude = longitude
        )
        return redirect('add_address')
    return render(request, 'add_address.html')

def customer_permission(request):
    return render(request, "customer_permissions.html")

def supplier_permission(request):
    return render(request, "supplier_permissions.html")

@login_required
@supplier_required
def supplier_earning(request):

    supplier = request.user

    # Base queryset (only supplier products)
    order_items = OrderItem.objects.filter(
        product__supplier=supplier
    ).select_related("order", "product")

    # FILTERS

    product_id = request.GET.get("product")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    status = request.GET.get("status")

    if product_id:
        order_items = order_items.filter(product__id=product_id)

    if date_from:
        order_items = order_items.filter(order__created_at__date__gte=date_from)

    if date_to:
        order_items = order_items.filter(order__created_at__date__lte=date_to)

    if status:
        order_items = order_items.filter(order__status=status)

    # SUMMARY CALCULATIONS 

    # Total orders (distinct orders)
    total_orders = order_items.values("order").distinct().count()

    # Units sold
    total_units = order_items.aggregate(
        total=Sum("quantity")
    )["total"] or 0

    # Total earnings (Paid + Delivered)
    total_earnings = order_items.filter(
        order__status__in=["Paid", "Delivered"]
    ).aggregate(
        total=Sum(F("quantity") * F("product__price"))
    )["total"] or 0

    # Pending earnings
    pending_earnings = order_items.filter(
        order__status="Pending"
    ).aggregate(
        total=Sum(F("quantity") * F("product__price"))
    )["total"] or 0

    # PER PRODUCT EARNINGS 

    product_data = order_items.values(
        "product__id",
        "product__name",
        "product__price"
    ).annotate(
        units_sold=Sum("quantity"),

        total_revenue=Sum(F("quantity") * F("product__price")),

        pending_amount=Sum(
            F("quantity") * F("product__price"),
            filter=Q(order__status="Pending")
        ),

        delivered_amount=Sum(
            F("quantity") * F("product__price"),
            filter=Q(order__status="Delivered")
        ),

        cancelled_amount=Sum(
            F("quantity") * F("product__price"),
            filter=Q(order__status="Cancelled")
        ),
    )

    product_earnings = []

    for row in product_data:
        net_earned = (row["total_revenue"] or 0) - (row["cancelled_amount"] or 0)

        product_earnings.append({
            "product_name": row["product__name"],
            "unit_price": row["product__price"],
            "units_sold": row["units_sold"] or 0,
            "total_revenue": row["total_revenue"] or 0,
            "pending_amount": row["pending_amount"] or 0,
            "delivered_amount": row["delivered_amount"] or 0,
            "cancelled_amount": row["cancelled_amount"] or 0,
            "net_earned": net_earned
        })

    # TOP PRODUCTS 

    max_revenue = max(
        [p["net_earned"] for p in product_earnings],
        default=0
    )

    top_products = []

    for p in sorted(product_earnings, key=lambda x: x["net_earned"], reverse=True)[:5]:
        pct = (p["net_earned"] / max_revenue * 100) if max_revenue > 0 else 0
        p["revenue_pct"] = round(pct, 2)
        top_products.append(p)

    # STATUS BREAKDOWN

    status_breakdown = {
        "paid_count": order_items.filter(order__status__in=["Paid", "Delivered"])
                                  .values("order").distinct().count(),
        "pending_count": order_items.filter(order__status="Pending")
                                    .values("order").distinct().count(),
        "cancelled_count": order_items.filter(order__status="Cancelled")
                                      .values("order").distinct().count(),
        "delivered_count": order_items.filter(order__status="Delivered")
                                      .values("order").distinct().count(),                             
    }

    supplier_products = Product.objects.filter(supplier=supplier)

    context = {
        "total_orders": total_orders,
        "total_units": total_units,
        "total_earnings": total_earnings,
        "pending_earnings": pending_earnings,
        "product_earnings": product_earnings,
        "top_products": top_products,
        "status_breakdown": status_breakdown,
        "supplier_products": supplier_products,
    }

    return render(request, "supplier_earnings.html", context)

@login_required
@customer_required
def customer_spending(request):

    user = request.user

    # Base queryset (only this customer's orders)
    order_items = OrderItem.objects.filter(
        order__user=user
    ).select_related("order", "product")

    # FILTERS

    category_id = request.GET.get("category")
    status = request.GET.get("status")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    if category_id:
        order_items = order_items.filter(product__category__id=category_id)

    if status:
        order_items = order_items.filter(order__status=status)

    if date_from:
        order_items = order_items.filter(order__created_at__date__gte=date_from)

    if date_to:
        order_items = order_items.filter(order__created_at__date__lte=date_to)

    # SUMMARY CARDS

    # Total orders
    total_orders = order_items.values("order").distinct().count()

    # Total items bought
    total_items = order_items.aggregate(
        total=Sum("quantity")
    )["total"] or 0

    # Total spent (Paid + Delivered only)
    total_spent = order_items.filter(
        order__status__in=["Paid", "Delivered"]
    ).aggregate(
        total=Sum(F("quantity") * F("product__price"))
    )["total"] or 0

    # Cancelled count
    cancelled_count = order_items.filter(
        order__status="Cancelled"
    ).values("order").distinct().count()

    # TABLE DATA 

    product_spending = []

    for item in order_items:
        total_paid = item.quantity * item.product.price

        product_spending.append({
            "product_name": item.product.name,
            "image": item.product.image,
            "category": item.product.category.name if item.product.category else "N/A",
            "quantity": item.quantity,
            "unit_price": item.product.price,
            "total_paid": total_paid,
            "status": item.order.status,
            "date": item.order.created_at,
        })

    # TOP ITEMS 

    confirmed_items = order_items.filter(
        order__status__in=["Paid", "Delivered"]
    )

    item_totals = confirmed_items.values(
        "product__name"
    ).annotate(
        total_paid=Sum(F("quantity") * F("product__price"))
    )

    max_spend = max(
        [i["total_paid"] for i in item_totals],
        default=0
    )

    top_items = []

    for item in item_totals:
        pct = (item["total_paid"] / max_spend * 100) if max_spend > 0 else 0

        top_items.append({
            "product_name": item["product__name"],
            "total_paid": item["total_paid"],
            "spend_pct": round(pct, 2)
        })

    # Sort highest first
    top_items = sorted(top_items, key=lambda x: x["total_paid"], reverse=True)[:5]

    # CATEGORY BREAKDOWN

    category_data = confirmed_items.values(
        "product__category__name"
    ).annotate(
        total=Sum(F("quantity") * F("product__price"))
    )

    max_total = total_spent if total_spent else 1

    colors = ["#27ae60", "#2980b9", "#e67e22", "#8e44ad", "#e74c3c", "#16a085"]

    category_breakdown = []
    for index, cat in enumerate(category_data):
        pct = (cat["total"] / max_total) * 100 if max_total > 0 else 0

        category_breakdown.append({
            "name": cat["product__category__name"] or "Uncategorized",
            "total": cat["total"],
            "pct": round(pct, 1),
            "color": colors[index % len(colors)]
        })

    # CATEGORY DROPDOWN 

    categories = Category.objects.all()

    paginator = Paginator(product_spending, 10)  # 10 rows per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "total_spent": total_spent,
        "total_orders": total_orders,
        "total_items": total_items,
        "cancelled_count": cancelled_count,
        "product_spending": product_spending,
        "top_items": top_items,
        "category_breakdown": category_breakdown,
        "categories": categories,
        "page_obj": page_obj
    }

    return render(request, "customer_spending.html", context)

@login_required
@customer_required
def customer_order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    # Apply filters
    status = request.GET.get('status')
    payment = request.GET.get('payment')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if status:
        orders = orders.filter(status=status)
    if payment:
        orders = orders.filter(payment_type=payment)
    if date_from:
        orders = orders.filter(created_at__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__lte=date_to)

    # Pagination
    paginator = Paginator(orders, 10)  # 10 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "delivered_count": orders.filter(status='Delivered').count(),
        "pending_count": orders.filter(status='Pending').count(),
        "cancelled_count": orders.filter(status='Cancelled').count(),
        "total_orders": orders.count(),
        # Keep any other data you need
    }
    return render(request, "customer_order_history.html", context)

def guidelines(request):
    return render(request, 'guideline.html')

def customer_guidelines(request):
    form = ContactMessageForm()

    if request.method == "POST":
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            form.save()
            form = ContactMessageForm()  

    return render(request, 'customer_guideline.html', {'form': form})

def supplier_guidelines(request):
    form = ContactMessageForm()

    if request.method == "POST":
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            form.save()
            form = ContactMessageForm()  
    return render(request, 'supplier_guideline.html', {'form': form})

def delivery_guidelines(request):
    form = ContactMessageForm()

    if request.method == "POST":
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            form.save()
            form = ContactMessageForm()  
    return render(request, 'delivery_guideline.html', {'form': form})

@customer_required
def customer_graph(request):
    user = request.user

    orders_qs = Order.objects.filter(user=user)\
        .prefetch_related('items__product__category')

    total_orders = orders_qs.count()

    # -------------------------
    #  PANDAS DATAFRAME
    # -------------------------
    orders = orders_qs.filter(status__in=["Paid", "Delivered"])\
        .values('created_at', 'amount')

    df = pd.DataFrame(orders)

    # DEFAULTS
    current_month_total = 0
    last_month_total = 0
    highest_month_total = 0
    highest_month_name = ""
    all_months_data = []
    monthly_labels = []
    monthly_totals = []

    current_date = now()
    current_month = current_date.month
    current_year = current_date.year

    last_month_date = current_date - timedelta(days=30)
    last_month = last_month_date.month
    last_month_year = last_month_date.year

    if not df.empty:
        df['created_at'] = pd.to_datetime(df['created_at'])
        df['year'] = df['created_at'].dt.year
        df['month'] = df['created_at'].dt.month
        df['day'] = df['created_at'].dt.day

        # -------------------------
        # CURRENT & LAST MONTH TOTAL
        # -------------------------
        current_df = df[(df['year']==current_year)&(df['month']==current_month)]
        last_df = df[(df['year']==last_month_year)&(df['month']==last_month)]

        current_month_total = float(current_df['amount'].sum())
        last_month_total = float(last_df['amount'].sum())

        # -------------------------
        # HIGHEST MONTH
        # -------------------------
        monthly_group = df.groupby(['year','month'])['amount'].sum().reset_index()

        if not monthly_group.empty:
            top = monthly_group.sort_values(by='amount', ascending=False).iloc[0]
            highest_month_total = float(top['amount'])
            highest_month_name = month_name[int(top['month'])]

        # -------------------------
        # ALL MONTHS DAILY DATA
        # -------------------------
        grouped = df.groupby(['year','month'])

        for (year, month), group in grouped:
            days_in_month = group['created_at'].dt.days_in_month.iloc[0]
            daily = group.groupby('day')['amount'].sum()

            days = [0]*days_in_month
            for d,val in daily.items():
                days[d-1] = float(val)

            all_months_data.append({
                "label": f"{month_name[month]} {year}",
                "days": days
            })

        # -------------------------
        # MONTHLY (FULL YEAR)
        # -------------------------
        yearly = df[df['year']==current_year]
        monthly = yearly.groupby('month')['amount'].sum()

        monthly_labels = [month_name[i][:3] for i in range(1,13)]
        monthly_totals = [float(monthly.get(i,0)) for i in range(1,13)]

    # -------------------------
    # CATEGORY + PRODUCT
    # -------------------------
    category_map = defaultdict(float)
    product_map = defaultdict(float)

    for order in orders_qs.filter(status__in=["Paid","Delivered"]):
        for item in order.items.all():
            total = float(item.price)*item.quantity

            category_map[item.product.category.name] += total
            product_map[item.product.name] += total

    total_spent = sum(category_map.values())

    category_breakdown = []
    for name,total in category_map.items():
        pct = (total/total_spent*100) if total_spent else 0

        category_breakdown.append({
            'name':name,
            'total':total,
            'pct':round(pct,1),
            'color': "#%06x" % (hash(name)&0xFFFFFF)
        })

    top_products = []
    for name,total in sorted(product_map.items(), key=lambda x:x[1], reverse=True)[:5]:
        pct = (total/total_spent*100) if total_spent else 0
        top_products.append({'name':name,'total':total,'pct':round(pct,1)})

    recent_orders = orders_qs.order_by('-created_at')[:5]

    # -------------------------
    # CONTEXT
    # -------------------------
    context = {
        'total_orders': total_orders,
        'current_month_total': current_month_total,
        'last_month_total': last_month_total,
        'highest_month_total': highest_month_total,
        'highest_month_name': highest_month_name,
        'current_month_name': month_name[current_month],
        'last_month_name': month_name[last_month],

        'all_months_data': json.dumps(all_months_data),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_totals': json.dumps(monthly_totals),

        'category_breakdown': category_breakdown,
        'top_products': top_products,
        'recent_orders': recent_orders,
    }

    return render(request, 'customer_graph.html', context)

@login_required
def supplier_graph(request):
    user = request.user

    # PRODUCTS
    products = Product.objects.filter(supplier=user)
    total_products = products.count()
    active_products = products.filter(is_active=True).count()

    # ORDER ITEMS
    items_qs = OrderItem.objects.filter(product__supplier=user)\
        .select_related('order', 'product__category')

    # ORDERS
    orders = Order.objects.filter(items__in=items_qs).distinct()

    # -------------------------
    # PANDAS DATAFRAME
    # -------------------------
    data = items_qs.filter(order__status__in=["Paid", "Delivered"])\
        .values('order__created_at', 'price', 'quantity')

    df = pd.DataFrame(data)

    # DEFAULTS
    current_month_revenue = 0
    last_month_revenue = 0
    best_month_revenue = 0
    best_month_name = ""
    all_months_data = []
    monthly_labels = []
    monthly_totals = []

    now_date = now()
    current_month = now_date.month
    current_year = now_date.year

    last_month_date = now_date - timedelta(days=30)
    last_month = last_month_date.month
    last_month_year = last_month_date.year

    if not df.empty:
        df['created_at'] = pd.to_datetime(df['order__created_at'])
        df['amount'] = df['price'] * df['quantity']
        df['year'] = df['created_at'].dt.year
        df['month'] = df['created_at'].dt.month
        df['day'] = df['created_at'].dt.day

        # CURRENT & LAST
        current_df = df[(df['year']==current_year)&(df['month']==current_month)]
        last_df = df[(df['year']==last_month_year)&(df['month']==last_month)]

        current_month_revenue = float(current_df['amount'].sum())
        last_month_revenue = float(last_df['amount'].sum())

        # TREND
        def trend(c, p):
            if p == 0: return 100 if c > 0 else 0
            return ((c-p)/p)*100

        revenue_trend = trend(current_month_revenue, last_month_revenue)

        # MONTHLY GROUP
        monthly_group = df.groupby(['year','month'])['amount'].sum().reset_index()

        if not monthly_group.empty:
            top = monthly_group.sort_values(by='amount', ascending=False).iloc[0]
            best_month_revenue = float(top['amount'])
            best_month_name = month_name[int(top['month'])]

        # DAILY CHART
        for (y,m), group in df.groupby(['year','month']):
            days_in_month = group['created_at'].dt.days_in_month.iloc[0]
            daily = group.groupby('day')['amount'].sum()

            days = [0]*days_in_month
            for d,v in daily.items():
                days[d-1] = float(v)

            all_months_data.append({
                "label": f"{month_name[m]} {y}",
                "days": days
            })

        # YEARLY
        yearly = df[df['year']==current_year]
        monthly = yearly.groupby('month')['amount'].sum()

        monthly_labels = [month_name[i][:3] for i in range(1,13)]
        monthly_totals = [float(monthly.get(i,0)) for i in range(1,13)]

    else:
        revenue_trend = 0

    # ORDERS COUNT
    current_month_orders = orders.filter(
        created_at__year=current_year,
        created_at__month=current_month
    ).count()

    last_month_orders = orders.filter(
        created_at__year=last_month_year,
        created_at__month=last_month
    ).count()

    def trend(c,p):
        if p == 0: return 100 if c > 0 else 0
        return ((c-p)/p)*100

    orders_trend = trend(current_month_orders, last_month_orders)

    # -------------------------
    # CATEGORY + PRODUCT
    # -------------------------
    category_map = defaultdict(float)
    product_map = defaultdict(lambda: {"total":0,"qty":0})

    for item in items_qs.filter(order__status__in=["Paid","Delivered"]):
        total = float(item.price)*item.quantity

        category_map[item.product.category.name] += total
        product_map[item.product.name]["total"] += total
        product_map[item.product.name]["qty"] += item.quantity

    total_sales = sum(category_map.values()) or 1

    category_breakdown = []
    for name,total in category_map.items():
        pct = total/total_sales*100
        category_breakdown.append({
            "name":name,
            "total":total,
            "pct":round(pct,1),
            "color":"#%06x"%(hash(name)&0xFFFFFF)
        })

    top_products = []
    for name,data in sorted(product_map.items(), key=lambda x:x[1]["total"], reverse=True)[:5]:
        pct = data["total"]/total_sales*100
        top_products.append({
            "name":name,
            "total":data["total"],
            "qty_sold":data["qty"],
            "pct":round(pct,1)
        })

    low_stock_products = products.filter(stock__lte=5)
    recent_orders = orders.order_by('-created_at')[:5]

    context = {
        "current_month_revenue": current_month_revenue,
        "last_month_name": month_name[last_month],
        "current_month_name": month_name[current_month],
        "current_month_orders": current_month_orders,
        "revenue_trend": revenue_trend,
        "orders_trend": orders_trend,
        "total_products": total_products,
        "active_products": active_products,
        "best_month_revenue": best_month_revenue,
        "best_month_name": best_month_name,

        "recent_orders": recent_orders,
        "top_products": top_products,
        "category_breakdown": category_breakdown,
        "low_stock_products": low_stock_products,

        "all_months_data": json.dumps(all_months_data),
        "monthly_labels": json.dumps(monthly_labels),
        "monthly_totals": json.dumps(monthly_totals),
    }

    return render(request, "supplier_graph.html", context)

def sales_dashboard(request):
    #  Metrics
    paid_orders = Order.objects.filter(status__in=['Paid', 'Delivered'])

    total_revenue = paid_orders.aggregate(total=Sum('amount'))['total'] or 0
    total_orders  = paid_orders.count()
    avg_review    = ProductReview.objects.aggregate(avg=Avg('rating'))['avg'] or 0
    total_supplier_products = Product.objects.filter(is_active=True).count()
    active_customers = paid_orders.values('user').distinct().count()

    # Period filter (default 30d) 
    period = request.GET.get('period', '30d')
    days_map = {'7d': 7, '30d': 30, '90d': 90, '1y': 365}
    days = days_map.get(period, 30)
    since = timezone.now() - timedelta(days=days)

    period_orders = paid_orders.filter(created_at__gte=since)

    # Line chart: daily revenue + orders 
    daily = (
        period_orders
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(rev=Sum('amount'), cnt=Count('id'))
        .order_by('day')
    )

    line_labels  = [str(d['day']) for d in daily]
    line_revenue = [float(d['rev']) for d in daily]
    line_orders  = [d['cnt'] for d in daily]

    # Donut chart: revenue by category 
    cat_data = (
        OrderItem.objects
        .filter(order__in=period_orders)
        .values('product__category__name')
        .annotate(total=Sum('price'))
        .order_by('-total')
    )

    donut_categories = [c['product__category__name'] or 'Uncategorized' for c in cat_data]
    donut_sales      = [float(c['total']) for c in cat_data]

    # Review distribution 
    review_dist = (
        ProductReview.objects
        .values('rating')
        .annotate(count=Count('id'))
        .order_by('rating')
    )
    review_labels = [str(r['rating']) + '★' for r in review_dist]
    review_counts = [r['count'] for r in review_dist]

    # Top supplier products 
    top_products = (
        OrderItem.objects
        .filter(order__in=period_orders)
        .values(
            'product__name',
            'product__supplier__username',
            'product__is_active'
        )
        .annotate(units=Sum('quantity'))
        .order_by('-units')[:10]
    )

    context = {
        'metrics': {
            'total_revenue':           total_revenue,
            'total_orders':            total_orders,
            'avg_review':              round(avg_review, 1),
            'total_supplier_products': total_supplier_products,
            'active_customers':        active_customers,
        },
        'line_chart': {
            'labels':  json.dumps(line_labels),
            'revenue': json.dumps(line_revenue),
            'orders':  json.dumps(line_orders),
        },
        'donut_chart': {
            'categories': json.dumps(donut_categories),
            'sales':      json.dumps(donut_sales),
        },
        'review_chart': {
            'labels': json.dumps(review_labels),
            'counts': json.dumps(review_counts),
        },
        'top_products': top_products,
        'active_period': period,
    }

    return render(request, 'admin/index.html', context)

