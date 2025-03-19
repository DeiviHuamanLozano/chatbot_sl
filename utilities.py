from pydub import AudioSegment

def convert_to_ogg(source_file, destination):
    segment = AudioSegment.from_wav(source_file)
    segment.export(destination, format="ogg", codec='libopus')

"""
FileNotFoundError: [Errno 2] No such file or directory: 'ffprobe'

https://stackoverflow.com/questions/76010749/sending-ogg-file-to-whatsapp-using-twilio
sudo apt-get install ffmpeg
"""