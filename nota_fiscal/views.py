import json
import datetime
import xmltodict
import xmlschema
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import datetime
from nota_fiscal.models import NotaFiscal as NotaFiscalModel, HistoricoNotaFiscal
from certificados.models import Certificado
from pynfe.processamento.comunicacao import ComunicacaoSefaz
from pynfe.utils.flags import NAMESPACE_NFE
from pynfe.processamento.assinatura import AssinaturaA1
from pynfe.processamento.serializacao import SerializacaoXML
from pynfe.entidades.evento import EventoCancelarNota, EventoCartaCorrecao
from pynfe.entidades.fonte_dados import _fonte_dados
from brazilfiscalreport.danfe import Danfe
from brazilfiscalreport.dacce import DaCCe
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from lxml import etree
from nota_fiscal.utils import (
    consulta_cadastro, 
    extrair_cstat_xmotivo, 
    salvar_nota_fiscal, 
    salvar_historico_nota_fiscal, 
    montar_nota_fiscal,
    validar_nota_fiscal,
    extrair_conteudo_nfe_result,
    extrair_cce_cancelar_cstat_xmotivo,
    salvar_carta_correcao,
    salvar_cancelamento,
    get_info_protocolo
)
from nota_fiscal.email_sender import EmailSender


def consulta_recibo_nota_fiscal(cnpj, numero_recibo, homologacao = True):
    certificado = Certificado.objects.get(cnpj=cnpj)
    certificado_path = Path(settings.MEDIA_ROOT) / certificado.file.name

    senha = certificado.password
    uf = certificado.uf

    con = ComunicacaoSefaz(uf, certificado_path, senha, homologacao)
    envio = con.consulta_recibo(modelo='nfe', numero=numero_recibo) # nfe ou nfce
    return envio.text

def consulta_nota_fiscal(cnpj, chave_acesso, homologacao = True):
    certificado = Certificado.objects.get(cnpj=cnpj)
    certificado_path = Path(settings.MEDIA_ROOT) / certificado.file.name

    senha = certificado.password
    uf = certificado.uf

    con = ComunicacaoSefaz(uf, certificado_path, senha, homologacao)
    envio = con.consulta_nota('nfe', chave_acesso)  # nfe ou nfce
    xml_string = envio.text
    # print(xml_string)

    root = ET.fromstring(xml_string)
    xml_pretty_str = ET.tostring(root, encoding='unicode', method='xml')

    # Busca os elementos cStat e xMotivo usando o ET
    cstat = root.find('.//{http://www.portalfiscal.inf.br/nfe}cStat').text
    xmotivo = root.find('.//{http://www.portalfiscal.inf.br/nfe}xMotivo').text
    xml = None

    # Configurando o namespace correto
    ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}

    # Parse usando lxml
    prot = etree.fromstring(envio.text.encode('utf-8'))

    # Tentando encontrar o status da nota fiscal
    try:
        status = prot.xpath('//ns:retConsSitNFe/ns:cStat', namespaces=ns)[0].text
    except IndexError:
        # Caso não encontre, retorne uma mensagem de erro ou faça um tratamento adequado
        status = None

    if status == '100':
        try:
            prot_nfe = prot.xpath('//ns:retConsSitNFe/ns:protNFe', namespaces=ns)[0]
            xml = etree.tostring(prot_nfe, encoding='unicode')
            print(xml)
        except IndexError:
            xml = None

    return cstat, xmotivo, xml

def verificar_status_servico(uf, certificado_path, senha, homologacao):
    con = ComunicacaoSefaz(uf, certificado_path, senha, homologacao)
    xml = con.status_servico('nfe')     # nfe ou nfce
    print(xml.text)
    # print(xml.content)
    
    cstat, xMotivo = extrair_cstat_xmotivo(xml.text)

    if cstat is not None and xMotivo is not None:
        print(f"cStat: {cstat}, xMotivo: {xMotivo}")
    else:
        print("Não foi possível encontrar cStat e xMotivo.")    

    # # exemplo de leitura da resposta
    # ns = {'ns': NAMESPACE_NFE }
    # # algumas uf podem ser xml.text ou xml.content
    # resposta = etree.fromstring(xml.content)[0][0]
    # print(resposta)

    # status = resposta.xpath('ns:retConsStatServ/ns:cStat',namespaces=ns)[0].text
    # motivo = resposta.xpath('ns:retConsStatServ/ns:xMotivo',namespaces=ns)[0].text

    # print(f'Status:{status}')
    # print(f'Motivo:{motivo}')

