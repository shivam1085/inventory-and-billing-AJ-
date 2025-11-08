from django.db import models
from django.utils import timezone

class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.sku})"

class Customer(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Sale(models.Model):
    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    date = models.DateTimeField(default=timezone.now)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice #{self.invoice_number}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number based on date and ID
            last_sale = Sale.objects.order_by('-id').first()
            last_id = last_sale.id if last_sale else 0
            self.invoice_number = f"INV{timezone.now().strftime('%Y%m%d')}{last_id + 1:04d}"
        super().save(*args, **kwargs)

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = self.quantity * self.unit_price
        
        # Update product quantity
        if not self.id:  # Only reduce stock on creation
            self.product.quantity -= self.quantity
            self.product.save()
            
        super().save(*args, **kwargs)
