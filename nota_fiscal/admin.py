from django.contrib import admin
from .models import NotaFiscal, HistoricoNotaFiscal,  CartaCorrecao, NotaCancelada

@admin.register(NotaFiscal)
class NotaFiscalAdmin(admin.ModelAdmin):
    list_display = ('numero', 'cnpj', 'status', 'data_emissao', 'destinatario', 'valor_total', 'chave_nota_fiscal')
    search_fields = ('numero', 'cnpj', 'destinatario', 'status', 'chave_nota_fiscal')
    list_filter = ('data_emissao', 'cnpj', 'status', )
    date_hierarchy = 'data_emissao'
    
@admin.register(CartaCorrecao)
class CartaCorrecaoAdmin(admin.ModelAdmin):
    list_display = ('chave_nota_fiscal', 'cnpj', 'data_emissao', 'correcao', 'n_seq_evento', 'status')
    search_fields = ('chave_nota_fiscal', 'cnpj', 'correcao', 'status')
    list_filter = ('data_emissao', 'cnpj', 'status', )
    date_hierarchy = 'data_emissao'   
    
@admin.register(NotaCancelada)
class NotaCanceladaAdmin(admin.ModelAdmin):
    list_display = ('chave_nota_fiscal', 'cnpj', 'data_emissao', 'justificativa', 'status')
    search_fields = ('chave_nota_fiscal', 'cnpj', 'justificativa', 'status')
    list_filter = ('data_emissao', 'cnpj', 'status', )
    date_hierarchy = 'data_emissao'      

@admin.register(HistoricoNotaFiscal)
class HistoricoNotaFiscalAdmin(admin.ModelAdmin):
    list_display = ('cnpj', 'numero', 'cstat', 'xmotivo', 'created_at')
    search_fields = ('cnpj', 'numero', 'cstat', 'xmotivo')
    list_filter = ('created_at', 'cstat')
    date_hierarchy = 'created_at'