@method_decorator(csrf_exempt, name='dispatch')
class NotaFiscalView(View):
    def get(self, request, *args, **kwargs):
        notas = NotaFiscalModel.objects.all().values()
        return JsonResponse(list(notas), safe=False)

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Erro ao decodificar JSON: {str(e)}'}, status=400)
        
        # extraindo o tipo de ambiente
        tipo_ambiente = data.get('tipo_ambiente', True) 
        
        if tipo_ambiente == 1:
            homologacao = False
        else:
            homologacao = True    
                       
        # Extrair o CNPJ do emitente
        cnpj_emitente = data.get('emitente', {}).get('cnpj', '')
        uf_emitente = data.get('emitente', {}).get('endereco_uf', '')
        
        if not cnpj_emitente:
            return JsonResponse({'error': 'CNPJ do emitente não fornecido'}, status=400)
        
        # Buscar o Certificado pelo CNPJ do emitente
        try:
            certificado = Certificado.objects.get(cnpj=cnpj_emitente)
        except Certificado.DoesNotExist:
            return JsonResponse({'error': 'Certificado não encontrado'}, status=404)

        validade_certificado, message_validade = consulta_cadastro(certificado.file.name, cnpj_emitente, certificado.password, uf_emitente, homologacao)
        
        if not validade_certificado:
            return JsonResponse({'error': message_validade}, status=404)

        certificado_path = Path(settings.MEDIA_ROOT) / certificado.file.name
        senha = certificado.password
        
        # Dados da  nota fiscal
        numero_nota_fiscal = data.get('numero_nf', '')
        valor_total_nota_fiscal = data.get('valor_total_nota_fiscal', 0)
        emitente_razao_social = data.get('emitente', {}).get('razao_social', '')

        # montar nota fiscal
        nfe, cliente_razao_social = montar_nota_fiscal(data, uf_emitente, homologacao)
        
        # assinatura
        a1 = AssinaturaA1(certificado_path, senha)
        xml = a1.assinar(nfe)
        xml_string = a1.assinar(nfe, retorna_string=True)
        xml_doc = etree.fromstring(xml_string)        
        
        resultado_validar_nota_fiscal = validar_nota_fiscal(xml_doc)
        
        if resultado_validar_nota_fiscal["status"] == "falha":
            historico = salvar_historico_nota_fiscal(
                cnpj_emitente, 
                numero_nota_fiscal, 
                1, 
                resultado_validar_nota_fiscal["status"], 
                xml_string, 
                resultado_validar_nota_fiscal['erros'])            
            return JsonResponse({
                'erro': 1,
                'mensagem': 'Validação falhou',
                'detalhes': resultado_validar_nota_fiscal['erros']
            }, status=400)  # Mudando para 400, pois 404 é mais usado para "não encontrado"
        elif resultado_validar_nota_fiscal["status"] == "erro":
            historico = salvar_historico_nota_fiscal(
                cnpj_emitente, 
                numero_nota_fiscal, 
                1, 
                resultado_validar_nota_fiscal["status"], 
                xml_string, 
                resultado_validar_nota_fiscal['mensagem'])              
            return JsonResponse({
                'erro': 1,
                'mensagem': resultado_validar_nota_fiscal['mensagem']
            }, status=500)  # Status 500 para erros no servidor      
        
        
        # quando for apenas validar o XML sem enviar
        # nfe_xml = etree.tostring(xml, encoding="unicode").replace('\n','').replace('ns0:','').replace(':ns0', '')
        # print(nfe_xml)
        # return 1        

        # envio
        con = ComunicacaoSefaz(uf_emitente, certificado_path, senha, homologacao)
        envio = con.autorizacao(modelo='nfe', nota_fiscal=xml)

        # em caso de sucesso o retorno será o xml autorizado
        # Ps: no modo sincrono, o retorno será o xml completo (<nfeProc> = <NFe> + <protNFe>)
        # no modo async é preciso montar o nfeProc, juntando o retorno com a NFe  
        
        if envio[0] == 0:
            # print('Sucesso!')
            # print(etree.tostring(envio[1], encoding="unicode").replace('\n','').replace('ns0:','').replace(':ns0', ''))
            xml_content = etree.tostring(envio[1], encoding="unicode").replace('\n','').replace('ns0:','').replace(':ns0', '')

            # Montando o nome dos arquivos
            # Supondo que `emitente` e `nota_fiscal` sejam os objetos que contêm as informações necessárias
            razao_social = emitente_razao_social.split()[0]  # Primeiro nome da razão social
            data_emissao = datetime.strptime(data.get('data_emissao'), "%Y-%m-%dT%H:%M:%S").strftime("%d%m%Y")  # Data de emissão no formato ddmmyyyy
            numero_nf = numero_nota_fiscal  # Número da nota fiscal

            # Montar o nome do arquivo DANFE
            danfe_nome_arquivo = f"{razao_social}_{data_emissao}-{numero_nf}.pdf"
            xml_nome_arquivo = f"{razao_social}_{data_emissao}-{numero_nf}.xml"
            
            # Escrevendo o conteúdo do XML no arquivo
            caminho_arquivo = Path(settings.MEDIA_ROOT) / 'xml' / xml_nome_arquivo
            with open(caminho_arquivo, 'w', encoding='utf-8') as file:
                file.write(xml_content)

            # # Load XML Content
            # with open(caminho_arquivo, "r", encoding="utf8") as file:
            #     xml_content = file.read()          
            
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
            

            # Caminho completo para salvar o PDF
            caminho_arquivo = Path(settings.MEDIA_ROOT) / 'danfe' / danfe_nome_arquivo
            # Construir a URL completa
            full_danfe_url = request.build_absolute_uri(f'/media/danfe/{danfe_nome_arquivo}')
            
            if info_protocolo['cStat'] == 100:
                # Gerar o DANFE e salvar o PDF
                danfe = Danfe(xml=xml_content)
                with open(caminho_arquivo, 'wb') as pdf_file:
                    danfe.output(caminho_arquivo)          
            
            # Salvando em Nota fiscal
            chave_nota_fiscal = info_protocolo['chNFe']
                      
            data_nota_fiscal = {
                'cnpj': cnpj_emitente,
                'numero_nfe': numero_nota_fiscal,
                'destinatario': cliente_razao_social,
                'valor_total': valor_total_nota_fiscal,
                'chave_nota_fiscal': chave_nota_fiscal,
                'numero_protocolo': info_protocolo['nProt'],
                'status_nfe': info_protocolo['cStat'],
                'xml_content': xml_content,
                'xml_file': xml_nome_arquivo,
                'pdf_file': danfe_nome_arquivo
            }

            gravar_nf = salvar_nota_fiscal(data_nota_fiscal)            

            historico = salvar_historico_nota_fiscal(
                cnpj_emitente, 
                numero_nota_fiscal, 
                info_protocolo['cStat'], 
                info_protocolo['xMotivo'], 
                xml_content
            )
            
            # Processo de enviar a nota por e-mail
            email_sender = EmailSender(cnpj_emitente, info_protocolo['chNFe'])
            resultado = email_sender.send_nota_fiscal_email()            
            
            return JsonResponse({
                'xMotivo': info_protocolo['xMotivo'],
                'cStat': info_protocolo['cStat'],
                'chNFe': info_protocolo['chNFe'],
                'nProt': info_protocolo['nProt'],
                'danfe': full_danfe_url
                }, 
            status=200)
        # em caso de erro o retorno será o xml de resposta da SEFAZ + NF-e enviada
        else:
            # print('Erro:')
            # print(envio[1].text) # resposta
            details = f"""
            Inteiro: {envio[0]}
            Status HTTP: {envio[1].status_code}
            Resposta HTTP: {envio[1].text}
            Conteúdo XML:
            """
            resposta_string = envio[1].text
            # print(details)
            # print(resposta_string)
            cstat_ret_envi, xmotivo_ret_envi, cstat_inf_prot, xmotivo_inf_prot, num_recibo, numero_protocolo = extrair_conteudo_nfe_result(envio[1].text)

            buscar_retorno = False
            if cstat_ret_envi == '103' and cstat_inf_prot is None:
                # Aguardando retorno
                cStat = cstat_ret_envi
                xMotivo = xmotivo_ret_envi
                buscar_retorno = True
            elif cstat_inf_prot is not None:
                cStat = cstat_inf_prot
                xMotivo = xmotivo_inf_prot
                buscar_retorno = False
            elif cstat_ret_envi is not None and cstat_ret_envi != '103' and cstat_inf_prot is None:
                cStat = cstat_inf_prot
                xMotivo = xmotivo_inf_prot
                buscar_retorno = True
            else:
                cStat = 0
                xMotivo = 'Motivo desconhecido'
                
            if num_recibo is None:
                num_recibo = 0                
            
            # Convertendo o XML em string
            xml_str = etree.tostring(envio[2], pretty_print=True, encoding='unicode')

            # Analisando o XML
            root = etree.fromstring(xml_str)

            # Extraindo o valor do atributo 'Id' dentro de 'infNFe'
            inf_nfe = root.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
            id_value = inf_nfe.get('Id')

            # Extraindo apenas os números
            chave_nota_fiscal = re.sub(r'\D', '', id_value)
            # consulta_nota_fiscal(cnpj_emitente, chave_nota_fiscal, homologacao)

            # Salvando em Nota fiscal
            data_nota_fiscal = {
                'cnpj': cnpj_emitente,
                'numero_nfe': numero_nota_fiscal,
                'destinatario': cliente_razao_social,
                'valor_total': valor_total_nota_fiscal,
                'chave_nota_fiscal': chave_nota_fiscal,
                'numero_protocolo': numero_protocolo,
                'status_nfe': cStat,
                'xml_content': xml_str,
                'xml_file': '',
                'pdf_file': ''
            }

            gravar_nf = salvar_nota_fiscal(data_nota_fiscal)  

            historico = salvar_historico_nota_fiscal(cnpj_emitente, numero_nota_fiscal, cStat, xMotivo, xml_str, resposta_string)
            # Exibindo os valores
            return JsonResponse({
                'buscar_retorno': buscar_retorno,
                'cStat': cStat, 
                'xMotivo': xMotivo,
                'chNFe': chave_nota_fiscal,
                'nProt': numero_protocolo
                }, 
            status=404)
    
