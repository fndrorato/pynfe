# Criação de uma imagem Docker para o projeto SGE
FROM python:3.11-slim

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Pode ser alterado para o nome que desejar
# mas também pode ser /app OU /sge
WORKDIR /sge

# copiou todos os arquivos do diretório atual para o diretório /sge
COPY . .

# Instalando as dependências do projeto
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Sempre executar o migrate antes de iniciar o servidor
# RUN python manage.py migrate

# Comando para expor a porta para acessar o projeto
EXPOSE 8000

# Comando para iniciar o servidor
CMD python manage.py migrate && python manage.py runserver 0.0.0.0:8000
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
