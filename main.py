from fastapi import FastAPI, Request, Form, Depends, BackgroundTasks
from twilio_functions import *
from datetime import datetime
from models import WSPAlert
from db import retrieve_today_earliest_alert, search_keyword_alert, get_clientes_alerta,  get_clientes_aa, get_source_alias, update_alert_values, retrieve_count_earliest_alert, retrieve_count_especific_day, get_clients_from_topic
from gcloud_functions import download_blob, upload_file_to_blob  # , list_bucket_folder
from wsp_functions import send_message_wsp
from utilities import convert_to_ogg
from dotenv import load_dotenv
import openai
import json
import os
import shutil
import time
import random

load_dotenv()

app = FastAPI()

ACTIVE_ALERTS = {}
FECHA_ACTUAL = datetime.now().date()

#num_tageadores = ['964895356', '963191165', '972850985']
num_tageadores = os.getenv('NUM_TAGGEADORES')

if num_tageadores:
    num_tageadores = num_tageadores.split(',')
    
sender_tageadores_phone_number = [f"whatsapp:+51{num}" for num in num_tageadores]

list_sender_clientes_aa = get_clientes_aa()
sender_clientes_aa = [f"whatsapp:+{num}" for num in list_sender_clientes_aa]

#query_nums = get_clients_from_topic('agricultura')
#sender_clientes_phone_number = [f"whatsapp:+{num}" for num in query_nums]

#get_clientes_alerta(861)

def give_alert_logic() -> tuple:
    # * 1. Get earliest alert of the current day
    earliest_alert = retrieve_today_earliest_alert().iloc[0].to_dict()
    source_alias = get_source_alias(earliest_alert["id_source"])
    earliest_alert['source_alias'] = source_alias
    earliest_alert['id'] = earliest_alert["id_alerta"]
    earliest_alert['alert_path'] = earliest_alert['alert_path'].replace("https://storage.googleapis.com/conflictividad-core/", "")
    # * 2. Download the audio file
    file_path = download_blob(os.environ['GCLOUD_STORAGE_BUCKET'], earliest_alert["alert_path"])

    # * 3. Convert the audio file to .ogg
    ogg_file_path = file_path.replace(".wav", ".ogg")
    convert_to_ogg(file_path, ogg_file_path)
    time.sleep(2)
    # * 4. Upload the .ogg file to the bucket to send it later
    audio_public_url = upload_file_to_blob(os.environ['GCLOUD_STORAGE_BUCKET'], ogg_file_path, f"{earliest_alert['id']}.ogg")
    print(audio_public_url)
    time.sleep(10)
    os.remove(file_path)
    os.remove(ogg_file_path)

    return earliest_alert, audio_public_url

#give_alert_logic()

FECHA_ACTUAL = datetime.now().date()
DIA_ACTUAL = datetime.now().strftime("%A")

def analyze_response_with_openai(message_body: str):
    """
    Analiza el mensaje del usuario para clasificar la alerta y el nivel de riesgo.

    Args:
        message_body (str): Mensaje recibido del usuario en lenguaje natural.

    Returns:
        tuple:
            response: Respuesta de OpenAI.
            dict|str: Un diccionario con las claves "classification" y "risk_level".
    """
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un asistente que evalúa respuestas de un usuario respecto a alertas de seguridad "
                    "Clasifica si el usuario calificó la alerta como 'falso positivo' o 'verdadero positivo', y el nivel de riesgo como 'bajo', 'medio' o 'alto'."
                )
            },
            {"role": "user", "content": message_body}
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "classify_alert",
                    "description": "Clasifica una alerta y su nivel de riesgo.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "classification": {
                                "type": "string",
                                "enum": ["falso positivo", "verdadero positivo"]
                            },
                            "risk_level": {
                                "type": "string",
                                "enum": ["bajo", "medio", "alto"]
                            }
                        },
                        "required": ["classification", "risk_level"]
                    }
                }
            }, {
                "type": "function",
                "function": {
                    "name": "obtener_fecha_rango",
                    "description": "Obtiene el rango de fechas asociadas a la petición de reporte",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "format": "date",
                                "description": f"Fecha inicial en formato YYYY-MM-DD. Ten en cuenta que la fecha actual es {DIA_ACTUAL}, {FECHA_ACTUAL}"
                            },
                            "end_date": {
                                "type": "string",
                                "format": "date",
                                "description": f"Fecha final en formato YYYY-MM-DD, si no se especifica, se toma la fecha actual {DIA_ACTUAL}, {FECHA_ACTUAL}"
                            },
                        },
                        "required": ["start_date", "end_date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "obtener_fecha_especifica",
                    "description": "Obtiene la fecha asociada a la peticion de reporte",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "format": "date",
                                "description": f"Fecha exacta en formato YYYY-MM-DD del cual generar el reporte especifico. Ten en cuenta que la fecha actual es {DIA_ACTUAL}, {FECHA_ACTUAL}"
                            }
                        },
                        "required": ["date"]
                    }
                }
            }
        ]
    )

    llm_response = None
    try:
        llm_response = response.choices[0].message.tool_calls[0].function.arguments
    except:
        llm_response = response.choices[0].message.content
        # print(response.choices[0])

    return response, llm_response


