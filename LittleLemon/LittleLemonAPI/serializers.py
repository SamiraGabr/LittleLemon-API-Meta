from rest_framework import serializers
from .models import MenuItem, Category, Cart, Order, OrderItem
from django.contrib.auth.models import User
from decimal import Decimal
from rest_framework.validators import UniqueValidator

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'slug', 'title']

class MenuItemSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset = Category.objects.all()
    )
    # category_name = serializers.CharField(source='category.title', read_only=True)
    class Meta:
        model = MenuItem
        fields = ['id', 'title', 'price', 'featured', 'category']

class CartSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset = User.objects.all(),
        default  = serializers.CurrentUserDefault() 
    )
    menuitem_title = serializers.CharField(source='menuitem.title', read_only=True)
    """
    def validate(self, attrs):
        if 'menuitem' in attrs:
            attrs['unit_price'] = attrs['menuitem'].price
            attrs['price']      = attrs['quantity'] * attrs['unit_price']
        else:
            raise serializers.ValidationError({"message": "We Need Menuitem"})
        return attrs 
    """
    class Meta:
        model = Cart
        fields = ['user', 'menuitem', 'unit_price', 'quantity', 'price', 'menuitem_title']
        extra_kwargs = {
            'price'      : {'read_only' : True},
            'unit_price' : {'read_only' : True},
            'user'       : {'read_only' : True},
            'menuitem'   : {'write_only': True}, 

        }
        validators = []
    def create(self, validated_data):
        user       = validated_data['user']
        menuitem   = validated_data['menuitem']
        quantity   = validated_data['quantity']
        """
        try:
            menuitem_instance = MenuItem.objects.get(id=menuitem_id)
        except MenuItem.DoesNotExist:
            raise serializers.ValidationError({"menuitem": "Not Exists"})
        """
        unit_price = menuitem.price
        cart_item, created = Cart.objects.get_or_create(
            user=user,
            menuitem=menuitem,
            defaults={
                'quantity'   :quantity,
                'unit_price' :unit_price,
                'price'      :unit_price * quantity
            }
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.price = cart_item.quantity * cart_item.unit_price
            cart_item.save()
        return cart_item

class OrderItemSerializer(serializers.ModelSerializer):
    menuitem_title = serializers.CharField(source='menuitem.title', read_only=True)
    class Meta:
        model = OrderItem
        fields = ['id', 'menuitem_title', 'quantity', 'unit_price', 'price']
        extra_kwargs = {
            'price':      {'read_only' : True},
            'unit_price': {'read_only' : True},
            'menuitem':   {'write_only': True},
        }

class OrderSerializer(serializers.ModelSerializer):
    #orderitem   = OrderItemSerializer(many=True, read_only=True, source='order')
    items             = OrderItemSerializer(many=True, read_only=True)
    user_username           = serializers.CharField(source='user.username', read_only=True)
    delivery_crew_username  = serializers.CharField(source='delivery_crew.username', read_only=True, allow_null=True)
    class Meta:
        model = Order
        fields = ['id', 'user', 'user_username','delivery_crew', 'delivery_crew_username', 'status', 'total', 'date', 'items']
        extra_kwargs = {
            #'user'         : {'read_only': True},
            #'total'        : {'read_only': True}, 
            'date'         : {'read_only': True},
            'delivery_crew': {'required': False, 'allow_null': True}
            }

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']