@method_decorator(csrf_exempt, name='dispatch')
class NotaFiscalDetailView(View):
    '''
    Classe para retornar informações sobre o recibo do envio
    '''
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Erro ao decodificar JSON: {str(e)}'}, status=400)
        
        # extraindo o tipo de ambiente
        tipo_ambiente = data.get('tipo_ambiente', True) 
        cnpj_emitente = data.get('cnpj', '')
        # chave_acesso = data.get('chave_acesso', '')
        numero_recibo = data.get('numero_recibo', '')
        
        if tipo_ambiente == 1:
            homologacao = False
        else:
            homologacao = True          
        
        # consulta_nota_fiscal(cnpj_emitente, chave_acesso, homologacao)
        resultado_recibo = consulta_recibo_nota_fiscal(cnpj_emitente, numero_recibo, homologacao)
        cstat_ret_envi, xmotivo_ret_envi, cstat_inf_prot, xmotivo_inf_prot, num_recibo = extrair_conteudo_nfe_result(resultado_recibo)
        buscar_retorno = False
        if cstat_ret_envi == '103' and cstat_inf_prot is None:
            # Aguardando retorno
            cStat = cstat_ret_envi
            xMotivo = xmotivo_ret_envi
            buscar_retorno = True
        elif cstat_inf_prot is not None:
            cStat = cstat_inf_prot
            xMotivo = xmotivo_inf_prot
            buscar_retorno = False
        elif cstat_ret_envi is not None and cstat_ret_envi != '103' and cstat_inf_prot is None:
            cStat = cstat_inf_prot
            xMotivo = xmotivo_inf_prot
            buscar_retorno = True
        else:
            cStat = 0
            xMotivo = 'Motivo desconhecido'
            
        if num_recibo is None:
            num_recibo = 0        
        
        # Exibindo os valores
        return JsonResponse({
            'buscar_retorno': buscar_retorno,
            'cStat': cStat, 
            'xMotivo': xMotivo,
            'num_recibo': num_recibo
            }, 
        status=200)
               
