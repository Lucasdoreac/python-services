import os
from datetime import datetime
from typing import Dict, Any
import typst
from minio import Minio, S3Error
from BLL import FlowController
from DAL import ReservationManager


def get_name_by_idODS(data: dict, filter_id: str) -> str:
    """
    Retorna o 'name' do objeto na lista 'types' cujo 'id' seja igual a filter_id.
    :param data: Dicionário com a chave 'types' contendo uma lista de objetos.
    :param filter_id: Identificador para filtrar.
    :return: O valor do 'name' se encontrado, ou None caso contrário.
    """

    # Se filter_id começa com "ODS ", remove esse prefixo para ficar apenas o número.
    if filter_id.startswith("ODS "):
        filter_id = filter_id.replace("ODS ", "")

    for item in data.get("types", []):
        if str(item.get("id")) == filter_id:
            return item.get("name")

    return None


def generate_event_pdf(event_id,data: Dict[str, Any] = None):
    """
    Gera um PDF a partir dos dados do evento utilizando a linguagem Typst.

    Parâmetros:
        event_data (dict): Dicionário contendo os dados do evento. Deve possuir as seguintes chaves:
            - name: Título do evento.
            - organizer: Dicionário com 'name', 'email' e 'phone'.
            - eventTypeId: Tipo de evento.
            - odsId: Identificação do ODS.
            - subscriptionLink: Link de inscrição (pode estar vazio).
            - description: Descrição do evento.
            - graduationId: Identificação do curso.
            - targetPublic: Público alvo.
            - resources: Recursos necessários.
            - expectedSubscribers: Número esperado de participantes.
            - roomType: Tipo de sala.
            - entrepreneuralPath: Trilha empreendedora.
            - extensionProject: Projeto de extensão.
            - studentsMonitors: Alunos monitores.
            - eventLogo: Logo do evento (pode estar vazio).
            - status: Status do evento.
    """

    ods = FlowController.find_types_by_collection("ODS")

    # Extrai JSON de ods se for uma tupla ou tiver get_json(), senão usa ods diretamente.
    if isinstance(ods, tuple):
        ods_data = ods[0].get_json()
    elif hasattr(ods, "get_json"):
        ods_data = ods.get_json()
    else:
        ods_data = ods

    if data:
        event_data = FlowController.event_data_build(data)
    else:
        event_data = FlowController.find_event_by_event_id(event_id)


    name_ods = get_name_by_idODS(ods_data, event_data['odsId'])
    reserva_date = FlowController.find_reservation_by_event_id(event_id)




    # Inicializa variáveis padrão
    data_evento = "Sem data informada ainda"
    hora_inicio = "Sem horário de início informado ainda"
    hora_final = "Sem horário final informado ainda"

    if isinstance(reserva_date, list) and len(reserva_date) > 0:
        reserva_date = reserva_date[0]
    elif isinstance(reserva_date, list):
        reserva_date = {}



    # Tenta extrair data e hora apenas se as chaves existirem
    start_at = reserva_date.get("startAt")
    end_at = reserva_date.get("endAt")

    try:
        if isinstance(start_at, datetime):
            data_evento = start_at.strftime("%d/%m/%Y")
            hora_inicio = start_at.strftime("%H:%M")
        if isinstance(end_at, datetime):
            hora_final = end_at.strftime("%H:%M")
    except Exception as e:
        print(f"Erro ao processar data/hora da reserva: {e}")

    # Define valores padrão para campos que podem não ter sido informados
    entrepreneurial_path = event_data['entrepreneuralPath'] or "Não associado a trilha empreendedora"
    extension_project = event_data['extensionProject'] or "Não associado a projeto de extensão"
    students_monitors = event_data['studentsMonitors'] or "Sem alunos monitores"
    date = data_evento
    hours_start = hora_inicio
    hours_end = hora_final


    typst_text = f"""
// Título do Evento
#set text(
  font: "New Computer Modern",
  size: 14pt
)
#align(center)[
  = "{event_data['name']}"
]

#align(center)[
  #set text(
    font: "New Computer Modern",
    size: 15pt
  )
]

// Organizador

*Informações do Organizador:*

#set text(
  font: "New Computer Modern",
  size: 11pt
)
#set table(
  stroke: luma(v),
  gutter: 0.2em,
  fill: (x, y) =>
    if x == 0 or y == 0 {{ gray }},
  inset: (right: 1.5em),
)
#set table(
  stroke: luma(v),
  gutter: 0.2em,
  fill: (x, y) =>
    if x != 0 or x == 0 {{ gray.lighten(30%) }},
  inset: (right: 1.5em),
)

#show table.cell: it => {{
  if it.x == 0 {{
    set text(black.lighten(5%))
    strong(it)
  }} else if it.body == [] {{
    // Substitui células vazias por "N/A"
    pad(..it.inset)[_N/A_]
  }} else {{
    it
  }}
}}

#table(
  columns: 2,
  [Responsável:], [`{event_data['organizer']['email'].split('@')[0]}`],
  [E-mail do Responsável:], [`{event_data['organizer']['email']}`],
  [Telefone:], [`{event_data['organizer']['phone']}`],
)

#set table(
  stroke: luma(v),
  gutter: 0.2em,
  fill: (x, y) =>
    if x == 0 or y == 0 {{ blue }},
  inset: (right: 1.5em),
)
#set table(
  stroke: luma(v),
  gutter: 0.2em,
  fill: (x, y) =>
    if x != 0 or x == 0 {{ blue.lighten(50%) }},
  inset: (right: 1.5em),
)

#show table.cell: it => {{
  if it.x == 0 {{
    set text(black.lighten(5%))
    strong(it)
  }} else if it.body == [] {{
    pad(..it.inset)[_N/A_]
  }} else {{
    it
  }}
}}

#set text(
  font: "New Computer Modern",
  size: 14pt
)

// Evento

*Informações do Evento:*

#set text(
  font: "New Computer Modern",
  size: 11pt
)

#table(
  columns: 2,
  [Tipo de Evento:], [`{event_data['eventTypeId']}`],
  [ODS:], [`{name_ods}`],
  [Descrição:], [`{event_data['description']}`],
  [Curso:], [`{event_data['graduationId']}`],
  [Público Alvo:], [`{event_data['targetPublic']}`],
  [Recursos Necessários:], [`{event_data['resources']}`],
  [Número de Participantes Esperados:], [`{event_data['expectedSubscribers']}`],
  [Sala:], [`{event_data['roomType']}`],
  [Trilha Empreendedora:], [`{entrepreneurial_path}`],
  [Projeto de Extensão:], [`{extension_project}`],
  [Alunos Monitores:], [`{students_monitors}`],
  [Data:],[`{date}`],
  [Horário de inicio:],[`{hours_start}`],
  [Horário final:],[`{hours_end}`],   
)
    """

    pdf_dir = os.path.join("PDFs")
    os.makedirs(pdf_dir, exist_ok=True)

    typst_file_path = os.path.join(pdf_dir, "evento.typ")
    with open(typst_file_path, "w", encoding="utf-8") as typ_file:
        typ_file.write(typst_text)
    print(f"Arquivo Typst criado em: {typst_file_path}")

    pdf_bytes = typst.compile(typst_file_path)

    pdf_path = os.path.join(pdf_dir, "evento.pdf")
    with open(pdf_path, "wb") as pdf_file:
        pdf_file.write(pdf_bytes)

    print(f"PDF gerado e salvo com sucesso em: {pdf_path}")

    save_pdf(event_id)


