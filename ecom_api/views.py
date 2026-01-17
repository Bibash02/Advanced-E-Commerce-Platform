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


class CustomerProductListAPIView(APIView):
    permission_classes = [isAuthenticated]

    def get(self, request):
        products = Product.objects.filter(is_active=True)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

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
    
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class BlogViewSet(viewsets.ModelViewSet):
    queryset = Blog.objects.all()
    serializer_class = BlogSerializer

