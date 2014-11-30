import mock

from logit.logit import get_arg_parser, main


def test_get_arg_parser():
    get_arg_parser()


@mock.patch('logit.logit.parse_args', autospec=True)
def test_main(_):
    main()
