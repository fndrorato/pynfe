from django.db import models
from certificados.models import Certificado
    

class NotaFiscal(models.Model):
    numero = models.CharField(max_length=20)
    data_emissao = models.DateTimeField()
    destinatario = models.CharField(max_length=255)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    chave_nota_fiscal = models.CharField(max_length=255, unique=True)
    numero_protocolo = models.CharField(max_length=255, default='', null=True, blank=True)
    xml = models.TextField(blank=True, null=True)  # Para armazenar o XML da nota fiscal
    cnpj = models.ForeignKey(Certificado, on_delete=models.CASCADE, related_name='emissao')
    status = models.CharField(max_length=5, default='', blank=True, null=True)
    xml_file_name = models.CharField(max_length=255, default='', blank=True, null=True)
    pdf_file_name = models.CharField(max_length=255, default='', blank=True, null=True)

    def __str__(self):
        return f'Nota Fiscal {self.numero}'
    
class CartaCorrecao(models.Model):
    cnpj = models.ForeignKey(Certificado, on_delete=models.CASCADE, related_name='emissor')
    chave_nota_fiscal = models.ForeignKey(NotaFiscal, on_delete=models.CASCADE, to_field='chave_nota_fiscal')
    data_emissao = models.DateTimeField()
    n_seq_evento = models.IntegerField()
    correcao = models.CharField(max_length=255) 
    status = models.CharField(max_length=5, default='', blank=True, null=True) 
    motivo = models.CharField(max_length=255, default='', blank=True, null=True) 
    retorno = models.TextField(null=True, blank=True, default='')
    xml_file_name = models.CharField(max_length=255, default='', blank=True, null=True)
    pdf_file_name = models.CharField(max_length=255, default='', blank=True, null=True)    
    
    class Meta:
        verbose_name = "Carta de Correção"
        verbose_name_plural = "Cartas de Correções"
        
class NotaCancelada(models.Model):
    cnpj = models.ForeignKey(Certificado, on_delete=models.CASCADE, related_name='emissorcancelada')
    chave_nota_fiscal = models.ForeignKey(NotaFiscal, on_delete=models.CASCADE, to_field='chave_nota_fiscal')
    protocolo = models.CharField(max_length=50)
    data_emissao = models.DateTimeField()
    justificativa = models.CharField(max_length=255) 
    status = models.CharField(max_length=5, default='', blank=True, null=True) 
    motivo = models.CharField(max_length=255, default='', blank=True, null=True) 
    retorno = models.TextField(null=True, blank=True, default='')
    
    class Meta:
        verbose_name = "Nota Cancelada"
        verbose_name_plural = "Notas Canceladas"        
    
class HistoricoNotaFiscal(models.Model):
    cnpj = models.ForeignKey(Certificado, on_delete=models.CASCADE, related_name='historicos')
    numero = models.CharField(max_length=20)
    cstat = models.CharField(max_length=3, null=True, blank=True)
    xmotivo = models.CharField(max_length=255, null=True, blank=True)
    xml_string = models.TextField(null=True, blank=True, default='')
    resposta_string = models.TextField(null=True, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cnpj} - {self.numero} - {self.created_at}"

    class Meta:
        verbose_name = "Histórico da Nota Fiscal"
        verbose_name_plural = "Históricos das Notas Fiscais"    

