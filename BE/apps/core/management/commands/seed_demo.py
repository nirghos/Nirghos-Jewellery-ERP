"""Create a company, branch, owner user and gold rates. Idempotent.

Usage: python manage.py seed_demo --username owner --password '<pw>'
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.accounts.models import User
from apps.companies.models import Branch, Company
from apps.products.models import MetalRate


class Command(BaseCommand):
    def add_arguments(self, p):
        p.add_argument("--username", default="owner")
        p.add_argument("--password", required=True)
        p.add_argument("--company", default="Nirghos Jewellery")

    def handle(self, *a, **o):
        c, _ = Company.objects.get_or_create(name=o["company"])
        b, _ = Branch.objects.get_or_create(company=c, code="HO", defaults={"name": "Head Office"})
        u, made = User.objects.get_or_create(username=o["username"], defaults={
            "company": c, "branch": b, "role": "owner", "is_staff": True, "is_superuser": True})
        if made:
            u.set_password(o["password"])
            u.save()
        if not MetalRate.objects.filter(company=c).exists():
            MetalRate.objects.create(company=c, branch=b, metal="gold", purity=Decimal("0.916"), rate_per_gram=Decimal("7000"))
            MetalRate.objects.create(company=c, branch=b, metal="silver", purity=Decimal("0.999"), rate_per_gram=Decimal("90"))
        self.stdout.write(f"user={u.username} created={made}")
