from datetime import date as _date
from decimal import Decimal

from django.db.models import Sum
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import mixins, viewsets

from apps.accounts.permissions import ModulePermission
from apps.core.crud import serializer_for, viewset_for
from apps.core.models import AuditLog, audit
from . import services as S
from .models import Account, JournalEntry, JournalLine

D = Decimal
TYPES = ["asset", "liability", "equity", "income", "expense"]


class AccountViewSet(viewset_for(Account, "accounting", search=["code", "name"], filters=["type"], branch_scoped=False,
                                 readonly=["is_system"])):
    pagination_class = None

    def get_queryset(self):
        S.ensure_accounts(self.request.user.company)
        return super().get_queryset()

    def perform_destroy(self, instance):
        if instance.is_system or instance.lines.exists():
            raise ValidationError("System accounts and accounts with entries cannot be deleted")
        super().perform_destroy(instance)


class LineSer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)
    account_code = serializers.CharField(source="account.code", read_only=True)

    class Meta:
        model = JournalLine
        fields = ["id", "account", "account_code", "account_name", "debit", "credit", "party"]


class EntrySer(serializers.ModelSerializer):
    lines = LineSer(many=True, read_only=True)
    reversed = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = ["id", "number", "date", "kind", "narration", "reference", "reverses", "reversed", "lines", "created_at"]

    def get_reversed(self, o):
        return o.reversed_by.exists()


class VoucherIn(serializers.Serializer):
    type = serializers.ChoiceField(choices=["receipt", "payment", "expense", "income", "contra", "journal"])
    date = serializers.DateField(required=False)
    amount = serializers.DecimalField(max_digits=16, decimal_places=2, min_value=D("0.01"), required=False)
    account = serializers.UUIDField(required=False)          # the "other" account
    via = serializers.ChoiceField(choices=["cash", "bank"], default="cash")
    narration = serializers.CharField(required=False, allow_blank=True, default="")
    lines = serializers.ListField(child=serializers.DictField(), required=False)


class EntryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    module = "accounting"
    permission_classes = [ModulePermission]
    serializer_class = EntrySer
    queryset = JournalEntry.objects.prefetch_related("lines__account")
    search_fields = ["number", "narration", "reference"]
    filterset_fields = ["kind"]
    perm_map = {"reverse": "approve"}

    def get_queryset(self):
        u = self.request.user
        qs = super().get_queryset().filter(company_id=u.company_id)
        if not u.all_branches:
            qs = qs.filter(branch_id=u.branch_id)
        p = self.request.query_params
        if p.get("from"):
            qs = qs.filter(date__gte=p["from"])
        if p.get("to"):
            qs = qs.filter(date__lte=p["to"])
        return qs

    def create(self, request):
        s = VoucherIn(data=request.data)
        s.is_valid(raise_exception=True)
        d, u = s.validated_data, request.user
        company = u.company
        S.ensure_accounts(company)
        cash = Account.objects.get(company=company, code="1000" if d["via"] == "cash" else "1010")
        if d["type"] == "journal":
            lines = []
            for l in d.get("lines", []):
                a = Account.objects.filter(company=company, pk=l.get("account")).first()
                if not a:
                    raise ValidationError("Unknown account in lines")
                lines.append((a, D(str(l.get("debit") or 0)), D(str(l.get("credit") or 0)), l.get("party", "")))
        else:
            if not d.get("amount") or not d.get("account"):
                raise ValidationError("amount and account are required")
            other = Account.objects.filter(company=company, pk=d["account"]).first()
            if not other:
                raise ValidationError({"account": "Unknown account"})
            amt = d["amount"]
            if d["type"] in ("receipt", "income"):
                lines = [(cash, amt, 0), (other, 0, amt)]
            elif d["type"] in ("payment", "expense"):
                lines = [(other, amt, 0), (cash, 0, amt)]
            else:  # contra: move between cash and bank
                lines = [(other, amt, 0), (cash, 0, amt)]
        e = S.post(company=company, branch=u.branch, user=u, kind=d["type"], lines=lines,
                   narration=d["narration"], date=d.get("date"))
        audit(u, "create", e)
        return Response(EntrySer(e).data, status=201)

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        e = S.reverse(self.get_object(), request.user, request.data.get("reason", ""))
        audit(request.user, "reverse", e)
        return Response(EntrySer(e).data)


def _range(request):
    p = request.query_params
    return p.get("from") or None, p.get("to") or None


class _Report(APIView):
    module = "accounting"
    permission_classes = [ModulePermission]

    def scope(self, request):
        u = request.user
        S.ensure_accounts(u.company)
        branch = None if u.all_branches else u.branch
        if u.all_branches and request.query_params.get("branch"):
            branch = u.company.branches.filter(pk=request.query_params["branch"]).first()
        return u.company, branch