@app.get("/alive")
async def alive() -> dict:
    return {
        "twilio_number": TWILIO_PHONE_NUMBER,
        "status": "alive"
    }


async def get_request_form(request: Request):
    # print(request)
    # print(dir(request))
    # print(vars(request))

    return await request.form()


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@app.get("/alive")
async def alive() -> dict:
    return {
        "twilio_number": TWILIO_PHONE_NUMBER,
        "status": "alive"
    }


@app.post("/send-wsp-alert")
async def send_wsp_alert(alert: WSPAlert) -> dict:
    file_path = alert.gcloud_wav
    audio_path = download_blob(os.environ['GCLOUD_STORAGE_BUCKET'], file_path)
    ogg_file_path = audio_path.replace(".wav", ".ogg")
    convert_to_ogg(audio_path, ogg_file_path)
    audio_public_url = upload_file_to_blob(os.environ['GCLOUD_STORAGE_BUCKET'], ogg_file_path, "wsp_alert_audio.ogg")

    if isinstance(alert.fecha, datetime):
        alert.fecha = alert.fecha.strftime('%d-%m-%Y  %H:%m')

    alert_message = f"""
    Alerta de *{alert.radio_name}* ({alert.fecha}):\n\n*{alert.gpt_tema}*\n\n{alert.summary}\n
    """

    #query_nums = get_clients_from_topic(alert.tematica)

    
    for n in sender_tageadores_phone_number:
        try:
            send_message(n, alert_message)
            send_audio(n, audio_public_url)
            time.sleep(random.randint(1, 5))
            print(f"Mensaje enviado a {n}")
        except Exception as e:
            print(f"Error al enviar mensaje por Twilio a {n}: {e}")

    try:
        os.remove(audio_path)
        os.remove(ogg_file_path)
    except Exception as e:
        print(f"Error al eliminar archivos: {e}")

    return {
        **alert.model_dump(),
        "nums": query_nums
    }


