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
