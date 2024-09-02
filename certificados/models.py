from django.db import models

class Certificado(models.Model):
    cnpj = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=255)
    uf = models.CharField(max_length=2, default='', null=True, blank=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    file = models.FileField(upload_to='certificados/')
    password = models.CharField(max_length=255)
    validate = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.cnpj


    def to_dict(self):
        return {
            'cnpj': self.cnpj,
            'password': self.password,
            'validate': self.validate.isoformat(),  # Formato ISO para datas
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }