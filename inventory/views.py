from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db import transaction
from .models import Product, Customer, Sale, SaleItem
from .forms import ProductForm, CustomerForm, SaleForm, SaleItemFormSet

def product_list(request):
    products = Product.objects.all().order_by('name')
    return render(request, 'inventory/product_list.html', {'products': products})

def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product created successfully.')
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'inventory/product_form.html', {'form': form})

def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully.')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'inventory/product_form.html', {'form': form})

def customer_list(request):
    customers = Customer.objects.all().order_by('name')
    return render(request, 'inventory/customer_list.html', {'customers': customers})

def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer created successfully.')
            return redirect('customer_list')
    else:
        form = CustomerForm()
    return render(request, 'inventory/customer_form.html', {'form': form})

from django.http import JsonResponse
from django.db import connection
import os

@transaction.atomic
def create_sale(request):
    if request.method == 'POST':
        # Handle quick-add customer
        if 'quick_add_customer' in request.POST:
            customer_form = CustomerForm(request.POST)
            if customer_form.is_valid():
                customer = customer_form.save()
                return JsonResponse({
                    'success': True,
                    'customer_id': customer.id,
                    'customer_name': customer.name
                })
            else:
                return JsonResponse({
                    'success': False,
                    'errors': customer_form.errors
                }, status=400)

        # Handle normal sale creation
        sale_form = SaleForm(request.POST)
        item_formset = SaleItemFormSet(request.POST)
        
        if sale_form.is_valid() and item_formset.is_valid():
            sale = sale_form.save(commit=False)
            sale.total_amount = 0
            sale.save()
            
            total = 0
            for form in item_formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                    item = form.save(commit=False)
                    item.sale = sale
                    item.unit_price = item.product.selling_price
                    
                    # Validate stock availability
                    if item.quantity > item.product.quantity:
                        messages.error(request, f'Only {item.product.quantity} units available for {item.product.name}')
                        transaction.set_rollback(True)
                        return redirect('create_sale')
                    
                    item.save()
                    total += item.total_price
            
            sale.total_amount = total
            sale.save()
            
            messages.success(request, f'Sale #{sale.invoice_number} created successfully.')
            return redirect('sale_receipt', pk=sale.pk)
    else:
        sale_form = SaleForm()
        item_formset = SaleItemFormSet()
        customer_form = CustomerForm()  # For quick-add modal
    
    return render(request, 'inventory/sale_form.html', {
        'sale_form': sale_form,
        'item_formset': item_formset,
        'customer_form': customer_form,  # Pass the customer form to template
    })

def sale_receipt(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    html = render_to_string('inventory/receipt.html', {'sale': sale})
    return HttpResponse(html)

def dashboard(request):
    context = {
        'total_products': Product.objects.count(),
        'low_stock_products': Product.objects.filter(quantity__lte=5),
        'recent_sales': Sale.objects.order_by('-created_at')[:5],
    }
    return render(request, 'inventory/dashboard.html', context)


def db_status(request):
    """Return JSON with current DB connection details (masked).
    Protected by a token passed as query param `token` that must match
    the DB_STATUS_TOKEN environment variable. Intended for production verification.
    """
    expected = os.environ.get('DB_STATUS_TOKEN')
    supplied = request.GET.get('token')
    if not expected or supplied != expected:
        return HttpResponse('Forbidden', status=403)

    info = connection.settings_dict.copy()
    # Mask sensitive fields
    if 'USER' in info and info['USER']:
        info['USER'] = str(info['USER'])[:2] + '***'
    if 'PASSWORD' in info and info['PASSWORD']:
        info['PASSWORD'] = '***'

    # Gather engine/vendor/version
    engine = info.get('ENGINE')
    vendor = connection.vendor
    version = 'unknown'
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT version()')
            row = cursor.fetchone()
            if row:
                version = row[0]
    except Exception as exc:
        version = f'error: {exc}'

    return JsonResponse({
        'engine': engine,
        'vendor': vendor,
        'database': {
            'NAME': str(info.get('NAME')),
            'HOST': info.get('HOST'),
            'PORT': info.get('PORT'),
        },
        'connected_to_postgres': vendor == 'postgresql' or (engine and 'postgresql' in engine),
        'version': version,
    })
