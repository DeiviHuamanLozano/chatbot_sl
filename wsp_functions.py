from datetime import datetime
import requests
import json
import subprocess
import concurrent.futures
import os
from config import WHATSAPP_TOKEN, WHATSAPP_PHONE_SID
from gcloud_functions import download_blob
import time

WEEKDAY_NAMES = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]

def convert_wav_to_mp4(input_wav: str, output_mp4: str, image_path: str) -> None:
    ffprobe_command = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {input_wav}"
    duration = subprocess.check_output(
        ffprobe_command, shell=True, encoding="utf-8"
    ).strip()

    command = f"ffmpeg -loop 1 -i {image_path} -i {input_wav} -t {duration} -c:v libx264 -pix_fmt yuv420p -c:a aac -strict experimental -b:a 192k {output_mp4}" #  -y

    subprocess.call(command, shell=True)


def send_message_wsp(alert_data: dict, nivel_riesgo: str, empresa: str, target_phone_numbers: list):
    gcloud_wav, fecha = alert_data["alert_path"], alert_data["alert_date"]

    wav_file_path = download_blob('conflictividad-core', gcloud_wav, "_".join(gcloud_wav.split("/")[2:]))
    mp4_file_path = wav_file_path.replace(".wav", ".mp4").replace(".mp3", ".mp4")
    print(wav_file_path)
    if os.path.exists("./wallpaper"):
        image_path = f"./wallpaper/agricultura.png"
    else:
        raise FileNotFoundError("No se encontro la carpeta 'wallpaper' en la ruta './wallpaper'")

    convert_wav_to_mp4(wav_file_path, mp4_file_path, image_path)

    content_type = "video/mp4"  # Especifica el tipo MIME correcto para el archivo

    url = "https://graph.facebook.com/v17.0/" + WHATSAPP_PHONE_SID + "/media"
    files = {"file": (mp4_file_path, open(mp4_file_path, "rb"), content_type)}
    data = {"messaging_product": "whatsapp", "type": content_type}
    headers = {"Authorization": "Bearer " + WHATSAPP_TOKEN}

    response = requests.post(url, files=files, data=data, headers=headers)
    result_whatsapp_media = response.json()

    media_object_id = result_whatsapp_media["id"]  # MEDIA OBJECT ID, el cual usaremos para enviar el archivo multimedia

    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S")
        
    template = {
        "name": "alerta_sl_update",
        "language": {"code": "es_PE"},
        "components": [
            {
                "type": "header",
                "parameters": [
                    {
                        "type": "video",
                        "video": {
                            "id": media_object_id,
                        },
                    }
                ],
            },
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": alert_data["source_alias"]},
                    {"type": "text", "text": WEEKDAY_NAMES[fecha.weekday()]},
                    {
                        "type": "text",
                        "text": fecha.date().strftime("%Y-%m-%d"),
                    },
                    {"type": "text", "text": fecha.strftime("%Y-%m-%d %H:%M:%S")[-8:-3]},
                    {"type": "text", "text": alert_data["gpt_generated_topic"]},
                    {"type": "text", "text": str(alert_data["found_keywords"]) if alert_data["found_keywords"] else "Sin keywords"},
                    {"type": "text", "text": alert_data["gpt_summary"]},
                    {"type": "text", "text": nivel_riesgo},
                    {"type": "text", "text": empresa},
                ],
            },
        ],
    }
    
    target_phone_numbers = list(set(target_phone_numbers))
    url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_SID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    for num in target_phone_numbers:
        data = {
            "messaging_product": "whatsapp",
            "to": num,
            "type": "template",
            "template": template,
        }
        print(data)
        time.sleep(2)
        response = requests.post(url, headers=headers, data=json.dumps(data))
        print(response.json())
        print(f"Enviado con exito a {num} :)")
        time.sleep(3)

    try:
        os.remove(wav_file_path)
        os.remove(mp4_file_path)
    except Exception as e:
        print(f"Error al eliminar los archivos: {e}")
