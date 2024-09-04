import os
from pathlib import Path
from django.core.mail import EmailMessage
from django.conf import settings
from django.http import JsonResponse
from certificados.models import Certificado, Email, EmailEnviado
from nota_fiscal.models import NotaFiscal


class EmailSender:

    def __init__(self, cnpj, chave_nota_fiscal):
        self.cnpj = cnpj
        self.chave_nota_fiscal = chave_nota_fiscal

    def get_emails(self):
        try:
            certificado = Certificado.objects.get(cnpj=self.cnpj)
            emails = Email.objects.filter(cnpj=certificado).values_list('email', flat=True)
            return emails
        except Certificado.DoesNotExist:
            return []
        
    def get_attachments(self):
        try:
            nota_fiscal = NotaFiscal.objects.get(chave=self.chave_nota_fiscal)
            xml_file = Path(settings.MEDIA_ROOT) / 'xml' / nota_fiscal.xml_file_name
            pdf_file = Path(settings.MEDIA_ROOT) / 'danfe' / nota_fiscal.pdf_file_name
            return [xml_file, pdf_file]
        except NotaFiscal.DoesNotExist:
            return []        

    def send_email(self, subject, message, attachments=None):
        emails = self.get_emails()
        if not emails:
            return {
                "success": False,
                "message": "Nenhum email cadastrado para o CNPJ fornecido."
            }

        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=emails
        )

        # Anexar arquivos, se houver
        if attachments:
            for attachment in attachments:
                if os.path.exists(attachment):
                    email.attach_file(attachment)

        email.send()
        return {
            "success": True,
            "message": f"E-mail enviado para: {', '.join(emails)}"
        }

    def send_nota_fiscal_email(self):
        try:
            nota_fiscal = NotaFiscal.objects.get(chave=self.chave_nota_fiscal)
            certificado = Certificado.objects.get(cnpj=self.cnpj)
            subject = f'Nota Fiscal Emitida: {nota_fiscal.numero}'
            message = f"""
            Olá {certificado.name}, segue em anexo os arquivos referentes à nota fiscal:
            Número da Nota Fiscal: {nota_fiscal.numero}
            Chave da Nota Fiscal: {self.chave_nota_fiscal}
            """
            attachments = self.get_attachments()
            return self.send_email(subject, message, attachments)
        except NotaFiscal.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "Nota fiscal não encontrada para a chave fornecida."
            })
