from rest_framework.routers import DefaultRouter
from .views import JobCardViewSet, KarigarVS, PaymentViewSet, TxnViewSet

router = DefaultRouter()
router.register("karigars/jobcards", JobCardViewSet, basename="jobcard")
router.register("karigars/transactions", TxnViewSet, basename="karigar-txn")
router.register("karigars/payments", PaymentViewSet, basename="karigar-payment")
router.register("karigars", KarigarVS, basename="karigar")
urlpatterns = router.urls
