# logit - a log for humans

A tool for logging stuff that you care about.

```
mkdir -p ~/src
cd ~/src
git clone git@github.com:wbbradley/logit.git
cd logit
virtualenv env
. env/bin/activate
pip install -r requirements.txt
```

Add this to your .bashrc:
```
function logit() {
	(. ~/src/logit/env/bin/activate && python ~/src/logit/logit.py $@)
}
```

And, if you'd like to use the backup functionality, make sure you've got an S3 bucket called `logit-logs`. (TODO: make this a command-line parameter)

```
function logit-backup () {
	logit --backup --aws-access-key-id=AKIAYOURACCESSKEY --aws-secret-access-key=alsfkjasdlfjasldkfjasdklfjasldkfjasdlk
}
```
