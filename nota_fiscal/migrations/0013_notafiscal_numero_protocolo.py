# Generated by Django 5.0.7 on 2024-09-02 12:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nota_fiscal', '0012_notacancelada_protocolo'),
    ]

    operations = [
        migrations.AddField(
            model_name='notafiscal',
            name='numero_protocolo',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
    ]
