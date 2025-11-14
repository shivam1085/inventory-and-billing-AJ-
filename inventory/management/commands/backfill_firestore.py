from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from inventory.models import Product, Customer, Sale
from inventory.firestore_repo import upsert_product, upsert_customer, write_sale_and_sync_products

class Command(BaseCommand):
    help = "Backfill Firestore collections from current Django database."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--include-sales', action='store_true', help='Also write canonical sales and mirror product quantities')
        parser.add_argument('--sales-batch', type=int, default=200, help='Process sales in batches of N')

    def handle(self, *args, **options):
        include_sales = options['include_sales']
        self.stdout.write(self.style.MIGRATE_HEADING('Backfilling products...'))
        with transaction.atomic():
            for p in Product.objects.all().iterator():
                try:
                    upsert_product(p)
                except Exception as exc:
                    self.stderr.write(f"Product {p.id} failed: {exc}")
        self.stdout.write(self.style.SUCCESS('Products backfilled.'))

        self.stdout.write(self.style.MIGRATE_HEADING('Backfilling customers...'))
        with transaction.atomic():
            for c in Customer.objects.all().iterator():
                try:
                    upsert_customer(c)
                except Exception as exc:
                    self.stderr.write(f"Customer {c.id} failed: {exc}")
        self.stdout.write(self.style.SUCCESS('Customers backfilled.'))

        if include_sales:
            self.stdout.write(self.style.MIGRATE_HEADING('Backfilling sales...'))
            batch_size = options['sales_batch'] or 200
            qs = Sale.objects.order_by('id')
            total = qs.count()
            start = 0
            while start < total:
                for s in qs[start:start+batch_size]:
                    try:
                        write_sale_and_sync_products(s)
                    except Exception as exc:
                        self.stderr.write(f"Sale {s.id} failed: {exc}")
                start += batch_size
                self.stdout.write(f"Processed {min(start, total)}/{total} sales...")
            self.stdout.write(self.style.SUCCESS('Sales backfilled.'))

        self.stdout.write(self.style.SUCCESS('Firestore backfill completed.'))
