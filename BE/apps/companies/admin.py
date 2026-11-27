from django.contrib import admin
from .models import Branch, Company

admin.site.register([Company, Branch])
