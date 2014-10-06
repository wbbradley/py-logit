# logit - a log for humans

A tool for logging stuff that you care about.

```
mkdir -p ~/src
cd ~/src
git clone https://github.com/wbbradley/logit.git
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

And, if you'd like to use the backup functionality, make sure you've got an S3
bucket specified.

```
function logit-backup () {
	logit --backup --s3-bucket my-bucket-of-logit-logs --aws-access-key-id=AKIAYOURACCESSKEY --aws-secret-access-key=alsfkjasdlfjasldkfjasdklfjasldkfjasdlk
}
```
