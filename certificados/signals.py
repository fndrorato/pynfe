import datetime
from django.db.models.signals import post_save
from django.db.models import Sum
from django.dispatch import receiver
from django.conf import settings
from pathlib import Path
from OpenSSL import crypto
from certificados.models import Certificado
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend


@receiver(post_save, sender=Certificado)
def update_certificate_validate(sender, instance, **kwargs):
    # Verifica se o arquivo do certificado foi enviado
    if instance.file:
        try:
            # Lê o conteúdo do arquivo do certificado
            certificado_path = Path(settings.MEDIA_ROOT) / instance.file.name
            # Carrega o certificado protegido por senha
            with open(certificado_path, 'rb') as cert_file:
                p12_data = cert_file.read()

            # Desempacota o arquivo PKCS#12
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                p12_data, instance.password.encode(), backend=default_backend()
            )

            # Obtém as datas de validade
            validade_fim = certificate.not_valid_after_utc.date() 
            # Atualiza o campo validate e salva, evitando loops infinitos
            Certificado.objects.filter(pk=instance.pk).update(validate=validade_fim)
        except Exception as e:
            print(f"Erro ao processar o certificado: {e}")