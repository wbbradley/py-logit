import sys
import gc
from io import StringIO
from datetime import datetime, timedelta
import logging
import textwrap
import uuid
import argparse
import json
from os.path import dirname
from functools import cmp_to_key

from attrdict import AttrDict
import boto
from boto.s3.key import Key

from logit.crypt import encrypt_json, get_secret_key, decrypt_json
from logit.utils import (get_home_dir_path, get_terminal_size, bcolors,
                         unique_id_from_entry, make_sure_path_exists,
                         get_console_input)

LOGIT_FILENAME = 'logit.txt'


if __name__ == '__main__':
    logging.basicConfig(filename=get_home_dir_path('.logit.log'),
                        level=logging.INFO)

log = logging.getLogger('logit')


def get_categories():
    """Get categories."""
    return {
        'note': {
            'description': 'Just a note',
        },
        'todo': {
            'description': 'TODO',
            'track_completion': True,
        },
        'url': {
            'description': 'An URL',
            'fields': {
                'url': 'URL: ',
            },
        },
        'health': {
            'description': 'A health issue',
        },
        'work': {
            'description': 'You did something for work',
        },
        'home': {
            'description': 'You did something for home',
        },
        'idea': {
            'description': 'An idea',
        },
        'dream': {
            'description': 'A dream you remember',
        },
    }


def get_version():
    """Get version."""
    import pkg_resources
    return pkg_resources.require('logit')[0]


