import requests

url = "https://blockstream.info/api/blocks/tip/hash"
response = requests.get(url)

print(response.text)