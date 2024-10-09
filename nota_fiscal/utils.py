import xmltodict
import datetime
import os
from pathlib import Path
from django.utils import timezone
from django.conf import settings
from pynfe.entidades.cliente import Cliente
from pynfe.entidades.emitente import Emitente
from pynfe.entidades.transportadora import Transportadora
from pynfe.entidades.notafiscal import NotaFiscal
from pynfe.entidades.fonte_dados import _fonte_dados
from pynfe.processamento.serializacao import SerializacaoXML
from pynfe.processamento.validacao import Validacao
from pynfe.utils.flags import CODIGO_BRASIL
from decimal import Decimal
from nota_fiscal.models import (
    NotaFiscal as NotaFiscalModel, 
    HistoricoNotaFiscal, 
    CartaCorrecao, 
    NotaCancelada
)
from certificados.models import Certificado
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from datetime import datetime
from lxml import etree
import xml.etree.ElementTree as ET


def salvar_historico_nota_fiscal(cnpj, numero_nfe, cStat, xMotivo, xml_content, resposta_string = ''):
    try:
        # Busca o Certificado com base no CNPJ
        certificado = Certificado.objects.get(cnpj=cnpj)
        
        # Cria uma nova instância de HistoricoNotaFiscal com os parâmetros recebidos
        historico = HistoricoNotaFiscal(
            cnpj=certificado,
            numero=numero_nfe,
            cstat=cStat,
            xmotivo=xMotivo,
            xml_string=xml_content,
            resposta_string=resposta_string
        )
        
        # Salva a instância no banco de dados
        historico.save()

        return historico
    
    except Certificado.DoesNotExist:
        print(f"Certificado com CNPJ {cnpj} não encontrado.")
        return None

def salvar_nota_fiscal(data):
    try:
        # Busca o Certificado com base no CNPJ
        certificado = Certificado.objects.get(cnpj=data['cnpj'])
        
        # Cria uma nova instância de NotaFiscal com os parâmetros recebidos
        nota_fiscal = NotaFiscalModel(
            cnpj=certificado,
            numero=data['numero_nfe'],
            destinatario=data['destinatario'],
            valor_total=data['valor_total'],
            chave_nota_fiscal=data['chave_nota_fiscal'],
            numero_protocolo=data['numero_protocolo'],
            xml=data['xml_content'],
            xml_file_name=data['xml_file'],
            pdf_file_name=data['pdf_file'],
            status=data['status_nfe'],
            data_emissao=timezone.now(),  # Adiciona a data e hora atual
        )
        
        # Salva a instância no banco de dados
        nota_fiscal.save()

        return nota_fiscal
    
    except Certificado.DoesNotExist:
        print(f"Certificado com CNPJ {data['cnpj']} não encontrado.")
        return None

def salvar_carta_correcao(data):
    try:
        # Busca o Certificado com base no CNPJ
        certificado = Certificado.objects.get(cnpj=data['cnpj'])
        chave = NotaFiscalModel.objects.get(chave_nota_fiscal=data['chave'])
        
        # Cria uma nova instância de CartaCorrecao com os parâmetros recebidos
        carta_correcao = CartaCorrecao(
            cnpj=certificado,
            chave_nota_Fiscal=chave,
            data_emissao=timezone.now(),            
            n_seq_evento=data['n_seq_evento'],
            correcao=data['correcao'],
            status=data['status'],
            motivo=data['motivo'],
            retorno=data['xml_retorno'],
            xml_file_name=data['xml_file'],
            pdf_file_name=data['pdf_file'],
        )
        
        # Salva a instância no banco de dados
        carta_correcao.save()

        return carta_correcao
    
    except Certificado.DoesNotExist:
        print(f"Certificado com CNPJ {data['cnpj']} não encontrado.")
        return None
    
    except NotaFiscalModel.DoesNotExist:
        print(f"Chave da NFe {data['chave']} não encontrada.")
        return None  
    
