from cryptography.fernet import Fernet

with open('./creds/postgres_key.bin', 'rb') as file_object:
    for line in file_object:
        encrypted_key = line
with open('./creds/postgres_pwd.bin', 'rb') as file_object:
    for line in file_object:
        encrypted_pwd = line
# generate cipher_suite using key
cipher_suite = Fernet(encrypted_key)
# decrypt
decrypted_text = cipher_suite.decrypt(encrypted_pwd)
# convert to string
DB_PWD = bytes(decrypted_text).decode('utf-8')