@method_decorator(csrf_exempt, name='dispatch')
class NotaFiscalConsultarView(View):
    '''
    Classe para retornar informações sobre a chave da nota fiscal
    '''    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Erro ao decodificar JSON: {str(e)}'}, status=400)
        
        # extraindo o tipo de ambiente
        tipo_ambiente = data.get('tipo_ambiente', True) 
        cnpj_emitente = data.get('cnpj', '')
        chave_acesso = data.get('chave_acesso', '')
        
        if tipo_ambiente == 1:
            homologacao = False
        else:
            homologacao = True          
        
        # consulta_nota_fiscal(cnpj_emitente, chave_acesso, homologacao)
        cStat, xMotivo, xml_prot = consulta_nota_fiscal(cnpj_emitente, chave_acesso, homologacao)
        danfe_url = None
        numero_protocolo = None
        http_status = 404

        if cStat == '100':
            http_status = 200
            try:
                # Busca a NotaFiscal com base na chave de acesso
                nota_fiscal = NotaFiscalModel.objects.get(chave_nota_fiscal=chave_acesso)
                xml_content = nota_fiscal.xml
                
                emitente = Certificado.objects.get(cnpj=cnpj_emitente)
                razao_social = emitente.name.split()[0]  # Primeiro nome da razão social
                data_emissao = nota_fiscal.data_emissao.strftime("%d%m%Y")
                numero_nf = nota_fiscal.numero  # Número da nota fiscal                
                # Verificar se existe o arquivo XML e gerar o PDF
                # Aqui você pode verificar a existência do arquivo XML e gerar o PDF, se necessário
                # Verifica se o xml_content começa com "<NFe"
                if xml_content.strip().startswith("<NFe"):
                    
                    xml_content_modificado = re.sub(r'<NFe\b[^>]*>', '<NFe xmlns="http://www.portalfiscal.inf.br/nfe">', xml_content, count=1)
                    xml_prot_modificado = re.sub(r'<protNFe\b[^>]*>', '<protNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">', xml_prot, count=1)

                    # Monta o XML completo
                    nfe_proc = (
                        '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
                        f"{xml_content_modificado}"
                        f"{xml_prot_modificado}"
                        '</nfeProc>'
                    )
                    xml_nome_arquivo = f"{razao_social}_{data_emissao}-{numero_nf}.xml"
                    
                    info_protocolo = get_info_protocolo(nfe_proc) 
                    
                    if info_protocolo is not None:
                        numero_protocolo = info_protocolo['nProt']
                        nota_fiscal.numero_protocolo = numero_protocolo
                        nota_fiscal.save()

                    # Escrevendo o conteúdo do XML no arquivo
                    caminho_arquivo = Path(settings.MEDIA_ROOT) / 'xml' / xml_nome_arquivo
                    with open(caminho_arquivo, 'w', encoding='utf-8') as file:
                        file.write(nfe_proc) 
                        
                    nota_fiscal.xml = nfe_proc   
                    nota_fiscal.xml_file_name  = xml_nome_arquivo
                    nota_fiscal.status = cStat
                    nota_fiscal.save()  
                    
                    nota_fiscal = NotaFiscalModel.objects.get(chave_nota_fiscal=chave_acesso)
                else:
                    print('O xml nao começa com Nfe')   
                    xml_get_info = """<protNFe xmlns="http://www.portalfiscal.inf.br/nfe" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" versao="4.00"><infProt><tpAmb>1</tpAmb><verAplic>SP_NFE_PL009_V4</verAplic><chNFe>35240821277052000180550010000000461549586434</chNFe><dhRecbto>2024-08-31T08:02:21-03:00</dhRecbto><nProt>135241923712032</nProt><digVal>XrSxG4y1xUsyXsEtGwH6D8VNnGA=</digVal><cStat>100</cStat><xMotivo>Autorizado o uso da NF-e</xMotivo></infProt></protNFe>"""           
                    # Converter o XML para um dicionário
                    data = xmltodict.parse(xml_prot)

                    # Acessar a informação dentro de infProt
                    numero_protocolo = data['protNFe']['infProt']['nProt'] 
                    
                    if nota_fiscal.numero_protocolo is None or nota_fiscal.numero_protocolo == '':
                        nota_fiscal.numero_protocolo = numero_protocolo  
                        nota_fiscal.save()                 

                if nota_fiscal.xml_file_name:
                    xml_file = Path(settings.MEDIA_ROOT) / 'xml' / nota_fiscal.xml_file_name
                    nome_arquivo = nota_fiscal.xml_file_name.rstrip('.xml') + '.pdf'

                    if xml_file.exists():
                        if nota_fiscal.pdf_file_name:
                            pdf_file = Path(settings.MEDIA_ROOT) / 'danfe' / nota_fiscal.pdf_file_name
                        else:
                            pdf_file = None
                            
                        if pdf_file.exists():
                            danfe_url = nota_fiscal.pdf_file_name
                        else:
                            # Gerar o DANFE e salvar o PDF
                            caminho_arquivo = Path(settings.MEDIA_ROOT) / 'danfe' / nome_arquivo
                            danfe = Danfe(xml=xml_content)
                            with open(caminho_arquivo, 'wb') as pdf_file:
                                danfe.output(caminho_arquivo)

                            # Atualizar o campo pdf_file_name na instância de NotaFiscalModel
                            nota_fiscal.pdf_file_name = nome_arquivo
                            nota_fiscal.save()
                            danfe_url = nome_arquivo
                    else:
                        print('Arquivo xml nao existe')

                if not nota_fiscal.xml_file_name or not xml_file.exists():                    
                    # Montar o nome do arquivo DANFE
                    danfe_nome_arquivo = f"{razao_social}_{data_emissao}-{numero_nf}.pdf"
                    xml_nome_arquivo = f"{razao_social}_{data_emissao}-{numero_nf}.xml"
                    
                    # Escrevendo o conteúdo do XML no arquivo
                    caminho_arquivo = Path(settings.MEDIA_ROOT) / 'xml' / xml_nome_arquivo
                    with open(caminho_arquivo, 'w', encoding='utf-8') as file:
                        file.write(xml_content) 
                        
                    info_protocolo = get_info_protocolo(xml_content) 
                    
                    if info_protocolo is not None:
                        numero_protocolo = info_protocolo['nProt']  
                        nota_fiscal.numero_protocolo = numero_protocolo
                        nota_fiscal.save()                                              
                        
                    # Caminho completo para salvar o PDF
                    caminho_arquivo = Path(settings.MEDIA_ROOT) / 'danfe' / danfe_nome_arquivo

                    danfe = Danfe(xml=xml_content)
                    with open(caminho_arquivo, 'wb') as pdf_file:
                        danfe.output(caminho_arquivo)   
                        
                    danfe_url = danfe_nome_arquivo   
                    nota_fiscal.pdf_file_name = danfe_nome_arquivo
                    nota_fiscal.xml_file_name = xml_nome_arquivo
                    nota_fiscal.save()                                                          
                
            except NotaFiscalModel.DoesNotExist:
                print(f"Nota Fiscal com chave {chave_acesso} não encontrada.")
        
        # Exibindo os valores
        # Construir a URL completa
        full_danfe_url = request.build_absolute_uri(f'/media/danfe/{danfe_url}')        
        return JsonResponse({
            'cStat': cStat, 
            'xMotivo': xMotivo,
            'nProt': numero_protocolo,
            'danfe': full_danfe_url
            }, 
        status=http_status)
        