def salvar_cancelamento(data):
    try:
        # Busca o Certificado com base no CNPJ
        certificado = Certificado.objects.get(cnpj=data['cnpj'])
        chave = NotaFiscalModel.objects.get(chave_nota_fiscal=data['chave'])
        
        # Cria uma nova instância de CartaCorrecao com os parâmetros recebidos
        nota_cancelada = NotaCancelada(
            cnpj=certificado,
            chave_nota_Fiscal=chave,
            data_emissao=timezone.now(),            
            protocolo=data['numero_protocolo'],
            justificativa=data['justificativa'],
            status=data['status'],
            motivo=data['motivo'],
            retorno=data['xml_retorno'],
        )
        
        # Salva a instância no banco de dados
        nota_cancelada.save()

        return nota_cancelada
    
    except Certificado.DoesNotExist:
        print(f"Certificado com CNPJ {data['cnpj']} não encontrado.")
        return None
    
    except NotaFiscalModel.DoesNotExist:
        print(f"Chave da NFe {data['chave']} não encontrada.")
        return None       

def verificar_validade_certificado(certificado_path, senha):
    try:
        # Carrega o certificado protegido por senha
        with open(certificado_path, 'rb') as cert_file:
            p12_data = cert_file.read()

        # Desempacota o arquivo PKCS#12
        private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
            p12_data, senha.encode(), backend=default_backend()
        )

        # Obtém as datas de validade
        validade_inicio = certificate.not_valid_before_utc.date() 
        validade_fim = certificate.not_valid_after_utc.date() 

        return validade_inicio, validade_fim
    except Exception as e:
        print(f"Erro ao carregar ou verificar o certificado: {e}")
        return None

def extrair_cstat_xmotivo(xml_string):
    """
    Extrai as informações de 'cStat' e 'xMotivo' de um dicionário, independente da estrutura.
    
    Args:
        data (dict): O dicionário que contém os dados do XML convertido.
    
    Returns:
        dict: Um dicionário com as chaves 'cStat' e 'xMotivo' e seus respectivos valores.
    """
    # Inicializando as variáveis de retorno com valores padrão
    cStat = None
    xMotivo = None
    data = xmltodict.parse(xml_string)

    try:
        # Verifica se a chave principal pode ser 'env:Envelope' ou 'soap:Envelope'
        envelope_key = next((key for key in data if key.endswith(':Envelope')), None)
        if not envelope_key:
            raise KeyError("Chave 'Envelope' não encontrada no dicionário.")

        # Verifica se a chave do body pode ser 'env:Body' ou 'soap:Body'
        body_key = next((key for key in data[envelope_key] if key.endswith(':Body')), None)
        if not body_key:
            raise KeyError("Chave 'Body' não encontrada no dicionário.")

        # Acessa o corpo da mensagem
        body = data[envelope_key][body_key]

        # Extraindo informações de retConsStatServ, se existirem
        if 'nfeResultMsg' in body and 'retConsStatServ' in body['nfeResultMsg']:
            retConsStatServ = body['nfeResultMsg']['retConsStatServ']
            cStat = retConsStatServ.get('cStat')
            xMotivo = retConsStatServ.get('xMotivo')
            return cStat, xMotivo

    except Exception as e:
        # Pode-se implementar logs ou tratamento de exceções mais sofisticado aqui
        print(f"Erro ao extrair dados: {e}")  
        return None, None  

