from rest_framework import serializers, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.accounts.permissions import ModulePermission
from .models import Branch, Company


class CompanySer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "gstin", "pan", "address", "phone", "gst_rate", "hallmark_charge"]


class BranchSer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "name", "code", "address", "is_active"]

    def validate_code(self, v):
        qs = Branch.objects.filter(company_id=self.context["request"].user.company_id, code=v)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Branch code already exists")
        return v


class BranchViewSet(viewsets.ModelViewSet):
    module = "company"
    permission_classes = [ModulePermission]
    serializer_class = BranchSer
    queryset = Branch.objects.all()
    pagination_class = None

    def get_queryset(self):
        return super().get_queryset().filter(company_id=self.request.user.company_id)

    def perform_create(self, s):
        s.save(company_id=self.request.user.company_id)


class CompanyView(APIView):
    module = "company"
    permission_classes = [ModulePermission]

    def get(self, request):
        return Response(CompanySer(request.user.company).data)

    def patch(self, request):
        s = CompanySer(request.user.company, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)
