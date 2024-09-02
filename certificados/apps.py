from django.apps import AppConfig


class CertificadosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'certificados'
    
    def ready(self):
        import certificados.signals    