def extrair_conteudo_nfe_result(xml_string):
    # Converta a string XML para bytes
    xml_bytes = xml_string.encode('utf-8')
    # Parse the XML bytes
    root = etree.fromstring(xml_bytes)

    # Define the namespaces
    namespaces = {
        'soap': 'http://www.w3.org/2003/05/soap-envelope',
        'nfe': 'http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4',
        'ret': 'http://www.portalfiscal.inf.br/nfe',
        'nferet': 'http://www.portalfiscal.inf.br/nfe/wsdl/NFeRetAutorizacao4'
    }
    nprot_inf_prot = None
    # Encontre o <nfeResultMsg>
    nfe_result_msg = root.find('.//nfe:nfeResultMsg', namespaces)
    if nfe_result_msg is None:
        nfe_result_msg = root.find('.//nferet:nfeResultMsg', namespaces)
        
    if nfe_result_msg is not None:
        # Verificar se o XML é de retorno de envio ou de consulta
        ret_envi_nfe = nfe_result_msg.find('.//ret:retEnviNFe', namespaces)
        if ret_envi_nfe is None:
            ret_envi_nfe = nfe_result_msg.find('.//ret:retConsReciNFe', namespaces)
        
        if ret_envi_nfe is not None:
            # Extrair o cStat e o xMotivo
            cstat_ret_envi = ret_envi_nfe.find('ret:cStat', namespaces).text
            xmotivo_ret_envi = ret_envi_nfe.find('ret:xMotivo', namespaces).text
            print(f"cStat: {cstat_ret_envi}")
            print(f"xMotivo: {xmotivo_ret_envi}")

            # Verificar se existe o infRec e extrair nRec
            inf_rec = ret_envi_nfe.find('.//ret:infRec', namespaces)
            nrec = None
            if inf_rec is not None:
                nrec = inf_rec.find('ret:nRec', namespaces).text
                print(f"nRec (infRec): {nrec}")
            else:
                nrec = ret_envi_nfe.find('ret:nRec', namespaces)
                if nrec is not None:
                    nrec = nrec.text
                    print(f"nRec: {nrec}")

            # Verificar se existe o protNFe e extrair cStat e xMotivo do infProt
            prot_nfe = ret_envi_nfe.find('.//ret:protNFe', namespaces)
            if prot_nfe is not None:
                inf_prot = prot_nfe.find('.//ret:infProt', namespaces)
                if inf_prot is not None:
                    cstat_inf_prot = inf_prot.find('ret:cStat', namespaces).text
                    xmotivo_inf_prot = inf_prot.find('ret:xMotivo', namespaces).text
                    
                    # Verificar se o nProt existe e, caso contrário, atribuir None
                    nprot_inf_prot_elem = inf_prot.find('ret:nProt', namespaces)
                    nprot_inf_prot = nprot_inf_prot_elem.text if nprot_inf_prot_elem is not None else None

                    return cstat_ret_envi, xmotivo_ret_envi, cstat_inf_prot, xmotivo_inf_prot, nrec, nprot_inf_prot
                else:
                    return cstat_ret_envi, xmotivo_ret_envi, None, None, nrec, nprot_inf_prot
            else:
                return cstat_ret_envi, xmotivo_ret_envi, None, None, nrec, nprot_inf_prot
        else:
            return None, None, None, None, None, nprot_inf_prot
    else:
        return None, None, None, None, None, nprot_inf_prot

def extrair_cce_cancelar_cstat_xmotivo(xml_string):
    '''
    Função para extrair dados do retorno da carta de correção
    '''
    # Carrega o XML em uma árvore ElementTree
    root = ET.fromstring(xml_string)
    
    # Define o namespace
    namespace = {'ns': 'http://www.portalfiscal.inf.br/nfe'}

    # Procura pela tag infEvento dentro do namespace
    inf_eventos = root.findall('.//ns:infEvento', namespaces=namespace)
    
    # Cria uma lista para armazenar os resultados
    resultados = []

    # Itera sobre cada infEvento encontrado
    for inf_evento in inf_eventos:
        cStat = inf_evento.find('ns:cStat', namespaces=namespace).text
        xMotivo = inf_evento.find('ns:xMotivo', namespaces=namespace).text
        resultados.append((cStat, xMotivo))

    print(resultados)
    return cStat, xMotivo
    
def consulta_cadastro(certificado, cnpj, senha, uf, homologacao = True):
    certificado_path = Path(settings.MEDIA_ROOT) / certificado
    # Verifica se o arquivo realmente existe
    if not certificado_path.is_file():
        raise Exception("O arquivo do certificado não foi encontrado no caminho especificado.")

    # verificar_status_servico(uf, certificado_path, senha, homologacao)

    # Chama a função para verificar a validade
    validade = verificar_validade_certificado(certificado_path, senha)

    # Verifica se o resultado é válido e exibe as datas de validade
    if validade:
        hoje = datetime.now().date()
        validade_inicio, validade_fim = validade
        if validade_fim < hoje:
            message = f"Certificado vencido no dia {validade_fim}"
            validade_certificado = False           
            return validade_certificado, message
        else:
            validade_certificado = True
            message = f"Certificado válido até {validade_fim}"
            print(f"Validade do Certificado: {validade_inicio} a {validade_fim}")
            return validade_certificado, message
    else:
        message = "Não foi possível verificar a validade do certificado."
        validade_certificado = False
        return validade_certificado, message
    
