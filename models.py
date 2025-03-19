from pydantic import BaseModel, Field


class WSPAlert(BaseModel):
    gcloud_wav: str # input_wav
    fecha: str      # fecha
    radio_name: str # estacion_formal
    gpt_tema: str   # gpt_generated_topic_alert
    keywords: str   # str_keywords
    summary: str    # gpt_summary_alert
    tematica: str   # tema


"""
FORMAT:

message_data = {
    'input_wav': path_audio_alert,
    'file_path_mp4': path_audio_alert.replace('.wav', '.mp4').replace('.mp3', '.mp4'),
    'fecha': fecha,
    'radio_name': estacion_formal,
    'gpt_tema': ml_vars['gpt_generated_topic_alert'],
    'keywords': str_keywords,
    'summary': ml_vars['gpt_summary_alert'],
    'tematica': tema,

}

MOCK:

{
  "gcloud_wav": "data/concatenated_audios/Radio_Huracan/audio_101220240734.wav",
  "fecha": "2024-12-10 07:34:00",
  "radio_name": "Radio Huracan 101.5 FM",
  "gpt_tema": "Inundaciones y su efecto en la agricultura local",
  "keywords": "Sin keywords",
  "summary": "Los ríos de Silbabaca han aumentado su caudal debido a intensas lluvias, inundando cultivos y viviendas cercanas. Algunos productos y objetos se perdieron en las aguas. Comuneros de Aguachini, preocupados por la situación, ataron un vehículo para evitar que la corriente lo arrastre. Solicitan la construcción de un puente en la zona para garantizar la seguridad de los escolares.",
  "tematica": "agricultura"
}
"""
