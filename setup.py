from distutils.core import setup
setup(name='logit',
      version='0.1',
      description='A log for humans',
      author='William Bradley',
      author_email='williambbradley@gmail.com',
      py_modules=['logit', 'utils'],
      install_requires=['boto', 'PyYAML'],
      )
