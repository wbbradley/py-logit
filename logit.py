import sys
from utils import get_home_dir_path, load_yaml_resource
import logging
import uuid
import argparse
import json
from datetime import datetime


logging.basicConfig(filename=get_home_dir_path('.logit.log'),
                    level=logging.INFO)

log = logging.getLogger('logit')

LOGIT_FILENAME = 'logit.txt'
LOGIT_BUCKET = 'logit-logs'

categories = load_yaml_resource('categories.yaml')


def get_arg_parser():
    """Get the argument parser"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--check',
        dest='check',
        action='store_true',
        default=False,
        help='Test the integrity of the logit.txt file',
        )
    parser.add_argument(
        '--backup',
        dest='backup',
        action='store_true',
        default=False,
        help=('Backup the logit.txt file to the {} bucket in S3'
              .format(LOGIT_BUCKET)),
        )
    parser.add_argument(
        '--aws-access-key-id',
        dest='aws_access_key_id',
        action='store',
        default=None,
        help='When running backup, use this AWS access key id',
        )
    parser.add_argument(
        '--aws-secret-access-key',
        dest='aws_secret_access_key',
        action='store',
        default=None,
        help='When running backup, use this AWS access key id',
        )
    parser.add_argument(
        '-c',
        dest='category',
        help='Message category',
        )
    parser.add_argument(
        '-m',
        dest='message',
        help='Log message',
        )
    parser.add_argument(
        '-l',
        dest='list',
        action='store_true',
        default=False,
        help='Print the current logit log',
        )
    return parser


def parse_args(argv):
    """Parse command line arguments"""
    parser = get_arg_parser()
    return parser.parse_args(argv)


def _get_install_config(read_config):
    install_config = None

    if read_config:
        config_filename = get_home_dir_path('.config/logit')
        try:
            with open(config_filename, 'r') as f:
                install_config = json.load(f)

        except (IOError, ValueError):
            pass

    if install_config is None:
        # Create a new id for this installation
        install_config = {
            'uuid': str(uuid.uuid4()),
            'config_time': datetime.utcnow().isoformat(),
        }

        try:
            with open(config_filename, 'w') as f:
                config_str = json.dumps(install_config, sort_keys=True,
                                        indent=4)
                f.write(config_str)

        except:
            log.warn('failed to save config to %s', config_filename)
            raise

    assert install_config
    return install_config


def get_install_id(read_config=True):
    """Get this installation's ID"""
    return _get_install_config(read_config)['uuid']


def _create_backup_key_name():
    return (
        '{}-{}-{}'
        .format(datetime.utcnow().isoformat(), get_install_id(),
                LOGIT_FILENAME)
    )


def _do_backup(opts):
    """Perform a backup to S3."""
    if not opts.aws_access_key_id or not opts.aws_secret_access_key:
        print ('You must specify AWS access credentials with access '
               'to a bucket called logit-logs')

    else:
        import boto
        from boto.s3.key import Key

        s3conn = boto.connect_s3(
            aws_access_key_id=opts.aws_access_key_id,
            aws_secret_access_key=opts.aws_secret_access_key)
        bucket = s3conn.get_bucket(LOGIT_BUCKET)
        key = Key(bucket)
        key.key = _create_backup_key_name()
        key.set_contents_from_filename(get_home_dir_path(LOGIT_FILENAME))


def _do_logit(opts):
    category = opts.category

    while category not in categories:
        print "Existing categories:"
        for key, schema in categories.iteritems():
            print "\t{}: {}".format(key, schema['description'])

        category = raw_input('Category: ')
        if not category:
            return

    entry = {
        'category': category,
        'timestamp': datetime.utcnow().isoformat(),
    }

    fields = categories[category].get('fields') or {}
    for field, description in fields.iteritems():
        value = raw_input(description)
        if value:
            entry[field] = value

    entry['message'] = opts.message or raw_input('Notes: ')

    if entry.get('message'):
        with open(get_home_dir_path(LOGIT_FILENAME), 'a') as f:
            f.write(json.dumps(entry))
            f.write('\r\n')
    else:
        print 'No logit entry entered.'


def _do_list():
    with open(get_home_dir_path(LOGIT_FILENAME), 'r') as f:
        print f.read()


def _do_check():
    with open(get_home_dir_path(LOGIT_FILENAME), 'r') as f:
        for line in f:
            json.loads(line)

    print "Looks good."


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    opts = parse_args(argv)

    if opts.check:
        _do_check()
    elif opts.list:
        _do_list()
    elif not opts.backup:
        _do_logit(opts)

    if opts.backup:
        _do_backup(opts)


if __name__ == '__main__':
    main()
