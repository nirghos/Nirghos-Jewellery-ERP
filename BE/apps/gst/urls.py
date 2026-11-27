from django.urls import path
from . import views as v

urlpatterns = [
    path("gst/sales-register/", v.SalesRegister.as_view()),
    path("gst/purchase-register/", v.PurchaseRegister.as_view()),
    path("gst/hsn-summary/", v.HsnSummary.as_view()),
    path("gst/gstr1/", v.Gstr1.as_view()),
    path("gst/gstr3b/", v.Gstr3b.as_view()),
    path("gst/reconciliation/", v.Reconciliation.as_view()),
]
