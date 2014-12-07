import json
import getpass
import base64

from Crypto.Hash import SHA256
from Crypto.Cipher import AES

LOGIT_SALT = '-logit-salt'
PADDING = ' '
BLOCK_SIZE = 32


def _salted(password):
    """Salt the password."""
    return password + LOGIT_SALT


def _get_password(prompt=None):
    """Get password."""
    if not prompt:
        prompt = ('Enter your logit password (do not use this password '
                  'anywhere else): ')

    return getpass.getpass(prompt)


def get_secret_key(opts, password=None, prompt=None):
    """Get secret key."""
    if not hasattr(opts, 'secret_key'):
        if not password:
            password = _get_password(prompt=prompt)

        hash_ = SHA256.new()
        hash_.update(_salted(password))
        opts.secret_key = hash_.digest()

    return opts.secret_key


def _pad(s):
    """Pad."""
    return s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING


def encode_aes(cipher, secret):
    return base64.b64encode(cipher.encrypt(_pad(secret)))


def encrypt_json(secret_key, blob, file_):
    """Encrypt a json blob into a file stream in base64."""

    cipher = AES.new(secret_key)
    encoded = encode_aes(cipher, json.dumps(blob))

    file_.write(encoded)


def decode_aes(cipher, encrypted):
    """Decode AES."""
    return (
        cipher
        .decrypt(base64.b64decode(encrypted))
        .rstrip(PADDING)
    )


def decrypt_json(secret_key, base64):
    """Decrypt json."""
    cipher = AES.new(secret_key)
    decoded = json.loads(decode_aes(cipher, base64))
    return decoded
