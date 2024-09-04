from django.contrib import admin
from .models import Certificado, Email, EmailEnviado

@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = ('cnpj', 'name', 'password', 'validate', 'created_at', 'updated_at')
    search_fields = ('cnpj',)
    
class EmailAdmin(admin.ModelAdmin):
    list_display = ('cnpj', 'email')  # Colunas que serão exibidas na lista de objetos
    search_fields = ('cnpj__cnpj', 'email')  # Campos de pesquisa

class EmailEnviadoAdmin(admin.ModelAdmin):
    list_display = ('cnpj', 'numero', 'chave', 'emails', 'created_at')
    search_fields = ('cnpj__cnpj', 'numero', 'chave', 'emails')
    list_filter = ('created_at',)  # Filtros na barra lateral

admin.site.register(Email, EmailAdmin)
admin.site.register(EmailEnviado, EmailEnviadoAdmin)
    