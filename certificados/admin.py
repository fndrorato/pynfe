from django.contrib import admin
from .models import Certificado

@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = ('cnpj', 'name', 'password', 'validate', 'created_at', 'updated_at')
    search_fields = ('cnpj',)