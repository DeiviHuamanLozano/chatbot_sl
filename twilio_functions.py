from twilio.rest import Client
from config import *


def get_message_metadata(message_sid):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    return client.messages(message_sid).fetch()


def send_message(destination_number: str, message: str):
    client = Client(ACCOUNT_SID.strip(), AUTH_TOKEN.strip())
    print(f"Intento de enviar mensaje {TWILIO_PHONE_NUMBER},{destination_number},{message}")
    print(client)
    message = client.messages.create(
        from_=TWILIO_PHONE_NUMBER.strip(),
        to=str(destination_number),
        body=str(message)
    )

    return message.sid

# 'https://storage.googleapis.com/conflictividad-core/data/concatenated_audios/Radio_Famicarr/audio_prueba.ogg'
def send_audio(destination_number: str, audio_url: str):
    client = Client(ACCOUNT_SID.strip(), AUTH_TOKEN.strip())
    # print(str('"'+TWILIO_PHONE_NUMBER.strip()+'"'))
    message = client.messages.create(
        from_=TWILIO_PHONE_NUMBER.strip(),
        to=str(destination_number),
        media_url=[
            audio_url
        ]
    )

    return message.sid


"""
https://www.twilio.com/docs/content/content-api-resources
https://help.twilio.com/articles/223179808-Sending-and-receiving-MMS-messages
https://stackoverflow.com/questions/76010749/sending-ogg-file-to-whatsapp-using-twilio
"""
