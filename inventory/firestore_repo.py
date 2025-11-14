import os
from types import SimpleNamespace
from typing import List, Optional, Dict, Any

from .firebase import get_firestore_client, firebase_enabled
from typing import Tuple
try:
    # Optional import; functions that need transactions will guard usage
    from google.cloud import firestore as gcfirestore
except Exception:  # pragma: no cover - library may not be present locally
    gcfirestore = None


def firebase_sor_enabled() -> bool:
    """Feature flag to use Firestore as primary store for domain data."""
    return firebase_enabled() and os.environ.get('FIREBASE_SOR', 'false').lower() in ('1', 'true', 'yes')


def _ns(d: Dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(**d)


# ---------- Products ----------
def list_products() -> list[dict]:
    db = get_firestore_client()
    if not db:
        return []
    docs = db.collection('products').order_by('name').stream()
    results: list[dict] = []
    for doc in docs:
        d = doc.to_dict() or {}
        # ensure id/pk present for templates/links
        pid = d.get('id') or (doc.id.isdigit() and int(doc.id) or doc.id)
        d['id'] = pid
        d['pk'] = pid
        results.append(d)
    return results

def upsert_product(product) -> None:
    """Create/update a product document mirroring the Django model.
    Doc id is the Django Product.id as string for easy correlation.
    """
    db = get_firestore_client()
    if not db:
        return
    data = {
        'id': product.id,
        'sku': product.sku,
        'name': product.name,
        'description': product.description,
        'cost_price': float(product.cost_price),
        'selling_price': float(product.selling_price),
        'quantity': int(product.quantity),
        'updated_at': getattr(product, 'updated_at', None).isoformat() if getattr(product, 'updated_at', None) else None,
        'created_at': getattr(product, 'created_at', None).isoformat() if getattr(product, 'created_at', None) else None,
    }
    db.collection('products').document(str(product.id)).set(data, merge=True)


def get_product(product_id: int) -> Optional[Dict[str, Any]]:
    db = get_firestore_client()
    if not db:
        return None
    doc = db.collection('products').document(str(product_id)).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    d['id'] = product_id
    return d


def reserve_and_decrement_stock(requested: Dict[int, int]) -> Dict[int, int]:
    """Perform a Firestore transaction to check and decrement stock atomically.

    requested: {product_id: quantity_to_decrement}
    Returns: {product_id: new_quantity_after_decrement}
    Raises ValueError on insufficient stock or RuntimeError if Firestore unavailable.
    """
    db = get_firestore_client()
    if not db or not gcfirestore:
        raise RuntimeError('Firestore not available for transactional stock update')

    transaction = db.transaction()

    @gcfirestore.transactional
    def _apply(tx, _db, req: Dict[int, int]) -> Dict[int, int]:
        new_qty_map: Dict[int, int] = {}
        # Deterministic order to avoid deadlocks
        for pid in sorted(req.keys(), key=lambda x: int(x)):
            need = int(req[pid])
            ref = _db.collection('products').document(str(pid))
            snap = ref.get(transaction=tx)
            data = snap.to_dict() or {}
            current = int(data.get('quantity', 0))
            if need <= 0:
                continue
            if need > current:
                raise ValueError(f'Insufficient stock for product {data.get("name", pid)}: need {need}, have {current}')
            new_q = current - need
            tx.update(ref, {'quantity': new_q})
            new_qty_map[pid] = new_q
        return new_qty_map

    return _apply(transaction, db, requested)


# ---------- Customers ----------
def list_customers() -> list[dict]:
    db = get_firestore_client()
    if not db:
        return []
    docs = db.collection('customers').order_by('name').stream()
    results: list[dict] = []
    for doc in docs:
        d = doc.to_dict() or {}
        cid = d.get('id') or (doc.id.isdigit() and int(doc.id) or doc.id)
        d['id'] = cid
        d['pk'] = cid
        results.append(d)
    return results

def upsert_customer(customer) -> None:
    db = get_firestore_client()
    if not db:
        return
    data = {
        'id': customer.id,
        'name': customer.name,
        'phone': customer.phone,
        'email': customer.email,
        'address': customer.address,
        'created_at': getattr(customer, 'created_at', None).isoformat() if getattr(customer, 'created_at', None) else None,
    }
    db.collection('customers').document(str(customer.id)).set(data, merge=True)


# ---------- Sales ----------

def write_sale_and_sync_products(sale) -> None:
    """Write a canonical sale document and ensure product quantities are mirrored.
    Assumes Django already validated stock and decremented local Product.quantity.
    """
    db = get_firestore_client()
    if not db:
        return

    items = []
    for it in sale.items.all():
        items.append({
            'product_id': it.product_id,
            'product_name': it.product.name,
            'quantity': int(it.quantity),
            'unit_price': float(it.unit_price),
            'total_price': float(it.total_price),
        })

    sale_doc = {
        'id': sale.id,
        'invoice_number': sale.invoice_number,
        'customer_id': sale.customer_id,
        'customer_name': sale.customer.name,
        'total_amount': float(sale.total_amount),
        'date': sale.date.isoformat(),
        'created_at': sale.created_at.isoformat() if sale.created_at else None,
        'items': items,
    }
    db.collection('sales').document(str(sale.id)).set(sale_doc, merge=False)

    # Mirror product quantities post-sale
    batch = db.batch()
    for it in sale.items.all():
        p = it.product
        ref = db.collection('products').document(str(p.id))
        batch.set(ref, {
            'id': p.id,
            'sku': p.sku,
            'name': p.name,
            'description': p.description,
            'cost_price': float(p.cost_price),
            'selling_price': float(p.selling_price),
            'quantity': int(p.quantity),
        }, merge=True)
    batch.commit()


def get_sale_for_receipt(sale_id: int) -> Optional[SimpleNamespace]:
    """Return a namespaced object suitable for the template."""
    db = get_firestore_client()
    if not db:
        return None
    doc = db.collection('sales').document(str(sale_id)).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    # Build a small object with attribute access similar to model
    items = [
        _ns({
            'product': _ns({'name': it.get('product_name')}),
            'quantity': it.get('quantity'),
            'unit_price': it.get('unit_price'),
            'total_price': it.get('total_price'),
        })
        for it in d.get('items', [])
    ]
    sale_obj = _ns({
        'id': d.get('id'),
        'invoice_number': d.get('invoice_number'),
        'customer': _ns({'name': d.get('customer_name')}),
        'date': d.get('date'),
        'total_amount': d.get('total_amount'),
        'items': items,
    })
    return sale_obj


def list_recent_sales(limit: int = 5) -> list[dict]:
    """Fetch recent sales from Firestore for dashboard widgets."""
    db = get_firestore_client()
    if not db:
        return []
    try:
        # Order by ISO datetime string is acceptable for ISO-8601 format
        direction = gcfirestore.Query.DESCENDING if gcfirestore else None
        q = db.collection('sales').order_by('date', direction=direction).limit(limit)
        docs = q.stream()
    except Exception:
        return []
    results: list[dict] = []
    for doc in docs:
        d = doc.to_dict() or {}
        d['id'] = d.get('id') or doc.id
        results.append({
            'id': d.get('id'),
            'invoice_number': d.get('invoice_number'),
            'customer_name': d.get('customer_name'),
            'total_amount': d.get('total_amount'),
            'date': d.get('date'),
        })
    return results
