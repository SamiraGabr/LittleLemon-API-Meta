from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Category, MenuItem, Cart, Order, OrderItem
from .serializers import CartSerializer, MenuItemSerializer, CategorySerializer, OrderItemSerializer, OrderSerializer, UserSerializer
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated, BasePermission
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_list_or_404
from django.contrib.auth.models import Group, User
from rest_framework import viewsets
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission
from decimal import Decimal
from datetime import date


class IsManagerUser(BasePermission): 
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.groups.filter(name='Manager').exists()
    
class IsDeliveryCrewUser(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name='Delivery Crew').exists()
    
class IsCustomerUser(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return not request.user.groups.filter(name__in=['Manager', 'Delivery Crew']).exists() and not request.user.is_superuser

class CategoriesView(generics.ListCreateAPIView):
    queryset          = Category.objects.all()
    serializer_class  = CategorySerializer
    search_fields   = ['title', 'slug']
    ordering_fields = ['title', 'slug', 'id']

    def get_permissions(self):
        permission_classes = []
        if self.request.method == 'GET':
            permission_classes = []
        elif self.request.method == 'POST':
            permission_classes =[IsAuthenticated, IsManagerUser]
        else:
            permission_classes =[IsAuthenticated, IsManagerUser]
        return [permission() for permission in permission_classes]

class MenuItemsView(generics.ListCreateAPIView):
    queryset          = MenuItem.objects.all()
    serializer_class  = MenuItemSerializer
    search_fields     = ['title', 'category__title']
    ordering_fields   = ['price', 'title']

    def get_permissions(self):
        permission_classes = []
        if self.request.method == 'GET':
            permission_classes = []
        elif self.request.method == 'POST':
            permission_classes = [IsAuthenticated, IsManagerUser]
        return [permission() for permission in permission_classes]
    
class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset          = MenuItem.objects.all()
    serializer_class  = MenuItemSerializer
    
    def get_permissions(self):
        permission_classes = []
        if self.request.method == 'GET':
            permission_classes = []
        elif self.request.method in ['PUT', 'PATCH', 'DELETE']:
            permission_classes = [IsAuthenticated, IsManagerUser]
        return [permission() for permission in permission_classes]
    
class CartView(generics.ListCreateAPIView):
    #queryset           = Cart.objects.all()
    serializer_class   = CartSerializer
    permission_classes = [IsAuthenticated, IsCustomerUser]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)
    #def perform_create(self, serializer):
        menuitem  = serializer.validated_data['menuitem']
        quantity  = serializer.validated_data['quantity']
        user      = self.request.user
        cart_item, created = Cart.objects.get_or_create(user=user, menuitem=menuitem, defaults={'quantity':quantity, 'unit_price': menuitem.price, 'price': menuitem.price * quantity})
        if not created:
            cart_item.quantity += quantity
            cart_item.price     = cart_item.quantity * cart_item.unit_price
            cart_item.save()
            serializer._instance= cart_item

    def delete(self, request, *args, **kwargs):
        Cart.objects.all().filter(user=self.request.user).delete()
        return Response({"message": "Done"}, status=status.HTTP_204_NO_CONTENT) #REMEBER TO EDIT THESE AND ADD FEATURE TO REMOVE SPESIFIC ITEM FROM THE USER CART
    
class OrderView(generics.ListCreateAPIView):
    serializer_class   = OrderSerializer
    permission_classes = [IsAuthenticated]
    search_fields      = ['user__username', 'delivery_crew__username', 'status']
    ordering_fields    = ['date', 'total', 'status']

    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.groups.filter(name='Manager').exists():
            return Order.objects.all()
        elif self.request.user.groups.filter(name='Delivery Crew').exists():
            return Order.objects.filter(delivery_crew=self.request.user)
        elif not self.request.user.groups.exists():
            return Order.objects.filter(user=self.request.user)
        return Order.objects.none()
        
    def create(self, request, *args, **kwargs):
        if not (self.request.user.is_authenticated and self.request.user.groups.count() == 0 and not self.request.user.is_superuser):
            return Response({"message" : "Customers Only"}, status=status.HTTP_403_FORBIDDEN)
        
        current_user_cart_items  =  Cart.objects.filter(user=self.request.user)
        if not current_user_cart_items.exists():
            return Response({"message": "Empty Cart!!!"}, status=status.HTTP_400_BAD_REQUEST)
        
        total_price = Decimal(0)
        for item in current_user_cart_items:
            total_price += item.price

        order_data = {
            'user'   : self.request.user.id,
            'total'  : total_price,
            'status' : 0,
            'date'   : date.today().isoformat()
        }
        order_serializer = OrderSerializer(data=order_data)

        if order_serializer.is_valid(raise_exception=True):
            order = order_serializer.save()

            for cart_item in current_user_cart_items:
                OrderItem.objects.create(
                    order      = order,
                    menuitem   = cart_item.menuitem,
                    quantity   = cart_item.quantity,
                    unit_price = cart_item.unit_price,
                    price      = cart_item.menuitem.price 
                )
            current_user_cart_items.delete()
            return Response(order_serializer.data, status=status.HTTP_201_CREATED)
        
