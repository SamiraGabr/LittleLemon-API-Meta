from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    slug  = models.SlugField(max_length=255)
    title = models.CharField(max_length=255, db_index=True)
    class Meta:
        unique_together      = ('slug', 'title')
        verbose_name_plural  = "Categories"
    def __str__(self):
        return self.title

class MenuItem(models.Model):
    title    = models.CharField(max_length=255, db_index=True)
    price    = models.DecimalField(max_digits=6, decimal_places=2, db_index=True)
    featured = models.BooleanField(db_index=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    class Meta:
        ordering = ['title']
    def __str__(self):
        return self.title

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    menuitem   = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity   = models.SmallIntegerField()
    unit_price = models.DecimalField(max_digits=6, decimal_places=2)
    price      = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        unique_together = ('menuitem', 'user')

class Order(models.Model):
    user          = models.ForeignKey(User, on_delete=models.CASCADE)
    delivery_crew = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="delivery_crew_orders", null=True, blank=True)
    status        = models.SmallIntegerField(default=0, db_index=True)
    total         = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    date          = models.DateField(db_index=True, auto_now_add=True)
    class Meta:
        ordering = ['-date']
    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

class OrderItem(models.Model):
    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menuitem   = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity   = models.SmallIntegerField()
    unit_price = models.DecimalField(max_digits=6, decimal_places=2)
    price      = models.DecimalField(max_digits=6, decimal_places=2)
    class Meta:
        unique_together = ('order', 'menuitem')
    def __str__(self):
        return f"{self.quantity} x {self.menuitem.title} in Order #{self.order.id}"