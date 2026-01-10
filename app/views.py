from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import UserProfile
from django.contrib.auth.models import User
from .models import *
from .forms import *
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
import uuid
from django.urls import reverse
from decimal import Decimal
from django.conf import settings
from .utils import generate_signature

from django.contrib.auth import get_user_model
User = get_user_model()

# Create your views here.
def dashboard(request):
    return render(request, 'dashboard.html')

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
        password = request.POST.get('password')  # ✅ FIXED
        confirm_password = request.POST.get('confirm_password')
        role = request.POST.get('role')
        profile_image = request.FILES.get('profile_image')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('signup')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect('signup')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect('signup')

        if role not in ['supplier', 'customer', 'delivery_personnel']:
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
            role=role,
            profile_image=profile_image
        )

        messages.success(request, "Account created successfully. Please sign in.")
        return redirect('signin')

    return render(request, 'signup.html')

def signin(request):
    if request.method == 'POST':
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = None

        try:
            user_obj = User.objects.get(email = email)
            user = authenticate(request, username = user_obj.username, password = password)
        except User.DoesNotExist:
            user = None

        if user is not None:
            login(request, user)

            # get role from userprofile
            role = user.userprofile.role
            if role == 'customer':
                return redirect('customer_dashboard')
            elif role == 'supplier':
                return redirect('supplier_dashboard')
            elif role == 'delivery_personnel':
                return redirect('delivery_personnel_dashboard')
            else:
                return redirect('signup')
        else:
            messages.error(request, "Invalid email or password!")
            return redirect('signin')
    return render(request, 'signin.html')


def signout(request):
    logout(request)
    return redirect('home')

def customer_dashboard(request):
    categories = Category.objects.all().order_by('-created_at')[:3]
    products = (
        Product.objects
        .annotate(avg_rating=Avg('reviews__rating'))
        .order_by('-created_at')[:4]
    )
    productss = Product.objects.order_by('-created_at')[:4]

    context = {
        'categories': categories,
        'products': products,
        'productss': productss
    }
    return render(request, 'customer_dashboard.html', context)   

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

def supplier_profile(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = None
    context = {
        'profile': profile
    }
    return render(request, 'supplier_profile.html', context)

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

def supplier_category_list(request):
    categories = Category.objects.all().order_by('created_at')
    return render(request, 'category_list.html', {'categories': categories})

def supplier_products(request):
    products = Product.objects.filter(supplier = request.user)
    return render(request, 'product_list.html', {'products': products})

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

def delete_product(request, pk):
    product = get_object_or_404(Product, pk = pk, supplier = request.user)
    product.delete()
    return redirect('supplier_dashboard')

def supplier_blogs(request):
    blogs = Blog.objects.filter(supplier = request.user)
    return render(request, 'blog_list.html', {'blogs': blogs})

def add_blog(request):  
    form = BlogForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        blog = form.save(commit=False)
        blog.supplier = request.user
        blog.save()
        return redirect(supplier_dashboard)
    return render(request, 'add_blog.html', {
        'form': form
    })

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

def delete_blog(request, pk):
    blog = get_object_or_404(Blog, pk = pk, supplier = request.user)
    blog.delete()
    return redirect('supplier_dashboard')

def customer_profile(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = None
    context = {
        'profile': profile
    }
    return render(request, 'customer_profile.html', context)

def edit_customer_profile(request):
    return render(request, 'edit_customer_profile.html')

def category_list_customer(request):
    categories = Category.objects.all().order_by('created_at')
    return render(request, 'category_list_customer.html', {'categories': categories})

def buy_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.select_related('user').order_by('-created_at')

    if request.method == 'POST' and request.user.is_authenticated:
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if rating:
            ProductReview.objects.create(
                product=product,
                user=request.user,
                rating=rating,
                comment=comment
            )
            return redirect('buy_product', product_id=product.id)

    context = {
        'product': product,
        'reviews': reviews
    }
    return render(request, 'buy_product.html', context)

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

def rate_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        rating = int(request.POST.get("rating"))

        ProductReview.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={'rating': rating}
        )

        return redirect('product_detail', product_id=product.id)

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not item_created:
        cart_item.quantity += 1
        cart_item.save()

    return redirect('cart_page')


@login_required
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


@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    return redirect('cart_page')

@login_required
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    total_amount = cart.grand_total

    return render(request, 'esewa_checkout.html', {
        'cart': cart,
        'total_amount': total_amount
     })

@login_required
def process_payment(request):
    if request.method != "POST":
        return redirect("checkout")

    cart = Cart.objects.filter(user=request.user).first()
    if not cart or not cart.items.exists():
        return redirect("cart_page")

    total_amount = cart.grand_total
    payment_type = request.POST.get("payment_type")

    transaction_uuid = str(uuid.uuid4())

    order = Order.objects.create(
        user=request.user,
        full_name=request.POST.get("name"),
        email=request.POST.get("email"),
        phone=request.POST.get("phone"),
        address=request.POST.get("address"),
        city=request.POST.get("city"),
        country="Nepal",
        amount=total_amount,
        payment_type=payment_type,
        transaction_uuid=transaction_uuid,
        status="Pending"
    )

    request.session["current_order_id"] = order.id

    # ✅ CASH ON DELIVERY (same pattern as second code)
    if payment_type == "cod":
        cart.items.all().delete()
        return render(request, "payment_success.html", {"order": order})

    # ✅ ESEWA (FIXED — copied from working example)
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


@login_required
def payment_success(request):
    order_id = request.session.get('order_id')
    order = get_object_or_404(Order, id=order_id)

    order.status = "Paid"
    order.save()

    # clear cart (assuming you have a Cart model linked to User)
    if hasattr(order.user, 'cart'):
        order.user.cart.items.all().delete()

    return render(request, 'payment_success.html', {'order': order})


@login_required
def payment_fail(request):
    order_id = request.session.get('order_id')
    order = get_object_or_404(Order, id=order_id)

    order.status = "Failed"
    order.save()

    return render(request, 'payment_fail.html', {'order': order})