def get_arg_parser():
    """Get the argument parser"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--log',
        dest='logit_filename',
        default=get_home_dir_path(LOGIT_FILENAME),
        help='Specify the location to store the actual log file.',
    )
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
        '--show_recent_week',
        dest='show_recent_week',
        action='store_true',
        default=False,
        help='Connect to S3 and show the most recent week of log info.',
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
    parser.add_argument(
        '--json',
        dest='as_json',
        action='store_true',
        default=False,
        help='When listing, print as json.')
    parser.add_argument(
        '-M',
        dest='merge',
        action='store_true',
        default=False,
        help='Merge all S3 logs into this log.',
    )
    parser.add_argument(
        '--version',
        dest='version',
        action='store_true',
        default=False,
        help='Print the current logit version ({})'.format(get_version()),
    )
    parser.add_argument(
        '--encrypt-all',
        dest='encrypt_all',
        action='store_true',
        default=False,
        help=('Go back through prior locally stored logit entries, and '
              'encrypt them.'),
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

        make_sure_path_exists(dirname(config_filename))

        with open(config_filename, 'w') as f:
            json.dump(install_config, f, sort_keys=True, indent=4)

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


def get_s3_bucket(opts):
    """Get s3 bucket."""
    s3conn = boto.connect_s3(
        aws_access_key_id=opts.aws_access_key_id,
        aws_secret_access_key=opts.aws_secret_access_key)
    return s3conn.get_bucket(opts.s3_bucket)


def _do_encrpyt_all(opts):
    """Do encrypt all."""
    get_secret_key(opts)
    new_secret_key = get_secret_key(AttrDict(),
                                    prompt='Enter a new password: ')
    new_secret_key_2 = get_secret_key(AttrDict(),
                                      prompt='Repeat your new password: ')
    if new_secret_key != new_secret_key_2:
        print("Passwords did not match.")
        return

    out = StringIO()
    for entry in _generate_entries_from_local_file(opts):
        encrypt_json(new_secret_key, entry, out)
        out.write('\r\n')
    out.seek(0)

    with open(opts.logit_filename, 'w') as f:
        f.write(out.read())


def _do_backup(opts):
    """Perform a backup to S3."""
    if (not opts.aws_access_key_id or
            not opts.aws_secret_access_key or
            not opts.s3_bucket):
        print('You must specify AWS access credentials and an S3 bucket name '
              '(see --help)')

    else:
        bucket = get_s3_bucket(opts)
        key = Key(bucket)
        key.key = _create_backup_key_name()
        key.set_contents_from_filename(opts.logit_filename)


def logit(opts, entry, timestamp):
    try:
        entry['timestamp'] = timestamp.isoformat()
        entry['id'] = str(uuid.uuid4())
        entry['installation'] = get_install_id()

        assert 'category' in entry
        entry['message'] = entry.get('message') or get_console_input('Notes: ',
                                                                     use_vim=True)

        if entry.get('message'):
            with open(opts.logit_filename, 'a') as f:
                secret_key = get_secret_key(opts)
                encrypt_json(secret_key, entry, f)
                f.write('\r\n')
        else:
            print('No logit entry entered.')
    finally:
        gc.collect()


def parse_datetime(date_string):
    """Convert 2014-10-2 to a datetime, etc..."""
    return datetime(*[int(n) for n in date_string.split('-')])


def print_recent_week(opts, categories):
    """Show a list of all entries from the recent week."""
    width, _ = get_terminal_size()
    week_ago = (datetime.utcnow() - timedelta(weeks=1)).isoformat()
    for entry in _generate_merged_entries_from_s3(opts):
        if entry['timestamp'] > week_ago:
            if not opts.category or entry.get('category') == opts.category:
                print_entry(entry, categories, width=width)


def _do_logit(opts):
    categories = get_categories()
    category = opts.category

    while category not in categories:
        print("Existing categories:")

        for key, schema in categories.items():
            print("\t{}: {}".format(key, schema['description']))

        category = get_console_input('Category: ')
        if not category:
            return

    opts.category = category

    if opts.show_recent_week:
        print_recent_week(opts, categories)

    entry = {'category': category}
    if opts.message:
        entry['message'] = opts.message

    fields = categories[category].get('fields') or {}
    for field, description in fields.items():
        value = get_console_input(description, use_vim=True)
        if value:
            entry[field] = value

    timestamp = datetime.utcnow()
    if opts.back_date:
        timestamp = parse_datetime(opts.back_date)

    logit(opts, entry, timestamp)


def _longest_category(categories):
    return max(len(category) for category in categories)


def print_entry(entry, categories, prefix='', width=0):
    timestamp = entry.get('timestamp', '')
    if len(timestamp) == 19:
        timestamp = timestamp[:-3].replace('T', ' ')
    elif len(timestamp) == 26:
        timestamp = timestamp[:-10].replace('T', ' ')
    else:
        timestamp = None

    if not timestamp:
        timestamp = '-no timestamp-'

    category = entry.get('category', 'note')
    prefix_len = len('{prefix}{timestamp} : {category}'.format(
        prefix=prefix,
        timestamp=timestamp,
        category=category,
    ))
    pretty_prefix = ((bcolors.MENU + prefix + bcolors.ENDC + bcolors.TIMESTAMP
                      + '{timestamp}' + bcolors.ENDC + ' : ' + bcolors.CATEGORY
                      + '{category}' + bcolors.ENDC)
                     .format(timestamp=timestamp, category=category))
    message = entry.get('message')
    print(pretty_prefix)
    for paragraph in message.splitlines():
        lines = textwrap.wrap(paragraph, width,
                              initial_indent=' '*4,
                              subsequent_indent=' '*4,
                              replace_whitespace=False) or ['']
        for line in lines:
            print(line)


def _generate_entries_from_file(opts, file_, filename):
    """Generate all the entries from the local logit file"""
    for line, entry in enumerate(file_, start=1):
        if entry[0] != '{':
            try:
                yield decrypt_json(get_secret_key(opts), entry)
            except:
                log.exception('error decrypting entry %s' % entry)
        else:
            try:
                yield json.loads(entry)
            except ValueError:
                log.exception('error on line %d of %s', line, filename)


def _generate_entries_from_local_file(opts, sort=False):
    """Generate all the entries from the local logit file"""
    filename = opts.logit_filename

    with open(filename, 'r') as file_:
        if sort:
            for entry in _generate_sorted_entries_from_file(opts, file_,
                                                            filename):
                yield entry
        else:
            for entry in _generate_entries_from_file(opts, file_, filename):
                yield entry


def _generate_entries_from_key(opts, key):
    file_ = StringIO(key.get_contents_as_string())
    for entry in _generate_entries_from_file(opts, file_, key.key):
        yield entry


def _compare_entries_by_timestamp(x, y):
    if x.get('timestamp', '') < y.get('timestamp', ''):
        return -1
    else:
        return 1


def _generate_sorted_entries_from_entries(entries):
    """Return all entries, sorted by time."""
    entries = sorted(entries, key=cmp_to_key(_compare_entries_by_timestamp))
    for entry in entries:
        yield entry


def _generate_sorted_entries_from_file(opts, file_, filename):
    """Return all entries, sorted by time."""
    entries = sorted(list(_generate_entries_from_file(opts, file_, filename)),
                     key=cmp_to_key(_compare_entries_by_timestamp))
    for entry in entries:
        yield entry


def _generate_incomplete_entries(opts, categories):
    incomplete_items = {}
    for entry in _generate_entries_from_local_file(opts):
        entry_category = entry.get('category')
        if opts.category is None or opts.category == entry_category:
            if categories.get(entry_category, {}).get('track_completion'):
                if 'ref_id' in entry:
                    ref_id = entry.get('ref_id')
                    if entry.get('complete'):
                        del incomplete_items[ref_id]
                else:
                    incomplete_items[unique_id_from_entry(entry)] = entry

    return incomplete_items.itervalues()


def _do_list(opts, categories, category=None):
    width, _ = get_terminal_size()
    for entry in _generate_entries_from_local_file(opts, sort=True):
        if not category or entry.get('category') == category:
            if opts.as_json:
                print(json.dumps(entry))
            else:
                print_entry(entry, categories, width=width)


def _do_check(opts):
    with open(opts.logit_filename, 'r') as f:
        for line in f:
            json.loads(line)

    print("Looks good.")


def _do_todo_list(opts, categories):
    """Show a menu for completing todo items"""
    width, _ = get_terminal_size()
    menu_items = list(enumerate(
        _generate_incomplete_entries(opts, categories),
        start=1))

    for index, entry in menu_items:
        print_entry(entry, categories, width=width, prefix=str(index) + ') ')

    try:
        completed_index = int(get_console_input(
            "Which entry did you complete [Enter to quit]? "))
    except ValueError:
        print("No entries changed.")
        return

    entry = dict(menu_items).get(completed_index)

    logit(opts, {
        'category': entry['category'],
        'ref_id': unique_id_from_entry(entry),
        'complete': True
    })


def _get_installation_from_key_name(key_name):
    installation = key_name[27:63]
    if len(installation) == 36:
        return installation


def _get_installations_from_keys(keys):
    installations = set()

    for key in keys:
        installation = _get_installation_from_key_name(key.key)
        if installation:
            installations.add(installation)

    return installations


def _get_latest_key(keys, installation):
    """Get the latest key for an installation."""
    latest_key = None

    for key in keys:
        if installation in key.key:
            is_latest = (
                latest_key is None or
                latest_key.key < key.key
            )

            if is_latest:
                latest_key = key

    return latest_key


def _generate_merged_entries_from_s3(opts):
    """Merge all of the installations' logs into this installation."""
    bucket = get_s3_bucket(opts)
    keys = bucket.get_all_keys()

    # first find all of the installations
    installations = _get_installations_from_keys(keys)
    install_id = get_install_id()
    if install_id in installations:
        installations.remove(install_id)

    # for each installation, find the latest key
    keys_to_merge = {
        installation: _get_latest_key(keys, installation)
        for installation in installations
    }
    entries = {}
    for installation, key in keys_to_merge.items():
        for entry in _generate_entries_from_key(opts, key):
            if 'installation' not in entry:
                entry['installation'] = installation
            entry_id = unique_id_from_entry(entry)
            entries[entry_id] = entry

    # now add any local entries
    for entry in _generate_entries_from_local_file(opts):
        if 'installation' not in entry:
            entry['installation'] = install_id
        entry_id = unique_id_from_entry(entry)
        entries[entry_id] = entry

    for entry in _generate_sorted_entries_from_entries(entries.values()):
        yield entry


def _do_merge(categories, opts):
    """Show the contents when merged from all installations."""
    width, _ = get_terminal_size()
    for entry in _generate_merged_entries_from_s3(opts):
        print_entry(entry, categories, width=width)


def _main(argv):
    if argv is None:
        argv = sys.argv[1:]

    opts = parse_args(argv)
    categories = get_categories()
    if opts.check:
        _do_check(opts)
    elif opts.encrypt_all:
        _do_encrpyt_all(opts)
    elif opts.version:
        print(get_version())
    elif opts.merge:
        _do_merge(categories, opts)
    elif opts.list:
        _do_list(opts, categories, category=opts.category)
    elif opts.todo_list:
        _do_todo_list(opts, categories)
    elif opts.backup:
        _do_backup(opts)
    else:
        _do_logit(opts)


def main(argv=None):
    _main(argv)


if __name__ == '__main__':
    main()