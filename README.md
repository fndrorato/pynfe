# API de Emissão de Nota Fiscal

Bem-vindo à documentação da API para emissão de nota fiscal. Esta API foi desenvolvida em Python e fornece múltiplas rotas para gerenciar notas fiscais, desde a criação até o cancelamento.

## Tecnologias Utilizadas

- **Linguagem**: Python
- **Framework**: Django
- **Gerenciamento de Dependências**: pip

---

## Rotas Disponíveis

### 1. Criar Notas Fiscais
**Endpoint**: `/nota-fiscal/`  
**Métodos**: `GET`, `POST`

- `POST`: Cria uma nova nota fiscal.

### 2. Buscar Retorno de Nota Fiscal
**Endpoint**: `/nota-fiscal/buscar-retorno/`  
**Método**: `POST`

- Busca o retorno da SEFAZ para uma nota fiscal específica.

### 3. Consultar Nota Fiscal
**Endpoint**: `/nota-fiscal/consultar/`  
**Método**: `POST`

- Consulta o status de uma nota fiscal.

### 4. Emitir Carta de Correção Eletrônica (CC-e)
**Endpoint**: `/nota-fiscal/cce/`  
**Método**: `POST`

- Permite enviar uma Carta de Correção Eletrônica para uma nota fiscal previamente emitida.

### 5. Cancelar Nota Fiscal
**Endpoint**: `/nota-fiscal/cancelar/`  
**Método**: `POST`

- Realiza o cancelamento de uma nota fiscal.

### 6. Enviar Nota Fiscal por E-mail
**Endpoint**: `/nota-fiscal/email/`  
**Método**: `POST`

- Envia a nota fiscal para o e-mail do cliente.

---

## Exemplo de Configuração

Adicione as rotas no seu arquivo `urls.py` da seguinte forma:

```python
from django.urls import path
from . import views

urlpatterns = [
    path('nota-fiscal/', views.NotaFiscalView.as_view(), name='nota-fiscal-list-create'),
    path('nota-fiscal/buscar-retorno/', views.NotaFiscalDetailView.as_view(), name='nota-fiscal-detail'),
    path('nota-fiscal/consultar/', views.NotaFiscalConsultarView.as_view(), name='nota-fiscal-detail'),
    path('nota-fiscal/cce/', views.NotaFiscalCCeView.as_view(), name='nota-fiscal-cce'),
    path('nota-fiscal/cancelar/', views.NotaFiscalCancelarView.as_view(), name='nota-fiscal-cancelar'),
    path('nota-fiscal/email/', views.NotaFiscalSendEmailView.as_view(), name='nota-fiscal-enviar-email'),
]
```

---

## Exemplo de Requisições