class TrialBalance(_Report):
    def get(self, request):
        company, branch = self.scope(request)
        f, t = _range(request)
        bal = S.balances(company, branch, upto=t, since=f)
        rows, td, tc = [], D(0), D(0)
        for a in Account.objects.filter(company=company):
            d, c = bal.get(a.id, (D(0), D(0)))
            if d == 0 and c == 0:
                continue
            net = d - c
            rows.append({"code": a.code, "name": a.name, "type": a.type, "debit": max(net, D(0)), "credit": max(-net, D(0))})
            td += max(net, D(0))
            tc += max(-net, D(0))
        return Response({"rows": rows, "total_debit": td, "total_credit": tc})


class ProfitLoss(_Report):
    def get(self, request):
        company, branch = self.scope(request)
        f, t = _range(request)
        bal = S.balances(company, branch, upto=t, since=f)
        inc, exp = [], []
        for a in Account.objects.filter(company=company, type__in=["income", "expense"]):
            d, c = bal.get(a.id, (D(0), D(0)))
            if a.type == "income" and (c - d):
                inc.append({"code": a.code, "name": a.name, "amount": c - d})
            if a.type == "expense" and (d - c):
                exp.append({"code": a.code, "name": a.name, "amount": d - c})
        ti, te = sum((x["amount"] for x in inc), D(0)), sum((x["amount"] for x in exp), D(0))
        return Response({"income": inc, "expenses": exp, "total_income": ti, "total_expense": te, "net_profit": ti - te})


class BalanceSheet(_Report):
    def get(self, request):
        company, branch = self.scope(request)
        _, t = _range(request)
        bal = S.balances(company, branch, upto=t)
        out = {"asset": [], "liability": [], "equity": []}
        profit = D(0)
        for a in Account.objects.filter(company=company):
            d, c = bal.get(a.id, (D(0), D(0)))
            if a.type == "income":
                profit += c - d
            elif a.type == "expense":
                profit -= d - c
            elif d or c:
                amt = d - c if a.type == "asset" else c - d
                out[a.type].append({"code": a.code, "name": a.name, "amount": amt})
        out["equity"].append({"code": "", "name": "Retained profit (current)", "amount": profit})
        ta = sum((x["amount"] for x in out["asset"]), D(0))
        tl = sum((x["amount"] for x in out["liability"] + out["equity"]), D(0))
        return Response({**out, "total_assets": ta, "total_liabilities_equity": tl, "balanced": ta == tl})


class Ledger(_Report):
    """Account ledger with running balance. Also used for cashbook/bankbook (codes 1000/1010)."""
    def get(self, request):
        company, branch = self.scope(request)
        code = request.query_params.get("code", "1000")
        a = Account.objects.filter(company=company, code=code).first()
        if not a:
            raise ValidationError("Unknown account code")
        f, t = _range(request)
        qs = JournalLine.objects.filter(account=a).select_related("entry").order_by("entry__date", "entry__created_at")
        if branch:
            qs = qs.filter(entry__branch=branch)
        if f:
            qs = qs.filter(entry__date__gte=f)
        if t:
            qs = qs.filter(entry__date__lte=t)
        run, rows = D(0), []
        sign = 1 if a.type in ("asset", "expense") else -1
        for l in qs:
            run += sign * (l.debit - l.credit)
            rows.append({"date": l.entry.date, "number": l.entry.number, "narration": l.entry.narration,
                         "debit": l.debit, "credit": l.credit, "balance": run})
        return Response({"account": f"{a.code} {a.name}", "rows": rows, "closing": run})


class Daybook(_Report):
    def get(self, request):
        company, branch = self.scope(request)
        day = request.query_params.get("date") or _date.today().isoformat()
        qs = JournalEntry.objects.filter(company=company, date=day).prefetch_related("lines__account")
        if branch:
            qs = qs.filter(branch=branch)
        return Response({"date": day, "entries": EntrySer(qs, many=True).data})


class Parties(_Report):
    """Receivables (customers) or payables (suppliers) by party."""
    def get(self, request):
        company, branch = self.scope(request)
        kind = request.query_params.get("kind", "receivable")
        code, prefix = ("1100", "customer:") if kind == "receivable" else ("2000", "supplier:")
        qs = JournalLine.objects.filter(account__company=company, account__code=code, party__startswith=prefix)
        if branch:
            qs = qs.filter(entry__branch=branch)
        rows = []
        from apps.customers.models import Customer
        from apps.suppliers.models import Supplier
        M = Customer if kind == "receivable" else Supplier
        for r in qs.values("party").annotate(d=Sum("debit"), c=Sum("credit")):
            pid = r["party"].split(":", 1)[1]
            amt = (r["d"] - r["c"]) if kind == "receivable" else (r["c"] - r["d"])
            if amt:
                m = M.objects.filter(pk=pid).first()
                rows.append({"party_id": pid, "name": m.name if m else pid, "outstanding": amt})
        return Response({"rows": rows, "total": sum((x["outstanding"] for x in rows), D(0))})


class AuditLogView(_Report):
    module = "users"

    def get(self, request):
        qs = AuditLog.objects.filter(company=request.user.company).select_related("user")[:200]
        return Response([{"id": a.id, "when": a.created_at, "user": a.user.username if a.user else "", "action": a.action,
                          "model": a.model, "summary": a.summary} for a in qs])
