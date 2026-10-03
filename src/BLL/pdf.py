import os
import tempfile
from datetime import datetime
from typing import Dict, Any
import typst
from minio import Minio
from BLL import FlowController
from DAL import ReservationManager
import json


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


# Longest text kept per field, so one request cannot make the PDF huge or slow to build.
PDF_FIELD_LIMIT = 2000
PDF_SHORT_FIELD_LIMIT = 200
PDF_LONG_FIELDS = frozenset({"description", "resources", "students_monitors", "target_public",
                             "entrepreneurial_path", "extension_project"})


def pdf_fields(values):
    """Strings for data.json: None becomes empty, everything is text and length-capped."""
    cleaned = {}
    for key, value in values.items():
        text = "" if value is None else str(value)
        limit = PDF_FIELD_LIMIT if key in PDF_LONG_FIELDS else PDF_SHORT_FIELD_LIMIT
        cleaned[key] = text[:limit]
    return cleaned


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
        print(f"Erro ao processar data/hora da reserva: {type(e).__name__}")

    # Define valores padrão para campos que podem não ter sido informados
    entrepreneurial_path = event_data['entrepreneuralPath'] or "Não associado a trilha empreendedora"
    extension_project = event_data['extensionProject'] or "Não associado a projeto de extensão"

    students_monitors = resolve_jsonlist(event_data['studentsMonitors'], "Sem alunos monitores")
    recursos_necessarios = resolve_jsonlist(event_data['resources'], "Recursos Necessários Não Informados!")
    publico_alvo = resolve_jsonlist(event_data['targetPublic'], "Publico Alvo Não Informado!")

   # if isinstance(event_data['studentsMonitors'], list):
   #     students_monitors =', '.join(event_data['studentsMonitors'])
   # else:
   #     students_monitors = event_data['studentsMonitors'] or "Sem alunos monitores"


    date = data_evento
    hours_start = hora_inicio
    hours_end = hora_final


    typst_text = f"""
#let d = json("data.json")

// Título do Evento
#set text(
  font: "New Computer Modern",
  size: 14pt
)
#align(center)[
  = "Event name"
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

    if x != 0 {{gray.lighten(55%)}}
    else {{gray.lighten(35%)}},
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

#table(
  columns: 2,
  [Responsável:], [#raw(d.organizer_name)],
  [E-mail do Responsável:], [#raw(d.organizer_email)],
  [Telefone:], [#raw(d.organizer_phone)],
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

    if x != 0 {{blue.lighten(59%)}}
    else {{blue.lighten(45%)}},
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
  [Tipo de Evento:], [#raw(d.event_type)],
  [ODS:], [#raw(d.ods)],
  [Descrição:], [#raw(d.description)],
  [Curso:], [#raw(d.course)],
  [Número de Participantes Esperados:], [#raw(d.expected_subscribers)],
  [Trilha Empreendedora:], [#raw(d.entrepreneurial_path)],
  [Projeto de Extensão:], [#raw(d.extension_project)],
  
)



#table(
  columns: 2,
  [Público Alvo:], [#raw(d.target_public)],
  [Recursos Necessários:], [#raw(d.resources)],
  [Alunos Monitores:], [#raw(d.students_monitors)],
  
)


#set text(
  font: "New Computer Modern",
  size: 14pt
)

// Evento

*Informações da Reserva do Evento:*

#set text(
  font: "New Computer Modern",
  size: 11pt
)

#set table(
  stroke: luma(v),
  gutter: 0.2em,
  fill: (x, y) =>

    if x != 0 {{orange.lighten(50%)}}
    else {{orange.lighten(30%)}},
  inset: (right: 1.5em),
)

#table(
  columns: 2,
  
  [Sala:], [#raw(d.room)],
  [Data:],[#raw(d.date)],
  [Horário de inicio:],[#raw(d.hours_start)],
  [Horário final:],[#raw(d.hours_end)], 
  
)
    """

    # Client-supplied text never enters the Typst source: it goes to data.json and
    # the template reads it with #json, so markup in a field renders as plain text.
    fields = pdf_fields({
        "organizer_name": str((event_data['organizer'].get('email') or '').split('@')[0]),
        "organizer_email": event_data['organizer'].get('email'),
        "organizer_phone": event_data['organizer'].get('phone'),
        "event_type": event_data['eventTypeId'],
        "ods": name_ods,
        "description": event_data['description'],
        "course": event_data['graduationId'],
        "expected_subscribers": event_data['expectedSubscribers'],
        "entrepreneurial_path": entrepreneurial_path,
        "extension_project": extension_project,
        "target_public": publico_alvo,
        "resources": recursos_necessarios,
        "students_monitors": students_monitors,
        "room": event_data['roomType'],
        "date": date,
        "hours_start": hours_start,
        "hours_end": hours_end,
    })

    # Isola arquivos temporários por evento para que aprovações simultâneas
    # não sobrescrevam o PDF umas das outras nem deixem arquivo local no serviço.
    with tempfile.TemporaryDirectory(prefix=f"pdf-{event_id}-") as pdf_dir:
        typst_file_path = os.path.join(pdf_dir, "evento.typ")
        with open(typst_file_path, "w", encoding="utf-8") as typ_file:
            typ_file.write(typst_text)
        with open(os.path.join(pdf_dir, "data.json"), "w", encoding="utf-8") as data_file:
            json.dump(fields, data_file, ensure_ascii=False)

        pdf_path = os.path.join(pdf_dir, "evento.pdf")
        with open(pdf_path, "wb") as pdf_file:
            pdf_file.write(typst.compile(typst_file_path))

        save_pdf(event_id, pdf_path)


def save_pdf(event_id, local_pdf_path):
    with open(local_pdf_path, "rb") as pdf_file:
        pdf_bytes = pdf_file.read()

    reservation_manager = ReservationManager()
    raw_minio_url = (os.getenv("MINIO_URL") or "").strip()
    pdf_data = {
        "eventId": str(event_id),
        "content": pdf_bytes,
        "filename": f"{event_id}.pdf",
        "contentType": "application/pdf",
        "path": f"/events/{event_id}/pdf",
    }

    # O Mongo é o armazenamento padrão do PDF. Se existir MinIO, ele recebe
    # uma cópia; falha de MinIO não impede salvar/servir o PDF pelo Mongo.
    if raw_minio_url:
        public_url = raw_minio_url.rstrip("/")
        minio_endpoint = public_url.split("//", 1)[1] if "//" in public_url else public_url
        access_key = os.getenv("MINIO_ACCESS_KEY") or ""
        secret_key = os.getenv("MINIO_SECRET_KEY") or ""

        try:
            client = Minio(
                minio_endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=public_url.startswith("https://"),
            )
            bucket_name = "labtech"
            if not client.bucket_exists(bucket_name):
                client.make_bucket(bucket_name)

            object_name = f"reservation-pdfs/{event_id}.pdf"
            client.fput_object(
                bucket_name,
                object_name,
                local_pdf_path,
                content_type="application/pdf",
            )
            pdf_data["path"] = f"{public_url}/{bucket_name}/{object_name}"
        except Exception as exc:
            print("MinIO upload failed; PDF remains stored in Mongo:", type(exc).__name__)

    reservation_manager.insert_pdf(pdf_data)


def resolve_jsonlist(event_data, errormsg):

    #tira o [] da list dentro do body
    if isinstance(event_data, list):

        return ', '.join(event_data)

    else:

        return event_data or errormsg
