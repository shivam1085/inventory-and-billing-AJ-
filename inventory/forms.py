from django import forms
from django.forms import inlineformset_factory
from .models import Product, Customer, Sale, SaleItem

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['sku', 'name', 'description', 'cost_price', 'selling_price', 'quantity']

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'email', 'address']

class SaleForm(forms.ModelForm):
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        empty_label="Select a customer",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Sale
        fields = ['customer']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.order_by('name')

class SaleItemForm(forms.ModelForm):
    quantity = forms.IntegerField(min_value=1, initial=1)
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(quantity__gt=0),
        empty_label="Select a product"
    )

    class Meta:
        model = SaleItem
        fields = ['product', 'quantity']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'product': forms.Select(attrs={'class': 'form-control'})
        }

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')

        if product and quantity:
            if quantity > product.quantity:
                raise forms.ValidationError(f'Only {product.quantity} units available for {product.name}')
        return cleaned_data

# Create a formset for sale items
SaleItemFormSet = inlineformset_factory(
    Sale, 
    SaleItem,
    form=SaleItemForm,
    extra=1,  # Number of empty forms to display
    can_delete=True,
    validate_min=1,  # Require at least one item
)