def montar_nota_fiscal(data, uf_emitente, homologacao = True):
    # Criar instâncias de Emitente e Cliente
    emitente_data = data.get('emitente', {})
    cliente_data = data.get('cliente', {}) 
    
    emitente = Emitente(
        razao_social=emitente_data.get('razao_social', ''),
        nome_fantasia=emitente_data.get('nome_fantasia', ''),
        cnpj=emitente_data.get('cnpj', ''),
        codigo_de_regime_tributario=emitente_data.get('codigo_de_regime_tributario', ''),
        inscricao_estadual=emitente_data.get('inscricao_estadual', ''),
        inscricao_municipal=emitente_data.get('inscricao_municipal', ''),
        cnae_fiscal=emitente_data.get('cnae_fiscal', ''),
        endereco_logradouro=emitente_data.get('endereco_logradouro', ''),
        endereco_numero=emitente_data.get('endereco_numero', ''),
        endereco_bairro=emitente_data.get('endereco_bairro', ''),
        endereco_municipio=emitente_data.get('endereco_municipio', ''),
        endereco_uf=emitente_data.get('endereco_uf', ''),
        endereco_cep=emitente_data.get('endereco_cep', ''),
        endereco_pais=CODIGO_BRASIL,
        endereco_telefone=emitente_data.get('endereco_telefone', '')
    )
    
    if homologacao:
        cliente_razao_social = "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
    else:
        cliente_razao_social = cliente_data.get('razao_social', '')
        
    cliente = Cliente(
        razao_social=cliente_razao_social,
        tipo_documento=cliente_data.get('tipo_documento', ''),
        email=cliente_data.get('email', ''),
        numero_documento=cliente_data.get('numero_documento', ''),
        indicador_ie=cliente_data.get('indicador_ie', 1),
        inscricao_estadual=cliente_data.get('inscricao_estadual', ''),
        isento_icms=cliente_data.get('isento_icms', False),
        endereco_logradouro=cliente_data.get('endereco_logradouro', ''),
        endereco_numero=cliente_data.get('endereco_numero', ''),
        endereco_complemento=cliente_data.get('endereco_complemento', ''),
        endereco_bairro=cliente_data.get('endereco_bairro', ''),
        endereco_cep=cliente_data.get('endereco_cep', ''),
        endereco_pais=CODIGO_BRASIL,
        endereco_uf=cliente_data.get('endereco_uf', ''),
        endereco_municipio=cliente_data.get('endereco_municipio', ''),
        endereco_cod_municipio=cliente_data.get('endereco_cod_municipio', ''),
        endereco_telefone=cliente_data.get('endereco_telefone', '')
    )
    transportadora_data = data.get('transportadora', {})
    transportadora = None
    if transportadora_data:
        transportadora = Transportadora(
            razao_social=transportadora_data.get('razao_social', ''),
            tipo_documento=transportadora_data.get('tipo_documento', 'CNPJ'),
            numero_documento=transportadora_data.get('numero_documento', 0),
            endereco_logradouro=transportadora_data.get('endereco_logradouro', ''),
            endereco_uf=transportadora_data.get('endereco_uf', ''),
            endereco_municipio=transportadora_data.get('endereco_municipio', '')
        )       


    # Criar instância de NotaFiscal com base no JSON
    nota_fiscal = NotaFiscal(
        emitente=emitente,
        cliente=cliente,
        transporte_transportadora=transportadora,
        uf=uf_emitente.upper(),
        natureza_operacao=data.get('natureza_operacao', 'VENDA'),
        forma_pagamento=data.get('forma_pagamento', 0),
        tipo_pagamento=data.get('tipo_pagamento', 1),
        modelo=data.get('modelo', 55),
        serie=data.get('serie', '1'),
        numero_nf=data.get('numero_nf', ''),
        data_emissao=datetime.fromisoformat(data.get('data_emissao', datetime.now().isoformat())),
        data_saida_entrada=datetime.fromisoformat(data.get('data_saida_entrada', datetime.now().isoformat())),
        tipo_documento=data.get('tipo_documento', 1),
        municipio=data.get('municipio', ''),
        tipo_impressao_danfe=data.get('tipo_impressao_danfe', 1),
        forma_emissao=data.get('forma_emissao', '1'),
        cliente_final=data.get('cliente_final', 1),
        indicador_destino=data.get('indicador_destino', 1),
        indicador_presencial=data.get('indicador_presencial', 1),
        finalidade_emissao=data.get('finalidade_emissao', '1'),
        processo_emissao=data.get('processo_emissao', '0'),
        transporte_modalidade_frete=data.get('transporte_modalidade_frete', '9.00'),
        informacoes_adicionais_interesse_fisco=data.get('informacoes_adicionais_interesse_fisco', ''),
        informacoes_complementares_interesse_contribuinte=data.get('informacoes_complementares_interesse_contribuinte', ''),
        totais_tributos_aproximado=Decimal(data.get('totais_tributos_aproximado', '0.00')),
        valor_total_nota=Decimal(data.get('valor_total_nota_fiscal', '0.00')),
    )
    
    produtos = data.get('produtos', [])  
    
    for produto_data in produtos:
        nota_fiscal.adicionar_produto_servico(
            codigo=produto_data.get('codigo', ''),
            descricao=produto_data.get('descricao', ''),
            ncm=produto_data.get('ncm', ''),
            cfop=produto_data.get('cfop', ''),
            unidade_comercial=produto_data.get('unidade_comercial', ''),
            ean=produto_data.get('ean', 'SEM GTIN'),
            ean_tributavel=produto_data.get('ean_tributavel', 'SEM GTIN'),
            quantidade_comercial=Decimal(produto_data.get('quantidade_comercial', '0')),
            valor_unitario_comercial=Decimal(produto_data.get('valor_unitario_comercial', '0.00')),
            valor_total_bruto=Decimal(produto_data.get('valor_total_bruto', '0.00')),
            total_frete=Decimal(produto_data.get('total_frete', '0.00')),
            unidade_tributavel=produto_data.get('unidade_tributavel', ''),
            quantidade_tributavel=Decimal(produto_data.get('quantidade_tributavel', '0')),
            valor_unitario_tributavel=Decimal(produto_data.get('valor_unitario_tributavel', '0.00')),
            ind_total=produto_data.get('ind_total', 1),
            icms_modalidade=produto_data.get('icms_modalidade', ''),
            icms_origem=produto_data.get('icms_origem', 0),
            icms_csosn=produto_data.get('icms_csosn', ''),
            pis_modalidade=produto_data.get('pis_modalidade', ''),
            cofins_modalidade=produto_data.get('cofins_modalidade', ''),
            valor_tributos_aprox=Decimal(produto_data.get('valor_tributos_aprox', '0.00'))
        )                             
    
    # responsável técnico
    responsavel_tecnico = data.get('responsavel_tecnico', {})
    nota_fiscal.adicionar_responsavel_tecnico(
        cnpj=responsavel_tecnico.get('cnpj', ''),
        contato=responsavel_tecnico.get('contato', ''),
        email=responsavel_tecnico.get('email', ''),
        fone=responsavel_tecnico.get('fone', '')
    )   

    # exemplo de nota fiscal referenciada (devolução/garantia)
    # nfRef = NotaFiscalReferenciada(
    #     chave_acesso='99999999999999999999999999999999999999999999')
    # nota_fiscal.notas_fiscais_referenciadas.append(nfRef)

    # serialização
    serializador = SerializacaoXML(_fonte_dados, homologacao=homologacao)
    nfe = serializador.exportar()   
    
    return nfe, cliente_razao_social

