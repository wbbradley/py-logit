import cStringIO
import tempfile
import mock

from attrdict import AttrDict

from logit.main import get_arg_parser, main
from logit.crypt import get_secret_key, encrypt_json, decrypt_json


def test_get_arg_parser():
    """Test get arg parser."""
    get_arg_parser()


@mock.patch('logit.main.get_console_input')
@mock.patch('logit.crypt.getpass.getpass')
def test_main(mock_getpass, mock_input):
    """Test adding a note."""
    password = 'p@ssword'
    mock_getpass.side_effect = [
        password,
        Exception('called too many times'),
    ]
    mock_input.side_effect = [
        'note',
        'This is a test note',
        Exception('called too many times'),
    ]

    with tempfile.NamedTemporaryFile() as file_:
        entry = {
            "category": "note",
            "timestamp": "2014-12-01T02:43:04.384669",
            "message": "This is a test.",
            "installation": "b8f2e978-f638-492a-022f-abce33fc8203",
            "id": "97c6683d-ff1f-4791-a313-6d4588fa5aaa",
        }
        length = file_.tell()
        opts = AttrDict()
        encrypt_json(get_secret_key(opts, password=password), entry, file_)
        assert length < file_.tell()
        length = file_.tell()
        main(argv=['--log={}'.format(file_.name)])
        file_.seek(0, 2)
        assert length < file_.tell()


def test_get_secret_key():
    """Test get secret key."""
    opts = AttrDict()
    get_secret_key(opts, password='blahblahblah')
    assert opts.secret_key is not None


def test_encrypt_decrypt_json():
    """Test encrypt decrypt json."""
    stream = cStringIO.StringIO()
    secret_key = b'\xd3\x81by(!]\xbdU0\xd0\xe2\xa0\xd6j\xcc\xca\x92\x0e\x8c\xd7\xb5~D/1\xdc4\xbd\xb2w\x06'  # noqa
    blob_data = {'test': 'data', '1': 2}
    encrypt_json(secret_key, blob_data, stream)
    stream.seek(0)
    encrypted = stream.read()
    assert len(encrypted) > 0

    decrypted_blob = decrypt_json(secret_key, encrypted)
    assert decrypted_blob == blob_data


def test_encrypt_decrypt_json_failure():
    """Test encrypt decrypt json."""
    stream = cStringIO.StringIO()
    secret_key = b'\xd3\x81by(!]\xbdU0\xd0\xe2\xa0\xd6j\xcc\xca\x92\x0e\x8c\xd7\xb5~D/1\xdc4\xbd\xb2w\x06'  # noqa
    blob_data = {'test': 'data', '1': 2}
    encrypt_json(secret_key, blob_data, stream)
    stream.seek(0)
    encrypted = stream.read()
    assert len(encrypted) > 0
    bad_secret_key = b'\xe3\x81by(!]\xbdU0\xd0\xe2\xa0\xd6j\xcc\xca\x92\x0e\x8c\xd7\xb5~D/1\xdc4\xbd\xb2w\x06'  # noqa

    try:
        decrypt_json(bad_secret_key, encrypted)
    except ValueError:
        pass
    else:
        assert False
