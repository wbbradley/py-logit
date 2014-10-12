import sys
from datetime import datetime, timedelta
import logging
import textwrap
import uuid
import argparse
import json

from utils import (get_home_dir_path, load_yaml_resource, get_terminal_size,
                   bcolors, unique_id_from_entry)

logging.basicConfig(filename=get_home_dir_path('.logit.log'),
                    level=logging.INFO)

logger = logging.getLogger('logit')

LOGIT_FILENAME = 'logit.txt'

categories = load_yaml_resource('categories.yaml')


def get_arg_parser():
    """Get the argument parser"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--todo',
        dest='todo_list',
        action='store_true',
        default=False,
        help='Launch interactive todo tracker',
        )
    parser.add_argument(
        '--check',
        dest='check',
        action='store_true',
        default=False,
        help='Test the integrity of the logit.txt file',
        )
    parser.add_argument(
        '--back-date',
        dest='back_date',
        action='store',
        default=None,
        help='Backdate a log entry. --backdate 2014-10-03',
        )
    parser.add_argument(
        '--backup',
        dest='backup',
        action='store_true',
        default=False,
        help='Backup the logit.txt file to an S3 bucket',
        )
    parser.add_argument(
        '--s3-bucket',
        dest='s3_bucket',
        action='store',
        help='When running backup, use this AWS access key id',
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
            logger.warn('failed to save config to %s', config_filename)
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
    if (not opts.aws_access_key_id
            or not opts.aws_secret_access_key
            or not opts.s3_bucket):
        print ('You must specify AWS access credentials and an S3 bucket name '
               '(see --help)')

    else:
        import boto
        from boto.s3.key import Key

        s3conn = boto.connect_s3(
            aws_access_key_id=opts.aws_access_key_id,
            aws_secret_access_key=opts.aws_secret_access_key)
        bucket = s3conn.get_bucket(opts.s3_bucket)
        key = Key(bucket)
        key.key = _create_backup_key_name()
        key.set_contents_from_filename(get_home_dir_path(LOGIT_FILENAME))


def logit(entry, timestamp):
    entry['timestamp'] = timestamp.isoformat()
    entry['id'] = str(uuid.uuid4())

    assert 'category' in entry
    entry['message'] = entry.get('message') or raw_input('Notes: ')

    if entry.get('message'):
        with open(get_home_dir_path(LOGIT_FILENAME), 'a') as f:
            f.write(json.dumps(entry))
            f.write('\r\n')
    else:
        print 'No logit entry entered.'


def parse_datetime(date_string):
    """Convert 2014-10-2 to a datetime, etc..."""
    return datetime(*[int(n) for n in date_string.split('-')])


def _do_logit(opts):
    category = opts.category
    width, _ = get_terminal_size()

    for entry in _generate_entries_stream():
        week_ago = (datetime.utcnow() - timedelta(weeks=1)).isoformat()
        if entry['timestamp'] > week_ago:
            if not category or entry.get('category') == category:
                print_entry(entry, width=width)

    while category not in categories:
        print "Existing categories:"

        for key, schema in categories.iteritems():
            print "\t{}: {}".format(key, schema['description'])

        category = raw_input('Category: ')
        if not category:
            return

    entry = {'category': category}
    if opts.message:
        entry['message'] = opts.message

    fields = categories[category].get('fields') or {}
    for field, description in fields.iteritems():
        value = raw_input(description)
        if value:
            entry[field] = value

    timestamp = datetime.utcnow()
    if opts.back_date:
        timestamp = parse_datetime(opts.back_date)

    print
    logit(entry, timestamp)


def _longest_category(categories):
    return max(len(category) for category in categories)


def print_entry(entry, prefix='', width=0):
    timestamp = entry.get('timestamp', '')
    if len(timestamp) == 19:
        timestamp = timestamp[:-3].replace('T', ' ')
    elif len(timestamp) == 26:
        timestamp = timestamp[:-10].replace('T', ' ')
    else:
        timestamp = None

    if not timestamp:
        timestamp = '-no timestamp-'

    category = (
        entry.get('category', 'note').rjust(_longest_category(categories))
    )
    prefix_len = len('{prefix}{timestamp} : {category} : '.format(
        prefix=prefix,
        timestamp=timestamp,
        category=category,
    ))
    pretty_prefix = (
        (bcolors.MENU + prefix + bcolors.ENDC +
         bcolors.TIMESTAMP + '{timestamp}' + bcolors.ENDC +
         ' : ' + bcolors.CATEGORY + '{category}' + bcolors.ENDC +
         ' : ').format(timestamp=timestamp, category=category)
    )
    message = entry.get('message')
    if prefix_len >= width:
        print pretty_prefix + message
    else:
        lines = textwrap.wrap(message, width - prefix_len) or ['']
        print pretty_prefix + lines[0]
        for line in lines[1:]:
            print ' ' * prefix_len + line


def _generate_entries_stream():
    """Generate all the entries from the local logit file"""
    with open(get_home_dir_path(LOGIT_FILENAME), 'r') as f:
        for line, entry in enumerate(f, start=1):
            try:
                yield json.loads(entry)
            except ValueError:
                logger.exception('error on line %d of logit log', line)


def _compare_entries_by_timestamp(x, y):
    if x.get('timestamp', '') < y.get('timestamp', ''):
        return -1
    else:
        return 1


def _generate_sorted_entries_stream():
    """Return all entries, sorted by time."""
    entries = sorted(list(_generate_entries_stream()),
                     _compare_entries_by_timestamp)
    for entry in entries:
        yield entry


def _generate_incomplete_entries(category=None):
    incomplete_items = {}
    for entry in _generate_entries_stream():
        entry_category = entry.get('category')
        if category is None or category == entry_category:
            if categories.get(entry_category, {}).get('track_completion'):
                if 'ref_id' in entry:
                    ref_id = entry.get('ref_id')
                    if entry.get('complete'):
                        del incomplete_items[ref_id]
                else:
                    incomplete_items[unique_id_from_entry(entry)] = entry

    return incomplete_items.itervalues()


def _do_list(category=None):
    width, _ = get_terminal_size()
    for entry in _generate_sorted_entries_stream():
        if not category or entry.get('category') == category:
            print_entry(entry, width=width)


def _do_check():
    with open(get_home_dir_path(LOGIT_FILENAME), 'r') as f:
        for line in f:
            json.loads(line)

    print "Looks good."


def _do_todo_list(opts):
    """Show a menu for completing todo items"""
    width, _ = get_terminal_size()
    menu_items = list(enumerate(
        _generate_incomplete_entries(category=opts.category),
        start=1))

    for index, entry in menu_items:
        print_entry(entry, width=width, prefix=str(index) + ') ')

    try:
        completed_index = int(raw_input("Which entry did you complete "
                                        "[Enter to quit]? "))
    except ValueError:
        print "No entries changed."
        return

    entry = dict(menu_items).get(completed_index)

    logit({
        'category': entry['category'],
        'ref_id': unique_id_from_entry(entry),
        'complete': True
    })


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    opts = parse_args(argv)

    if opts.check:
        _do_check()
    elif opts.list:
        _do_list(category=opts.category)
    elif opts.todo_list:
        _do_todo_list(opts)
    elif opts.backup:
        _do_backup(opts)
    else:
        _do_logit(opts)


if __name__ == '__main__':
    main()