def validar_nota_fiscal(xml_doc): 
    # Instanciar a classe de validação
    validacao = Validacao()    
    xsd_path = os.path.join(settings.BASE_DIR, 'nota_fiscal', 'XSDs', 'NF-e', 'nfe_v4.00.xsd')
    
    # Validar o XML
    try:
        resultado_validacao = validacao.validar_etree(xml_doc, xsd_path, use_assert=True)
        
        if resultado_validacao:
            return {"status": "sucesso", "mensagem": "XML válido."}
        else:
            erros = []
            for error in validacao.error_log:
                erros.append({
                    "linha": error.line,
                    "coluna": error.column,
                    "mensagem": error.message,
                    "tipo_erro": error.type_name
                })
            
            return {
                "status": "falha",
                "erros": erros
            }
    
    except Exception as e:
        return {
            "status": "erro",
            "mensagem": f"Erro na validação do XML: {str(e)}"
        }
    
def get_info_protocolo(xml_content):
    # Converter o XML da NF-e para um dicionário
    nfe_dict = xmltodict.parse(xml_content)

    # Extrair a chave de acesso cst e xMotivo
    try:
        info_protocolo = nfe_dict['nfeProc']['protNFe']['infProt']
    except KeyError as e:
        print(f"Erro: O info_protocolo {e} não foi encontrada no dicionário.")
        info_protocolo = None  # Defina um valor padrão ou execute outras ações necessárias
    except Exception as e:
        print(f"Um erro inesperado ocorreu: {e}")
        info_protocolo = None 
        
    return info_protocolo         