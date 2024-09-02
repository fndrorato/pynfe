# Generated by Django 5.0.7 on 2024-09-02 12:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('certificados', '0006_certificado_uf'),
        ('nota_fiscal', '0010_cartacorrecao_pdf_file_name_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cartacorrecao',
            options={'verbose_name': 'Carta de Correção', 'verbose_name_plural': 'Cartas de Correções'},
        ),
        migrations.CreateModel(
            name='NotaCancelada',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_emissao', models.DateTimeField()),
                ('justificativa', models.CharField(max_length=255)),
                ('status', models.CharField(blank=True, default='', max_length=5, null=True)),
                ('motivo', models.CharField(blank=True, default='', max_length=255, null=True)),
                ('retorno', models.TextField(blank=True, default='', null=True)),
                ('chave_nota_Fiscal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nota_fiscal.notafiscal', to_field='chave_nota_fiscal')),
                ('cnpj', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='emissorcancelada', to='certificados.certificado')),
            ],
            options={
                'verbose_name': 'Nota Cancelada',
                'verbose_name_plural': 'Notas Canceladas',
            },
        ),
    ]
