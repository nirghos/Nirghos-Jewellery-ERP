from rest_framework.routers import DefaultRouter
from .views import AdvanceViewSet, AttendanceViewSet, EmployeeViewSet, LeaveViewSet, PayslipViewSet

router = DefaultRouter()
router.register("hr/employees", EmployeeViewSet, basename="employee")
router.register("hr/attendance", AttendanceViewSet, basename="attendance")
router.register("hr/leaves", LeaveViewSet, basename="leave")
router.register("hr/advances", AdvanceViewSet, basename="advance")
router.register("hr/payslips", PayslipViewSet, basename="payslip")
urlpatterns = router.urls