def save_pdf(event_id):
    MINIO_URL = f"{os.getenv('MINIO_URL')}"
    if '//' in MINIO_URL:
        MINIO_URL = MINIO_URL.split('//', 1)[1]
    ACCESS_KEY = f"{os.getenv('MINIO_ACCESS_KEY')}"
    SECRET_KEY = f"{os.getenv('MINIO_SECRET_KEY')}"

    client = Minio(
        MINIO_URL,
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        secure=False  # Set to True if using HTTPS
    )

    try:
        # Bucket name
        bucket_name = "labtech"

        # Create bucket if it doesn't exist (optional)
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)

        # PDF file to upload
        local_pdf_path = "PDFs/evento.pdf"
        object_name = f"reservation-pdfs/{event_id}.pdf"  # Object key in bucket

        # Upload the file
        client.fput_object(
            bucket_name,
            object_name,
            local_pdf_path,
            content_type="application/pdf"
        )

        pdf_data ={
            "path":f"dwcorp.com.br:9000/{bucket_name}/{object_name}",
            "eventId": event_id,
        }

        reservation_manager = ReservationManager()
        reservation_manager.insert_pdf(pdf_data)

        print(f"Successfully uploaded {local_pdf_path} to {bucket_name}/{object_name}.")

    except S3Error as exc:
        print("Error occurred:", exc)