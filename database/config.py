from cryptography.fernet import Fernet
import os

key_path = os.path.expanduser("~/creds/postgres_key.bin")
pwd_path = os.path.expanduser("~/creds/postgres_pwd.bin")

with open(key_path, 'rb') as file_object:
    for line in file_object:
        encrypted_key = line
with open(pwd_path, 'rb') as file_object:
    for line in file_object:
        encrypted_pwd = line
# generate cipher_suite using key
cipher_suite = Fernet(encrypted_key)
# decrypt
decrypted_text = cipher_suite.decrypt(encrypted_pwd)
# convert to string
DB_PWD = bytes(decrypted_text).decode('utf-8')

