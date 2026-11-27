from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    OWNER = "owner", "Owner"
    BRANCH_MANAGER = "branch_manager", "Branch Manager"
    ACCOUNTANT = "accountant", "Accountant"
    SALES_MANAGER = "sales_manager", "Sales Manager"
    SALES_STAFF = "sales_staff", "Sales Staff"
    STOCK_MANAGER = "stock_manager", "Stock Manager"
    PURCHASE_MANAGER = "purchase_manager", "Purchase Manager"
    KARIGAR_MANAGER = "karigar_manager", "Karigar Manager"
    HR_MANAGER = "hr_manager", "HR Manager"
    AUDITOR = "auditor", "Auditor"


class User(AbstractUser):
    company = models.ForeignKey("companies.Company", on_delete=models.PROTECT, null=True, blank=True, related_name="users")
    branch = models.ForeignKey("companies.Branch", on_delete=models.SET_NULL, null=True, blank=True, related_name="users")
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.SALES_STAFF)
    phone = models.CharField(max_length=20, blank=True)

    @property
    def all_branches(self):
        return self.role in (Role.SUPER_ADMIN, Role.OWNER, Role.ACCOUNTANT, Role.AUDITOR) or self.is_superuser
