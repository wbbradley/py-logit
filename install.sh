#!/bin/sh
set -e

# Make sure needed tools are available
git --version > /dev/null
python --version > /dev/null

if [ ! -f install.sh ]; then
	echo "Please run install.sh from the directory you cloned 'logit' into..."
	exit 1
fi

export VIRTUAL_ENV=
rm -rf env
python -mvenv env
source env/bin/activate
pip install -r requirements.txt

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Write the run script
cat > /usr/local/bin/logit << EOF
#!/bin/bash

cd $DIR
source $DIR/env/bin/activate
python -m logit.main \$@
EOF

# Make the run script executable
chmod +x /usr/local/bin/logit

echo "logit was installed to /usr/local/bin."
