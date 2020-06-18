import errno
import os
import sys
import tempfile
import subprocess

from os.path import join, abspath, expanduser, dirname


def get_home_dir_path(filename):
    """Resolve a filename in the user's home dir"""
    return abspath(join(expanduser('~'), filename))


def get_resource_path(filename):
    """Resolve a filename in the resources"""
    return abspath(join(dirname(__file__), filename))


def get_terminal_size():
    env = os.environ

    def ioctl_GWINSZ(fd):
        try:
            import fcntl
            import termios
            import struct
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
                                                 '1234'))
        except:
            return
        return cr

    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)

    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass

    if not cr:
        cr = (env.get('LINES', 25), env.get('COLUMNS', 80))

        try:
            cr = (env['LINES'], env['COLUMNS'])
        except:
            cr = (25, 80)
    return int(cr[1]), int(cr[0])


def unique_id_from_entry(entry):
    if 'id' in entry:
        return entry['id']

    return (
        '{}-{}'
        .format(entry.get('timestamp'),
                entry.get('category'))
    )


def make_sure_path_exists(path):
    """Make sure path exists."""
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


class bcolors:
    TIMESTAMP = '\033[94m'
    CATEGORY = '\033[93m'
    HEADER = '\033[95m'
    MENU = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


def get_console_input(prompt, use_vim=False):
    """Get input."""
    if use_vim:
        initial_message = "# %s\n\n" % prompt

        with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
            tf.write(initial_message.encode('utf-8'))
            tf.flush()

            subprocess.call(["vim", tf.name, "+normal G"])

            with open(tf.name, 'r') as f:
                lines = (
                    f.read()
                    .replace('\n\n', '\0')
                    .replace('\n', ' ')
                    .replace('\0', '\n')).splitlines()
            return '\n'.join([line.strip() for line in lines if not
                              line.startswith('#')]).strip()
    else:
        return input(prompt).strip()
