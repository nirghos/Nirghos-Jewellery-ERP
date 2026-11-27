from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views as v

router = DefaultRouter()
router.register("accounting/accounts", v.AccountViewSet, basename="account")
router.register("accounting/entries", v.EntryViewSet, basename="entry")
urlpatterns = [
    path("accounting/trial-balance/", v.TrialBalance.as_view()),
    path("accounting/profit-loss/", v.ProfitLoss.as_view()),
    path("accounting/balance-sheet/", v.BalanceSheet.as_view()),
    path("accounting/ledger/", v.Ledger.as_view()),
    path("accounting/daybook/", v.Daybook.as_view()),
    path("accounting/parties/", v.Parties.as_view()),
    path("settings/audit-logs/", v.AuditLogView.as_view()),
] + router.urls
