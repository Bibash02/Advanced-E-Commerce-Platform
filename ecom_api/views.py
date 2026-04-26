import email
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .serializers import *
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated as isAuthenticated
from .permissions import *
import uuid
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django.core.mail import send_mail

from django.contrib.auth import get_user_model
User = get_user_model()


# Create your views here.
@api_view(['GET', 'POST'])
def test(request):
    return Response("Successful.")

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data = request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        token, _ = Token.objects.get_or_create(user=user)

        subject = "SignUp - Welcome to ShopSphere"
        message = f"""
Hi {user.first_name},

Your account has been successfully created.

Username: {user.username}

You can now login and start using our platform.

Thank you,
ShopSphere Team
"""
        recipient_list = [email]

        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                recipient_list,
                fail_silently=False,
            )
        except Exception as e:
            print("Email sending failed:", e)
        return Response({
            "message": "Account created successfully",
            "token": token.key,
            "email": user.email,
            "role": user.userprofile.role
        }, status=201)


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Invalid email or password"}, status=400)

        user = authenticate(username=user_obj.username, password=password)

        if not user:
            return Response({"error": "Invalid email or password"}, status=400)

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "message": "Login successful",
            "token": token.key,
            "username": user.first_name,
            "role": user.userprofile.role
        })

class CustomerProductListAPIView(ListAPIView):
    queryset = Product.objects.filter(stock__gt=0)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [SearchFilter]
    search_fields = ['name', 'supplier__username', 'category__name']

class CustomerProductDetailAPIView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Product.objects.filter(stock__gt=0)
    serializer_class = ProductDetailSerializer
    lookup_field = 'pk'

class CustomerProfileAPIView(APIView):
    permission_classes = [isAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user.userprofile)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = ProfileSerializer(request.user.userprofile, data = request.data, partial = True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class CustomerBlogListAPIView(APIView):
    permission_classes = [isAuthenticated]

    def get(self, request):
        blogs = Blog.objects.filter(is_published=True)
        serializer = BlogSerializer(blogs, many=True)
        return Response(serializer.data)

class CustomerOrderCreateAPIView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = serializer.save(
            user=request.user,
            amount=request.user.cart.total_amount(),  
            transaction_uuid=str(uuid.uuid4())
        )

        return Response({
            "message": "Order created successfully",
            "order_id": order.id
        }, status=201)

class CheckoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = Cart.objects.get(user=request.user)
        if cart.items.count() == 0:
            return Response({"error": "Cart is empty"}, status=400)

        full_name = request.data.get('full_name')
        email = request.data.get('email')
        phone = request.data.get('phone')
        address = request.data.get('address')
        city = request.data.get('city')
        payment_type = request.data.get('payment_type')

        order = Order.objects.create(
            user=request.user,
            full_name=full_name,
            email=email,
            phone=phone,
            address=address,
            city=city,
            amount=cart.grand_total,
            payment_type=payment_type,
            transaction_uuid=str(uuid.uuid4())
        )

        # Move cart items to order items
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

        # Clear cart
        cart.items.all().delete()

        return Response({"message": "Order created successfully", "order_id": order.id})
    
class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

class CartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_cart(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart

    # View cart
    def get(self, request):
        cart = self.get_cart()
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    # Add product to cart
    def post(self, request):
        cart = self.get_cart()
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        product = get_object_or_404(Product, id=product_id)

        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()

        serializer = CartSerializer(cart)
        return Response(serializer.data)

    # Update cart item quantity
    def put(self, request):
        cart = self.get_cart()
        for item in request.data.get('items', []):
            item_id = item.get('id')
            quantity = item.get('quantity')
            cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
            if quantity <= 0:
                cart_item.delete()
            else:
                cart_item.quantity = quantity
                cart_item.save()
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    # Remove cart item
    def delete(self, request):
        cart = self.get_cart()
        item_id = request.data.get('item_id')
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        cart_item.delete()
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
class SupplierProductAPIView(APIView):
    permission_classes = [IsSupplier]

    def get(self, request):
        products = Product.objects.filter(supplier = request.user)
        serializer = SupplierProductSerializer(products, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serialzer = SupplierProductSerializer(data = request.data)
        serialzer.is_valid(raise_exception=True)
        serialzer.save(supplier=request.user)
        return Response(serialzer.data, status=201)

class SupplierProductDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        product = get_object_or_404(Product, pk = pk, supplier = request.user)
        serializer = SupplierProductSerializer(product)
        return Response(serializer.data)

    def put(self, request, pk):
        product = get_object_or_404(Product, pk = pk, supplier = request.user)
        serializer = SupplierProductSerializer(product, data = request.data, partial = True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    def delete(self, request, pk):
        product = get_object_or_404(Product, pk = pk, supplier = request.user)
        product.delete()
        return Response({"message": "Product deleted successfully"}, status=204)

class SupplierBlogAPIView(APIView):
    permission_classes = [IsSupplier]

    def get(self, request):
        blogs = Blog.objects.filter(supplier = request.user)
        serializer = SupplierBlogSerializer(blogs, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = SupplierBlogSerializer(data = request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(supplier = request.user)
        return Response(serializer.data, status=201)

class SupplierBlogDetailAPIView(APIView):
    permission_classes = [IsSupplier]

    def put(self, request, pk):
        blog = get_object_or_404(Blog, pk = pk, supplier = request.user)
        serializer = SupplierBlogSerializer(blog, data = request.data, partial = True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    def delete(self, request, pk):
        blog = get_object_or_404(Blog, pk = pk, supplier = request.user)
        blog.delete()
        return Response({"message": "Blog deleted successfully"}, status=204)

class SupplierProfileAPIView(APIView):
    permission_classes = [IsSupplier]

    def get(self, request):
        serializer = SupplierProfileSerializer(request.user.userprofile)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = SupplierProfileSerializer(request.user.userprofile, data = request.data, partial = True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
class DeliveryProfileAPIView(APIView):
    permission_classes = [IsDeliveryPersonnel]

    def get(self, request):
        serializer = DeliveryProfileSerializer(request.user.userprofile)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = DeliveryProfileSerializer(request.user.userprofile, data = request.data, partial = True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class DeliveryAssignedOrdersAPIView(APIView):
    permission_classes = [IsDeliveryPersonnel]

    def get(self, request):
        orders = Order.objects.filter(delivery_person=request.user, status='Assigned')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    
class DeliveryUpdateOrderStatusAPIView(APIView):
    permission_classes = [IsDeliveryPersonnel]

    def get(self, request, pk):
        order = get_object_or_404(Order, pk = pk, delivery_person = request.user)
        serializer = OrderSerializer(order)
        return Response(serializer.data)
    
    def patch(self, request, pk):
        order = get_object_or_404(Order, pk = pk, delivery_person = request.user)
        status = request.data.get('status')

        allowed_status = ['Delivered', 'Failed', 'Cancelled']

        # check valid status
        if status not in allowed_status:
            return Response({"error": f"Invalid status. Allowed status like {allowed_status}"}, status=400)
        
        if status == 'Delivered':
            if 'delivery_proof' not in request.FILES:
                return Response({"error": "Delivery proof image is required for Delivered status"}, status=400)
            order.delivery_proof = request.FILES['delivery_proof']

        order.status = status
        order.save()

        # EMAIL NOTIFICATION
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

        return Response({
            "message": "Order status updated successfully",
            "new_status": order.status
        })