@method_decorator(csrf_exempt, name='dispatch')
class NotaFiscalCCeView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Erro ao decodificar JSON: {str(e)}'}, status=400)
        
        # extraindo os dados
        tipo_ambiente = data.get('tipo_ambiente', True) 
        cnpj_emitente = data.get('cnpj', '')
        chave_acesso = data.get('chave_acesso', '')
        n_seq_evento = data.get('n_seq_evento', 1)
        correcao = data.get('correcao', '')
        
        # dados do emitente
        emitente_data = data.get('emitente', {})
        emitente_nome = emitente_data.get('razao_social', '')
        emitente_logradouro = emitente_data.get('endereco_logradouro', '')
        emitente_numero = emitente_data.get('endereco_numero', '')
        emitente_bairro = emitente_data.get('endereco_bairro', '')
        emitente_municipio = emitente_data.get('endereco_municipio', '')
        emitente_uf = emitente_data.get('endereco_uf', '')
        emitente_cep = emitente_data.get('endereco_cep', '')
        emitente_telefone = emitente_data.get('endereco_telefone', '')
        emitente_endereco = emitente_logradouro + ' ' + emitente_numero
        
        if tipo_ambiente == 1:
            homologacao = False
        else:
            homologacao = True  
            
        # Buscar o Certificado pelo CNPJ do emitente
        try:
            certificado = Certificado.objects.get(cnpj=cnpj_emitente)
        except Certificado.DoesNotExist:
            return JsonResponse({'error': 'Certificado não encontrado'}, status=404)

        uf_emitente = certificado.uf
        validade_certificado, message_validade = consulta_cadastro(certificado.file.name, cnpj_emitente, certificado.password, uf_emitente, homologacao)
        
        if not validade_certificado:
            return JsonResponse({'error': message_validade}, status=404)

        certificado_path = Path(settings.MEDIA_ROOT) / certificado.file.name
        senha = certificado.password                  
        
        data_emissao = datetime.now()

        carta_correcao = EventoCartaCorrecao(
                cnpj=cnpj_emitente, # cnpj do emissor
                chave=chave_acesso, # chave de acesso da nota
                data_emissao=data_emissao,
                uf=uf_emitente,
                n_seq_evento=n_seq_evento,                                       #  
                correcao=correcao
            )

        # serialização
        serializador = SerializacaoXML(_fonte_dados, homologacao=homologacao)
        nfe_cc = serializador.serializar_evento(carta_correcao)

        # assinatura
        a1 = AssinaturaA1(certificado_path, senha)
        xml = a1.assinar(nfe_cc)
        # Converter o XML para string
        xml_content = etree.tostring(xml, pretty_print=True, encoding='unicode')
        
        con = ComunicacaoSefaz(uf_emitente, certificado_path, senha, homologacao)
        envio = con.evento(modelo='nfe', evento=xml) 

        # print(envio.text)
        xml_retorno = envio.text
        # xml_retorno = '<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><soap:Body><nfeResultMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4"><retEnvEvento versao="1.00" xmlns="http://www.portalfiscal.inf.br/nfe"><idLote>1</idLote><tpAmb>2</tpAmb><verAplic>SP_EVENTOS_PL_100</verAplic><cOrgao>35</cOrgao><cStat>128</cStat><xMotivo>Lote de Evento Processado</xMotivo><retEvento versao="1.00"><infEvento><tpAmb>2</tpAmb><verAplic>SP_EVENTOS_PL_100</verAplic><cOrgao>35</cOrgao><cStat>135</cStat><xMotivo>Evento registrado e vinculado a NF-e</xMotivo><chNFe>35240821277052000180550010000000351947416829</chNFe><tpEvento>110110</tpEvento><xEvento>Carta de Correção registrada</xEvento><nSeqEvento>1</nSeqEvento><CPFDest>22213849897</CPFDest><dhRegEvento>2024-08-31T20:28:13-03:00</dhRegEvento><nProt>135240006299780</nProt></infEvento></retEvento></retEnvEvento></nfeResultMsg></soap:Body></soap:Envelope>'
        # xml_retorno = '<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><soap:Body><nfeResultMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4"><retEnvEvento versao="1.00" xmlns="http://www.portalfiscal.inf.br/nfe"><idLote>1</idLote><tpAmb>2</tpAmb><verAplic>SP_EVENTOS_PL_100</verAplic><cOrgao>35</cOrgao><cStat>128</cStat><xMotivo>Lote de Evento Processado</xMotivo><retEvento versao="1.00"><infEvento><tpAmb>2</tpAmb><verAplic>SP_EVENTOS_PL_100</verAplic><cOrgao>35</cOrgao><cStat>494</cStat><xMotivo>Rejeição: Chave de Acesso inexistente para o tpEvento que exige a existência da NF-e</xMotivo><chNFe>35240821277052000180550010000000461549586434</chNFe><tpEvento>110110</tpEvento><nSeqEvento>1</nSeqEvento><dhRegEvento>2024-08-31T19:59:54-03:00</dhRegEvento></infEvento></retEvento></retEnvEvento></nfeResultMsg></soap:Body></soap:Envelope>'
        cStat, xMotivo = extrair_cce_cancelar_cstat_xmotivo(xml_retorno)
        
        pdf_url = None
        xml_nome_arquivo = ''
        pdf_nome_arquivo = ''    
        
        http_status = 404
        if cStat == '135':
            http_status = 200
            # Monta o XML completo    
            root = ET.fromstring(xml_retorno)           

            # Defina o namespace para procurar elementos corretamente
            namespaces = {
                'soap': 'http://www.w3.org/2003/05/soap-envelope',
                'nfe': 'http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4',
                'inf': 'http://www.portalfiscal.inf.br/nfe'  # Para o namespace padrão
            }

            # Encontre o elemento retEvento dentro de retEnvEvento
            ret_evento = root.find('.//inf:retEnvEvento/inf:retEvento', namespaces)

            # Converta o elemento retEvento de volta para uma string, incluindo as tags
            if ret_evento is not None:
                ret_evento_string = ET.tostring(ret_evento, encoding='unicode')
                print(ret_evento_string)
            else:
                print("Elemento retEvento não encontrado.")  
                          
            cce_proc = (
                '<?xml version="1.0" encoding="UTF-8"?><procEventoNFe versao="1.00" xmlns="http://www.portalfiscal.inf.br/nfe">'
                f"{xml_content}"
                f"{ret_evento_string}"
                '</procEventoNFe>'
            )            
            
            # GERAR XML
            razao_social = certificado.name.split()[0]  # Primeiro nome da razão social
            data_emissao = datetime.now().strftime("%Y%m%d%H%M%S")
            xml_nome_arquivo = f"{razao_social}_CCE_{data_emissao}-{chave_acesso}.xml"
            pdf_nome_arquivo = f"{razao_social}_CCE_{data_emissao}-{chave_acesso}.pdf"            
            
            # # Escrevendo o conteúdo do XML no arquivo
            caminho_arquivo = Path(settings.MEDIA_ROOT) / 'xml' / xml_nome_arquivo
            with open(caminho_arquivo, 'w', encoding='utf-8') as file:
                file.write(cce_proc)
                
            # Gerar o DANFE e salvar o PDF
            emitente = {
                "nome": emitente_nome,
                "end": emitente_endereco,
                "bairro": emitente_bairro,
                "cep": emitente_cep,
                "cidade": emitente_municipio,
                "uf": emitente_uf,
                "fone": emitente_telefone,
            }            
            caminho_arquivo = Path(settings.MEDIA_ROOT) / 'danfe' / pdf_nome_arquivo
            cce = DaCCe(xml=cce_proc, emitente=emitente)            
            with open(caminho_arquivo, 'wb') as pdf_file:
                cce.output(caminho_arquivo)  
                
            pdf_url = pdf_nome_arquivo              
                
        # Salvando em Carta de Correção
        data_carta_correcao = {
            'cnpj': cnpj_emitente,
            'chave': chave_acesso,
            'n_seq_evento': n_seq_evento,
            'correcao': correcao,
            'status': cStat,
            'motivo': xMotivo,
            'xml_retorno': xml_retorno,
            'xml_file': xml_nome_arquivo,
            'pdf_file': pdf_nome_arquivo
        }  
        cce = salvar_carta_correcao(data_carta_correcao)  
        
        # Construir a URL completa
        full_danfe_url = request.build_absolute_uri(f'/media/danfe/{pdf_url}')                                            
        
        # Exibindo os valores
        return JsonResponse({
            'cStat': cStat, 
            'xMotivo': xMotivo,
            'pdf': full_danfe_url
            }, 
        status=http_status)

