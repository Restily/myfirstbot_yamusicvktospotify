import base64

Token = ''
client_id = ''
client_secret = ''
login = ''
password = ''
access_token = ''

client_creds = f'{client_id}:{client_secret}'
clientenc_64 = base64.b64encode(client_creds.encode('ascii'))
client_64 = clientenc_64.decode('ascii')