@app.post("/twilio-webhook")
async def twilio_webhook(background_tasks: BackgroundTasks, request=Depends(get_request_form)) -> dict:
    # print(request)
    # print(dir(request))
    # print(json.dumps(vars(request), indent=2, default=str))

    sender_phone_number = request["From"]
    message_body = request["Body"]
    message_type = request["MessageType"]

    print(f"{sender_phone_number=}")
    print(
        f"From: {sender_phone_number}, Body: {message_body}, MessageType: {message_type}")

    # message_sid = request["MessageSid"]
    # metadata = get_message_metadata(message_sid)
    # print(dir(metadata))
    # print(json.dumps(vars(metadata), indent=2, default=str))

    # print(background_tasks)
    # print(dir(background_tasks))
    # print(vars(background_tasks))

    # send_audio(sender_phone_number)
    if 'rango' in message_body:
        response, fecha_obtenida = analyze_response_with_openai(message_body)
        print("consolidado")
        response_dict = json.loads(fecha_obtenida)
        fecha_inicial = response_dict.get("start_date")
        fecha_final = response_dict.get("end_date")
        total = retrieve_count_earliest_alert(fecha_inicial, fecha_final)

        report_message = f"Total de alertas no revisadas *(desde {fecha_inicial} hasta {fecha_final})*: {total}"
        send_message(sender_phone_number, report_message)
        return {
            "status": "Message sent",
            "number": sender_phone_number,
            "message_type": report_message,
        }
    if 'especifico' in message_body:
        response, fecha_obtenida = analyze_response_with_openai(message_body)
        print("especifico")
        response_dict = json.loads(fecha_obtenida)
        fecha = response_dict.get("date")
        total = retrieve_count_especific_day(fecha)
        report_message = f"Total de alertas no revisadas del día *{fecha}*: {total}"

        send_message(sender_phone_number, report_message)
        return {
            "status": "Message sent",
            "number": sender_phone_number,
            "message_type": report_message,
        }

    if '/alerta' in message_body:
        # send_message(sender_phone_number, "IA: Te dare más información sobre la alerta")
        earliest_alert, audio_public_url = give_alert_logic()
        print(f"{earliest_alert=}")
        alert_message = f"""
        Alerta de *{earliest_alert['source_alias']}* ({earliest_alert['alert_date'].strftime('%d-%m-%Y  %H:%m')}):\n\n*{earliest_alert['gpt_generated_topic']}*\n\n{earliest_alert['gpt_summary']}\n
Evalua si la alerta es un _"falso positivo"_ o un _"verdadero positivo"_ (alerta real). Asimismo, evalua el nivel de riesgo de la alerta como _"bajo"_, _"medio"_ o _"alto"_.
        """

        ACTIVE_ALERTS[sender_phone_number] = {
            'earliest_alert': earliest_alert,
            'alert_message': alert_message,
            'audio_alert': audio_public_url
        }
        time.sleep(10)
        send_message(sender_phone_number, alert_message)
        send_audio(sender_phone_number, audio_public_url)

    elif sender_phone_number in ACTIVE_ALERTS:
        alert_data = ACTIVE_ALERTS[sender_phone_number]
        earliest_alert = alert_data['earliest_alert']
        audio_public_url = alert_data['audio_alert']

        response, llm_response = analyze_response_with_openai(message_body)
        send_message(sender_phone_number, f"IA: {llm_response}")
        # print("Envio de diccionario")
        if isinstance(llm_response, dict):
            ACTIVE_ALERTS.pop(sender_phone_number)

        update_alert_values(earliest_alert['id'], llm_response)

        update_dict = json.loads(llm_response)
        # print(update_dict)
        if update_dict['classification'] == 'verdadero positivo':
            nivel_riesgo = update_dict['risk_level']
            alert_message = f"""
        Alerta de *{earliest_alert['source_alias']}* ({earliest_alert['alert_date'].strftime('%d-%m-%Y  %H:%m')}):\n\n*Nivel de riesgo: {update_dict['risk_level']}* \n\n*{earliest_alert['gpt_generated_topic']}*\n\n{earliest_alert['gpt_summary']}\n
        """
            # alert.model_dump()
            print('########## CLIENTES ESPECIFICOS#########')
            list_clientes_phone_alerta = get_clientes_alerta(earliest_alert['id_source'])

            print(list_clientes_phone_alerta)
            print('########## CLIENTES TOTALES ############')
            list_clientes_phone_number = list_sender_clientes_aa + list_clientes_phone_alerta

            print(list_clientes_phone_number)

            try:
                time.sleep(2)
                send_message_wsp(earliest_alert, nivel_riesgo, earliest_alert['name'], [n.replace("whatsapp:+", "") for n in list_clientes_phone_number])
                
            except Exception as e:
                print(f"Error al enviar mensaje por WhatsApp Business API: {e}")

        # enviar a clientes con etiqueta
    else:
        # Informacion sobre las funcionalidades del bot
        # /alertas
        # rango
        # especifico
        send_message(sender_phone_number, f"""
        ¡Hola!👋 Soy Apoyo Escucha Bot 🤖, un asistente virtual que te brindará alertas sobre las noticias más importantes de la agricultura 🧑‍🌾.
Si quieres:
    - obtener las últimas alertas escriba */alerta*
    - obtener el informe de alertas no etiquetadas de un día fijo escriba *especifico*
    - obtener el informe de alertas no etiquetadas en un rango de tiempo escriba *rango*
                     """)

    return {
        "status": "Message sent",
        "number": sender_phone_number,
        "message_type": message_type,
    }


"""
https://platform.openai.com/docs/guides/function-calling

https://cookbook.openai.com/examples/assistants_api_overview_python

https://cookbook.openai.com/examples/fine_tuning_for_function_calling

https://cookbook.openai.com/examples/how_to_call_functions_for_knowledge_retrieval

https://cookbook.openai.com/examples/how_to_call_functions_with_chat_models

https://platform.openai.com/docs/guides/structured-outputs?context=without_parse#examples

https://cookbook.openai.com/examples/structured_outputs_intro

https://cookbook.openai.com/examples/structured_outputs_multi_agent#data-pre-processing-agent

https://gmnithinsai.medium.com/structured-output-llm-routers-in-langchain-da26987b641a

https://github.com/ApoyoAnalyticsPE/vitapro-pipeline/blob/main/tasks/datastorage.py

DUDAS:
    - El chatbot admite preguntas abiertas
    - Entregar audio/video como respuesta

    PRIORIDAD 2:
QUERIES:
    - Q se ha dicho del congresista tal?
    - Sobre la alerta, dame mas contexto?
    - Quien lo ha dicho?
    - Donde se ha dicho? Sobre que zona se esta hablando?
    - Hazme un resumen de las principales noticias del sector
    - Que temas implica potenciales protestas, riesgos para las empresas
    - Quienes son los principales actores/personas clave del sector?

    NIVELES DE SEGMENTACION
        - Riesgo bajo (informativo)
        - Riesgo medio (alerta, informacion relevante)
        - Riesgo alto (protesta, huelga, conflictos, critica del sector)
    
    PRIORIDAD 1:
    GENERAR UNA HEURISTICA PARA DETERMINAR LOS RIESGOS DE LAS ALERTAS
        - Puede ser con subtemas: toma de carreteras, accidentes, seguridad, etc.
"""