### Criação de Nota Fiscal
**POST** `/nota-fiscal/`
```json
{
  "tipo_ambiente": 1,
  "emitente": {
    "razao_social": "NOME DO EMISSOR",
    "nome_fantasia": "NOME FANTASIA DO EMISSOR",
    "cnpj": "78945612308521",
    "codigo_de_regime_tributario": "1",
    "inscricao_estadual": "9999999",
    "inscricao_municipal": "",
    "cnae_fiscal": "",
    "endereco_logradouro": "AVENIDA RIO VERDE",
    "endereco_numero": "1",
    "endereco_bairro": "VILA SAO TOMAZ",
    "endereco_municipio": "Goiânia",
    "endereco_uf": "GO",
    "endereco_cep": "74915515",
    "endereco_pais": "1058",
    "endereco_telefone": "1133333333"
  },
  "cliente": {
    "razao_social": "NOME DO CLIENTE",
    "email": "",
    "tipo_documento": "CPF",
    "numero_documento": "112233333",
    "indicador_ie": 9,
    "inscricao_estadual": "",
    "isento_icms": true,
    "endereco_logradouro": "RUA SAO PAULO",
    "endereco_numero": "269",
    "endereco_complemento": "",
    "endereco_bairro": "CENTRO",
    "endereco_cep": "76500000",
    "endereco_pais": 1058,
    "endereco_uf": "GO",
    "endereco_municipio": "Santa Terezinha de Goiás",
    "endereco_cod_municipio": "5219704",
    "endereco_telefone": "11888888888"
  },
  "uf": "GO",
  "natureza_operacao": "VENDA DE MERCADORIA ADQUIRIDA",
  "forma_pagamento": 0,
  "tipo_pagamento": 1,
  "modelo": 55,
  "serie": "1",
  "numero_nf": "978",
  "data_emissao": "2024-09-17T13:39:49",
  "data_saida_entrada": "2024-09-17T13:39:49",
  "tipo_documento": 1,
  "municipio": "5208707",
  "tipo_impressao_danfe": 1,
  "forma_emissao": "1",
  "cliente_final": 1,
  "indicador_destino": 1,
  "indicador_presencial": 1,
  "finalidade_emissao": "1",
  "processo_emissao": "0",
  "transporte_modalidade_frete": "9",
  "informacoes_adicionais_interesse_fisco": "",
  "informacoes_complementares_interesse_contribuinte": "",
  "totais_tributos_aproximado": 0,
  "valor_total_nota_fiscal": "1530",
  "produtos": [
    {
      "descricao": "Corsario Garota Saudavel P",
      "codigo": "0175002",
      "ncm": "61046900",
      "cfop": "5102",
      "unidade_comercial": "UN",
      "ean": "SEM GTIN",
      "ean_tributavel": "SEM GTIN",
      "quantidade_comercial": "5",
      "valor_unitario_comercial": "50.00",
      "valor_total_bruto": "250.00",
      "total_frete": "0.00",
      "unidade_tributavel": "UN",
      "quantidade_tributavel": "5",
      "valor_unitario_tributavel": "50.00",
      "ind_total": 1,
      "icms_modalidade": "102",
      "icms_origem": 0,
      "icms_csosn": "102",
      "pis_modalidade": "07",
      "cofins_modalidade": "07",
      "valor_tributos_aprox": 0
    },
    {
      "descricao": "Abdominal Strap (Cinta Abdominal) Fit Line Preta GG",
      "codigo": "102014002",
      "ncm": "62123000",
      "cfop": "5102",
      "unidade_comercial": "UN",
      "ean": "SEM GTIN",
      "ean_tributavel": "SEM GTIN",
      "quantidade_comercial": "1",
      "valor_unitario_comercial": "430.00",
      "valor_total_bruto": "430.00",
      "total_frete": "0.00",
      "unidade_tributavel": "UN",
      "quantidade_tributavel": "1",
      "valor_unitario_tributavel": "430.00",
      "ind_total": 1,
      "icms_modalidade": "102",
      "icms_origem": 0,
      "icms_csosn": "102",
      "pis_modalidade": "07",
      "cofins_modalidade": "07",
      "valor_tributos_aprox": 0
    },
    {
      "descricao": "Bracelete NEW FIR Style - Preto - Kit Bracelete Style M/G",
      "codigo": "1522",
      "ncm": "39262000",
      "cfop": "5102",
      "unidade_comercial": "UN",
      "ean": "SEM GTIN",
      "ean_tributavel": "SEM GTIN",
      "quantidade_comercial": "1",
      "valor_unitario_comercial": "90.00",
      "valor_total_bruto": "90.00",
      "total_frete": "0.00",
      "unidade_tributavel": "UN",
      "quantidade_tributavel": "1",
      "valor_unitario_tributavel": "90.00",
      "ind_total": 1,
      "icms_modalidade": "102",
      "icms_origem": 0,
      "icms_csosn": "102",
      "pis_modalidade": "07",
      "cofins_modalidade": "07",
      "valor_tributos_aprox": 0
    },
    {
      "descricao": "Bracelete NEW FIR Style - Azul - Kit Bracelete Style M/G",
      "codigo": "1525",
      "ncm": "39262000",
      "cfop": "5102",
      "unidade_comercial": "UN",
      "ean": "SEM GTIN",
      "ean_tributavel": "SEM GTIN",
      "quantidade_comercial": "1",
      "valor_unitario_comercial": "90.00",
      "valor_total_bruto": "90.00",
      "total_frete": "0.00",
      "unidade_tributavel": "UN",
      "quantidade_tributavel": "1",
      "valor_unitario_tributavel": "90.00",
      "ind_total": 1,
      "icms_modalidade": "102",
      "icms_origem": 0,
      "icms_csosn": "101",
      "pis_modalidade": "07",
      "cofins_modalidade": "07",
      "valor_tributos_aprox": 0
    },
    {
      "descricao": "BRACELETE DOUBLE FIR AZUL COM PRETO G/GG",
      "codigo": "1614",
      "ncm": "94042900",
      "cfop": "5102",
      "unidade_comercial": "UN",
      "ean": "SEM GTIN",
      "ean_tributavel": "SEM GTIN",
      "quantidade_comercial": "1",
      "valor_unitario_comercial": "210.00",
      "valor_total_bruto": "210.00",
      "total_frete": "0.00",
      "unidade_tributavel": "UN",
      "quantidade_tributavel": "1",
      "valor_unitario_tributavel": "210.00",
      "ind_total": 1,
      "icms_modalidade": "102",
      "icms_origem": 0,
      "icms_csosn": "102",
      "pis_modalidade": "07",
      "cofins_modalidade": "07",
      "valor_tributos_aprox": 0
    },
    {
      "descricao": "CONDICIONADOR REVIVE FIR",
      "codigo": "1615",
      "ncm": "94039090",
      "cfop": "5102",
      "unidade_comercial": "UN",
      "ean": "SEM GTIN",
      "ean_tributavel": "SEM GTIN",
      "quantidade_comercial": "2",
      "valor_unitario_comercial": "55.00",
      "valor_total_bruto": "110.00",
      "total_frete": "0.00",
      "unidade_tributavel": "UN",
      "quantidade_tributavel": "2",
      "valor_unitario_tributavel": "55.00",
      "ind_total": 1,
      "icms_modalidade": "102",
      "icms_origem": 0,
      "icms_csosn": "102",
      "pis_modalidade": "07",
      "cofins_modalidade": "07",
      "valor_tributos_aprox": 0
    },
    {
      "descricao": "COTOVELEIRA",
      "codigo": "1616",
      "ncm": "94042900",
      "cfop": "5102",
      "unidade_comercial": "UN",
      "ean": "SEM GTIN",
      "ean_tributavel": "SEM GTIN",
      "quantidade_comercial": "1",
      "valor_unitario_comercial": "80.00",
      "valor_total_bruto": "80.00",
      "total_frete": "0.00",
      "unidade_tributavel": "UN",
      "quantidade_tributavel": "1",
      "valor_unitario_tributavel": "80.00",
      "ind_total": 1,
      "icms_modalidade": "102",
      "icms_origem": 0,
      "icms_csosn": "102",
      "pis_modalidade": "07",
      "cofins_modalidade": "07",
      "valor_tributos_aprox": 0
    },
    {
      "descricao": "LUVA P",
      "codigo": "1617",
      "ncm": "94042900",
      "cfop": "5102",
      "unidade_comercial": "UN",
      "ean": "SEM GTIN",
      "ean_tributavel": "SEM GTIN",
      "quantidade_comercial": "1",
      "valor_unitario_comercial": "70.00",
      "valor_total_bruto": "70.00",
      "total_frete": "0.00",
      "unidade_tributavel": "UN",
      "quantidade_tributavel": "1",
      "valor_unitario_tributavel": "70.00",
      "ind_total": 1,
      "icms_modalidade": "102",
      "icms_origem": 0,
      "icms_csosn": "102",
      "pis_modalidade": "07",
      "cofins_modalidade": "07",
      "valor_tributos_aprox": 0
    },
    {
      "descricao": "BRACELETE YOUNG FIR",
      "codigo": "1618",
      "ncm": "94042900",
      "cfop": "5102",
      "unidade_comercial": "UN",
      "ean": "SEM GTIN",
      "ean_tributavel": "SEM GTIN",
      "quantidade_comercial": "2",
      "valor_unitario_comercial": "100.00",
      "valor_total_bruto": "200.00",
      "total_frete": "0.00",
      "unidade_tributavel": "UN",
      "quantidade_tributavel": "2",
      "valor_unitario_tributavel": "100.00",
      "ind_total": 1,
      "icms_modalidade": "102",
      "icms_origem": 0,
      "icms_csosn": "102",
      "pis_modalidade": "07",
      "cofins_modalidade": "07",
      "valor_tributos_aprox": 0
    }
  ],
  "transportadora": [
    
  ],
  "pagamentos": [
    {
      "t_pag": "01",
      "v_pag": "1530.00",
      "tp_integra": "2",
      "ind_pag": "0"
    }
  ],
  "responsavel_tecnico": {
    "cnpj": "12345678901234",
    "contato": "FERNANDO RORATO",
    "email": "fernando.rorato@gmail.com",
    "fone": "11999999999"
  }
}
```

### Consultar Nota Fiscal
**POST** `/nota-fiscal/consultar/`
```json
{
    "cnpj": "78945612308521",
    "tipo_ambiente": 1,
    "chave_acesso": "11241021277052000180550010000000471437002277"
}
```

---

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/fndrorato/pynfe.git
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Execute as migrações:
   ```bash
   python manage.py migrate
   ```

4. Inicie o servidor:
   ```bash
   python manage.py runserver
   ```

---

## Contribuições

Contribuições são bem-vindas! Por favor, envie um pull request com suas melhorias ou correções.

---

## Licença

Este projeto está licenciado sob a Licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---

## Contato

Caso tenha dúvidas ou precise de suporte, entre em contato:
- **E-mail**: fernando.rorato@gmail.com