class SingleOrderView(generics.RetrieveUpdateAPIView):
    queryset           = Order.objects.all()
    serializer_class   = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.groups.filter(name='Manager').exists():
            return Order.objects.all()
        elif self.request.user.groups.filter(name = 'Delivery Crew').exists():
            return Order.objects.filter(delivery_crew = self.request.user)
        elif not self.request.user.groups.exists():
            return Order.objects.filter(user=self.request.user)
        return Order.objects.none()
    
    def get_object(self):
        obj  =  super().get_object()
        if self.request.user.groups.count() == 0 and not self.request.user.is_superuser:
            if obj.user != self.request.user:
                raise PermissionDenied("You Don't Have Permission")
        elif self.request.user.groups.filter(name='Delivery Crew').exists():
            if obj.delivery_crew != self.request.user:
                raise PermissionDenied("You Don't Have Permission")
        return obj
        
    def update(self, request, *args, **kwargs):
        order  =  self.get_object()
        
        if self.request.user.groups.count() == 0 and not self.request.user.is_superuser:
            return Response({"message": "You Don't have permission to update the order"}, status=status.HTTP_403_FORBIDDEN)
        
        elif self.request.user.is_superuser or self.request.user.groups.filter(name='Manager').exists():
            serializer  =  self.get_serializer(order, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        elif self.request.user.groups.filter(name='Delivery Crew').exists():
            allowed_fields  =  ['status']

            for key in request.data:
                if key not in allowed_fields:
                    return Response(
                        {"message": "Not allowed only Satus Is allowed for editing."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            serializer  =  self.get_serializer(order, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"message": "No Permission"}, status=status.HTTP_403_FORBIDDEN)
    
    def destroy(self, request, *args, **kwargs):
        if not (self.request.user.is_superuser or self.request.user.groups.filter(name='Manager').exists()):
            return Response({"message": "Managers Only"}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)
    
class GroupViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsManagerUser]

    def list(self, request):
        users = User.objects.all().filter(groups__name='Manager')
        items = UserSerializer(users, many=True)
        return Response(items.data)
    
    def create(self, request):
        username = request.data.get('username')
        if not username:
            return Response({"message": "Username is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        user           = get_object_or_404(User, username=username)
        managers_group = Group.objects.get(name="Manager")
        managers_group.user_set.add(user)
        return Response({"message": "user added to the manager group"}, status=status.HTTP_201_CREATED)
    
    def destroy(self, request):
        username = request.data.get('username')
        if not username:
            return Response({"message": "Username is required"}, status=status.HTTP_400_BAD_REQUEST)
        user           = get_object_or_404(User, username=username)
        managers_group = Group.objects.get(name="Manager")
        managers_group.user_set.remove(user)
        return Response({"message": "user removed from the manager group"}, status=status.HTTP_200_OK)
    
class DeliveryCrewViewSet(viewsets.ViewSet):
    permission_classes  =  [IsAuthenticated, IsManagerUser]

    def list(self, request):
        users = User.objects.all().filter(groups__name ='Delivery Crew')
        items = UserSerializer(users, many=True)
        return Response(items.data)
    
    def create(self, request):
        username = request.data.get('username')
        if not username:
            return Response({"message": "Username is required"}, status=status.HTTP_400_BAD_REQUEST)
        #if self.request.user.is_superuser == False:
         #   if self.request.user.groups.filter(name='Mannager').exists() == False:
          #      return Response({"message":"forbidden"}, status.HTTP_403_FORBIDDEN)
        user = get_object_or_404(User, username=username)
        dc_group   = Group.objects.get(name="Delivery Crew")
        dc_group.user_set.add(user)
        return Response({"message":"user added to the delivery crew group"}, status=status.HTTP_201_CREATED)
        
    def destroy(self, request):
        username = request.data.get('username')
        if not username:
            return Response({"message": "Username is required"}, status=status.HTTP_400_BAD_REQUEST)
        #if self.request.user.is_superuser == False:
         #   if self.request.user.groups.filter(name='Manager').exists() == False:
          #      return Response({"message" : "forbidden"}, status.HTTP_403_FORBIDDEN)
        user = get_object_or_404(User, username=username)
        dc_group   = Group.objects.get(name="Delivery Crew")
        dc_group.user_set.remove(user)
        return Response({"message" : "user removed from the delivery crew group successfully"}, status=status.HTTP_200_OK)
