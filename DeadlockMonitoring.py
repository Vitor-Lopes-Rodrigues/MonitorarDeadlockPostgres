#Imports
import paramiko
import time
from datetime import datetime
import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import re

#Desenvolvido por: Vitor Lopes Rodrigues.
#Objetivo: Este código tem como objetivo monitorar a cada 10 Minutos arquivos de Logs Postgres gerados por ele mesmo.
#Também gera um log destes arquivos dentro de um volume para facilitar na busca futuramente.
# Claro que não podemos esquecer que ao achar algum problema de (DEADLOCK) encaminha para os destinatários via EMAIL. (Arquivo em formato de TXT)
#Last Updated: 03/11/2023
#Versão: 1.0
#Todo este código esta destinado a ajudar desenvolvedores que queiram monitorar bases de dados postgres via Python. Por favor seguir os comentários e escritas substituidas
# E se possivel, incrementar novas ideías e encaminhar.
# Um ótimo estudo!!😁



# Configuração do logger
def get_logger():
    id_log = datetime.now().strftime('%d-%m-%Y')
    log_path = os.getenv('LOGS_PATH')
    log_file = f'{log_path}/PythonAtualizador-{id_log}.log'

    logging.basicConfig(
        format='%(asctime)s %(name)s %(levelname)s: %(message)s',
        datefmt='%d/%m/%Y %I:%M:%S %p',
        level=logging.INFO,
        filename=log_file
    )

    return logging.getLogger(__name__)

log = get_logger()

def enviar_email(deadlock_messages, assunto):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 123  # Se quiser, usa a porta 465
    smtp_username = 'SEU_EMAIL'
    smtp_password = 'SENHA_EMAIL'

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(smtp_username, smtp_password)

    sender_email = 'SEU_EMAIL'  # Remetente
    receiver_emails = ['EMAIL_RECEBEDOR', 'EMAIL_RECEBEDOR']

    # Cria o objeto MIMEMultipart antes de atribuir destinatários
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = ', '.join(receiver_emails)  # Destinatários
    message['Subject'] = assunto

    # Se algum deadlock for encontrado, anexa o arquivo de texto ao e-mail
    if deadlock_messages:
        txt_filename = f'deadlocks_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        with open(txt_filename, 'w') as txt_file:
            txt_file.write('\n'.join(deadlock_messages))

        attachment = open(txt_filename, 'rb')
        part = MIMEBase('application', 'octet-stream')
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename= %s" % txt_filename)
        message.attach(part)

        print(f'Deadlocks detectados. Arquivo TXT anexado ao e-mail.')
        log.info(f'Deadlocks detectados. Arquivo TXT anexado ao e-mail.')

    # Enviar o e-mail
    server.sendmail(sender_email, receiver_emails, message.as_string())

    # Fechar a conexão SMTP
    server.quit()

def extract_deadlock_info(line, log_lines):
    deadlock_info = []

    # Padrão para extrair informações específicas da mensagem de deadlock
    pattern = r'process (\d+) detected deadlock while waiting for ShareLock on transaction (\d+) after (\d+\.\d+) ms'

    match = re.search(pattern, line)
    if match:
        process_id = match.group(1)
        transaction_id = match.group(2)
        wait_time = match.group(3)

        deadlock_info.append(f"Processo {process_id} detectou deadlock na transação {transaction_id} após {wait_time} ms")

        # Adicione informações adicionais ao deadlock_info
        for i, next_line in enumerate(log_lines):
            if f'Process {process_id} waits for ShareLock on transaction {transaction_id}' in next_line:
                deadlock_info.append(next_line.strip())
                # Adicione mais linhas se necessário
                for j in range(i+1, i+5):  # Adicione até 5 linhas adicionais, ajuste conforme necessário
                    deadlock_info.append(log_lines[j].strip())

    return deadlock_info


def read_postgres_log(host, username, password, log_path):
    # Conectar ao servidor remoto
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=username, password=password)

    # Comando para ler todo o conteúdo do arquivo de log
    command = f'sudo cat {log_path}'

    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Executar o comando remotamente
        stdin, stdout, stderr = ssh.exec_command(command)

        # Ler as linhas do resultado
        log_lines = stdout.readlines()

        # Verificar se há deadlock em qualquer linha do arquivo
        deadlock_found = False
        deadlock_messages = []  # Armazenar as mensagens de deadlock

        for line in log_lines:
            if 'deadlock' in line.lower():
                print(f'Deadlock detectado: {line}')
                log.info(f'Deadlock detectado: {line}')

                # Extrair informações específicas da mensagem de deadlock
                deadlock_info = extract_deadlock_info(line, log_lines)
                if deadlock_info:
                    mensagem = f" \n \n Deadlock detectado:\n{''.join(deadlock_info)}"
                    deadlock_messages.append(mensagem)
                    deadlock_found = True

        # Se algum deadlock for encontrado
        if deadlock_found:
            # Enviar um único e-mail com todas as mensagens de deadlock
            assunto = "Deadlocks Detectados no Banco de dados Cartões-Production"
            mensagem = '\n'.join(deadlock_messages)
            enviar_email(deadlock_messages, assunto)

        # Se nenhum deadlock for encontrado
        else:
            print('Nenhum deadlock encontrado.')
            log.info('Nenhum deadlock encontrado.')

        # Aguardar 10 minutos antes de verificar novamente
        time.sleep(600)

    # Fechar a conexão SSH
    ssh.close()

# Substitua as informações abaixo com os detalhes do seu servidor
host = 'IP/MAQUINA'
username = 'USUARIO'
password = 'SENHA'
log_path = 'CAMINHO DO ARQUIVO DE LOG POSTGRES BY "/" '


read_postgres_log(host, username, password, log_path)