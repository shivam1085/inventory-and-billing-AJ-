from django.db.models.signals import post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict
from .models import Sale, SaleItem
from .firebase import get_firestore_client, firebase_enabled


def _safe_float(value):
    try:
        return float(value)
    except Exception:
        return None


@receiver(post_save, sender=Sale)
def log_sale_to_firestore(sender, instance: Sale, created: bool, **kwargs):
    if not created:
        return
    if not firebase_enabled():
        return

    db = get_firestore_client()
    if not db:
        return

    try:
        items = []
        for it in instance.items.all():
            items.append({
                'product_id': it.product_id,
                'product_name': it.product.name,
                'quantity': it.quantity,
                'unit_price': _safe_float(it.unit_price),
                'total_price': _safe_float(it.total_price),
            })
        doc = {
            'sale_id': instance.id,
            'invoice_number': instance.invoice_number,
            'customer_id': instance.customer_id,
            'customer_name': instance.customer.name,
            'total_amount': _safe_float(instance.total_amount),
            'date': instance.date.isoformat(),
            'created_at': instance.created_at.isoformat() if instance.created_at else None,
            'items': items,
            'event_type': 'sale_created',
        }
        db.collection('sales_events').add(doc)
    except Exception:
        # Never block main flow
        pass


@receiver(post_save, sender=SaleItem)
def log_stock_event(sender, instance: SaleItem, created: bool, **kwargs):
    if not created:
        return
    if not firebase_enabled():
        return

    db = get_firestore_client()
    if not db:
        return

    try:
        doc = {
            'sale_id': instance.sale_id,
            'product_id': instance.product_id,
            'product_name': instance.product.name,
            'quantity_change': -int(instance.quantity),
            'unit_price': _safe_float(instance.unit_price),
            'total_price': _safe_float(instance.total_price),
            'event_type': 'stock_decremented',
        }
        db.collection('stock_events').add(doc)
    except Exception:
        pass
