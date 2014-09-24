import yaml
from os.path import join, abspath, expanduser, dirname


def get_home_dir_path(filename):
    """Resolve a filename in the user's home dir"""
    return abspath(join(expanduser('~'), filename))


def get_resource_path(filename):
    """Resolve a filename in the resources"""
    return abspath(join(dirname(__file__),
                        'res', filename))


def load_yaml_resource(filename):
    """Load a yaml file from the resources"""
    with open(get_resource_path(filename), 'r') as f:
        return yaml.load(f)


def get_terminal_size():
    import os
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


class bcolors:
    TIMESTAMP = '\033[94m'
    CATEGORY = '\033[93m'
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
