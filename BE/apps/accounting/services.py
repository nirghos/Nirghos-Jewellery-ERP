"""Double-entry posting. Posted entries are never edited or deleted - only reversed."""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import next_number
from .models import Account, JournalEntry, JournalLine

D = Decimal
DEFAULTS = [
    ("1000", "Cash in Hand", "asset"), ("1010", "Bank", "asset"), ("1100", "Accounts Receivable", "asset"),
    ("1200", "Inventory (Metal & Jewellery)", "asset"), ("1300", "Input GST", "asset"),
    ("2000", "Accounts Payable", "liability"), ("2100", "Output GST", "liability"),
    ("2200", "Customer Advances / Schemes", "liability"),
    ("3000", "Owner Capital", "equity"),
    ("4000", "Sales", "income"), ("4100", "Repair & Other Income", "income"),
    ("5000", "Purchases", "expense"), ("5100", "Karigar Labour", "expense"),
    ("5200", "General Expenses", "expense"), ("5300", "Salaries", "expense"),
]
METHOD_ACCOUNT = {"cash": "1000", "upi": "1010", "card": "1010", "bank": "1010"}


def ensure_accounts(company):
    if Account.objects.filter(company=company).exists():
        return
    Account.objects.bulk_create([Account(company=company, code=c, name=n, type=t, is_system=True) for c, n, t in DEFAULTS])


def acct(company, code):
    ensure_accounts(company)
    return Account.objects.get(company=company, code=code)


@transaction.atomic
def post(*, company, branch, user, kind, lines, narration="", reference="", date=None, reverses=None):
    """lines: list of (account_code_or_Account, debit, credit[, party])"""
    ensure_accounts(company)
    rows, td, tc = [], D(0), D(0)
    for ln in lines:
        a, dr, cr = ln[0], D(ln[1] or 0), D(ln[2] or 0)
        if dr < 0 or cr < 0 or (dr and cr):
            raise ValidationError("Invalid journal line")
        if dr == 0 and cr == 0:
            continue
        a = a if isinstance(a, Account) else Account.objects.get(company=company, code=a)
        if a.company_id != company.id:
            raise ValidationError("Invalid account")
        rows.append((a, dr, cr, ln[3] if len(ln) > 3 else ""))
        td += dr
        tc += cr
    if not rows or td != tc:
        raise ValidationError(f"Entry not balanced (Dr {td} / Cr {tc})")
    e = JournalEntry.objects.create(
        company=company, branch=branch, created_by=user, number=next_number(company, "jv", "JV"),
        date=date or timezone.localdate(), kind=kind, narration=narration[:300], reference=reference, reverses=reverses)
    JournalLine.objects.bulk_create([JournalLine(entry=e, account=a, debit=dr, credit=cr, party=p) for a, dr, cr, p in rows])
    return e


@transaction.atomic
def reverse(entry, user, narration=""):
    entry = JournalEntry.objects.select_for_update().get(pk=entry.pk)
    if entry.reversed_by.exists() or entry.reverses_id:
        raise ValidationError("Entry is already reversed or is itself a reversal")
    return post(company=entry.company, branch=entry.branch, user=user, kind="reversal",
                narration=narration or f"Reversal of {entry.number}", reference=entry.number, reverses=entry,
                lines=[(l.account, l.credit, l.debit, l.party) for l in entry.lines.all()])


def reverse_by_reference(company, kinds, reference, user, narration=""):
    for e in JournalEntry.objects.filter(company=company, kind__in=kinds, reference=reference, reverses__isnull=True):
        if not e.reversed_by.exists():
            reverse(e, user, narration)


# ---- posting helpers used by other modules ------------------------------------------------
def post_sale(inv, user):
    c, lines = inv.company, []
    for p in inv.payments.all():
        lines.append((METHOD_ACCOUNT[p.method], p.amount, 0))
    lines.append(("1100", inv.grand_total - inv.paid, 0, f"customer:{inv.customer_id}" if inv.customer_id else ""))
    lines.append(("1200", inv.old_gold_adjustment, 0))
    lines.append(("4000", 0, inv.taxable_value))
    lines.append(("2100", 0, inv.gst_amount))
    return post(company=c, branch=inv.branch, user=user, kind="sale", lines=lines,
                narration=f"Sale {inv.number}", reference=inv.number)


def post_purchase(pi, user):
    return post(company=pi.company, branch=pi.branch, user=user, kind="purchase", reference=pi.number,
                narration=f"Purchase {pi.number}",
                lines=[("1200", pi.subtotal, 0), ("1300", pi.gst_amount, 0), ("2000", 0, pi.total, f"supplier:{pi.supplier_id}")])


def balances(company, branch=None, upto=None, since=None):
    qs = JournalLine.objects.filter(entry__company=company)
    if branch:
        qs = qs.filter(entry__branch=branch)
    if upto:
        qs = qs.filter(entry__date__lte=upto)
    if since:
        qs = qs.filter(entry__date__gte=since)
    out = {r["account"]: (r["d"] or D(0), r["c"] or D(0)) for r in qs.values("account").annotate(d=Sum("debit"), c=Sum("credit"))}
    return out
