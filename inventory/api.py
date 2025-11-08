from django.http import JsonResponse
from .models import Product

def get_product_price(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        return JsonResponse({
            'id': product.id,
            'name': product.name,
            'selling_price': float(product.selling_price),
            'available_qty': product.quantity
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)