@method_decorator(csrf_exempt, name='dispatch')
class NotaFiscalCancelarView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Erro ao decodificar JSON: {str(e)}'}, status=400)
        
        # extraindo os dados
        tipo_ambiente = data.get('tipo_ambiente', True) 
        cnpj_emitente = data.get('cnpj', '')
        chave_acesso = data.get('chave_acesso', '')
        numero_protocolo = data.get('numero_protocolo', '')
        justificativa = data.get('justificativa', '')
        
        if tipo_ambiente == 1:
            homologacao = False
        else:
            homologacao = True  
            
        # Buscar o Certificado pelo CNPJ do emitente
        try:
            certificado = Certificado.objects.get(cnpj=cnpj_emitente)
        except Certificado.DoesNotExist:
            return JsonResponse({'error': 'Certificado não encontrado'}, status=404)

        uf_emitente = certificado.uf
        validade_certificado, message_validade = consulta_cadastro(certificado.file.name, cnpj_emitente, certificado.password, uf_emitente, homologacao)
        
        if not validade_certificado:
            return JsonResponse({'error': message_validade}, status=404)

        certificado_path = Path(settings.MEDIA_ROOT) / certificado.file.name
        senha = certificado.password                  
        
        data_emissao = datetime.now()   
        
        cancelar = EventoCancelarNota(
                cnpj=cnpj_emitente,                                # cpf ou cnpj do emissor
                chave=chave_acesso, # chave de acesso da nota
                data_emissao=data_emissao,
                uf=uf_emitente,
                protocolo=numero_protocolo,                                      # número do protocolo da nota
                justificativa=justificativa
            )

        # serialização
        serializador = SerializacaoXML(_fonte_dados, homologacao=homologacao)
        nfe_cancel = serializador.serializar_evento(cancelar)

        # assinatura
        a1 = AssinaturaA1(certificado_path, senha)
        xml = a1.assinar(nfe_cancel)

        con = ComunicacaoSefaz(uf_emitente, certificado_path, senha, homologacao)
        envio = con.evento(modelo='nfe', evento=xml) 

        xml_retorno = envio.text
        # xml_retorno = """<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><soap:Body><nfeResultMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4"><retEnvEvento versao="1.00" xmlns="http://www.portalfiscal.inf.br/nfe"><idLote>1</idLote><tpAmb>2</tpAmb><verAplic>SP_EVENTOS_PL_100</verAplic><cOrgao>35</cOrgao><cStat>128</cStat><xMotivo>Lote de Evento Processado</xMotivo><retEvento versao="1.00"><infEvento><tpAmb>2</tpAmb><verAplic>SP_EVENTOS_PL_100</verAplic><cOrgao>35</cOrgao><cStat>135</cStat><xMotivo>Evento registrado e vinculado a NF-e</xMotivo><chNFe>35240821277052000180550010000000461205931807</chNFe><tpEvento>110111</tpEvento><xEvento>Cancelamento registrado</xEvento><nSeqEvento>1</nSeqEvento><CPFDest>05692967812</CPFDest><dhRegEvento>2024-09-02T08:46:05-03:00</dhRegEvento><nProt>135240006304664</nProt></infEvento></retEvento></retEnvEvento></nfeResultMsg></soap:Body></soap:Envelope>"""
        # xml_retorno = """<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><soap:Body><nfeResultMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4"><retEnvEvento versao="1.00" xmlns="http://www.portalfiscal.inf.br/nfe"><idLote>1</idLote><tpAmb>2</tpAmb><verAplic>SP_EVENTOS_PL_100</verAplic><cOrgao>35</cOrgao><cStat>128</cStat><xMotivo>Lote de Evento Processado</xMotivo><retEvento versao="1.00"><infEvento><tpAmb>2</tpAmb><verAplic>SP_EVENTOS_PL_100</verAplic><cOrgao>35</cOrgao><cStat>155</cStat><xMotivo>Cancelamento homologado fora de prazo</xMotivo><chNFe>35240821277052000180550010000000351947416829</chNFe><tpEvento>110111</tpEvento><xEvento>Cancelamento registrado</xEvento><nSeqEvento>1</nSeqEvento><CPFDest>22213849897</CPFDest><dhRegEvento>2024-09-02T08:38:50-03:00</dhRegEvento><nProt>135240006304554</nProt></infEvento></retEvento></retEnvEvento></nfeResultMsg></soap:Body></soap:Envelope>"""
        # xml_retorno = """<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><soap:Body><nfeResultMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4"><retEnvEvento versao="1.00" xmlns="http://www.portalfiscal.inf.br/nfe"><idLote>1</idLote><tpAmb>2</tpAmb><verAplic>SP_EVENTOS_PL_100</verAplic><cOrgao>35</cOrgao><cStat>128</cStat><xMotivo>Lote de Evento Processado</xMotivo><retEvento versao="1.00"><infEvento><tpAmb>2</tpAmb><verAplic>SP_EVENTOS_PL_100</verAplic><cOrgao>35</cOrgao><cStat>222</cStat><xMotivo>Rejeição: Protocolo de Autorização de Uso difere do cadastrado</xMotivo><chNFe>35240821277052000180550010000000461205931807</chNFe><tpEvento>110111</tpEvento><nSeqEvento>1</nSeqEvento><dhRegEvento>2024-09-02T08:44:33-03:00</dhRegEvento></infEvento></retEvento></retEnvEvento></nfeResultMsg></soap:Body></soap:Envelope>"""
        cStat, xMotivo = extrair_cce_cancelar_cstat_xmotivo(xml_retorno)
        
        # Salvando em Carta de Correção
        data_cancelamento = {
            'cnpj': cnpj_emitente,
            'chave': chave_acesso,
            'numero_protocolo': numero_protocolo,
            'justificativa': justificativa,
            'status': cStat,
            'motivo': xMotivo,
            'xml_retorno': xml_retorno
        }  
        cancelamento = salvar_cancelamento(data_cancelamento)        
        
        http_status = 404
        if cStat == '135': 
            http_status = 200      
        
        # Exibindo os valores
        return JsonResponse({
            'cStat': cStat,
            'xMotivo': xMotivo
            }, 
        status=http_status)                    

@method_decorator(csrf_exempt, name='dispatch')
class NotaFiscalSendEmailView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Erro ao decodificar JSON: {str(e)}'}, status=400)
        
        # extraindo os dados
        cnpj = data.get('cnpj', '')
        chave = data.get('chave_acesso', '')
        
        email_sender = EmailSender(cnpj, chave)
        resultado = email_sender.send_nota_fiscal_email()
        return resultado                

