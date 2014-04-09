# Python Dogstatsd Generator

This test tool will create dogstatsd metrics and send them to the monitoring agent.
To use it, you will need to install the following python libraries:
```
sudo apt-get install python-setuptools
sudo easy_install dogstatsd-python
```

## Usage
### To run the generator:
```
1) edit the config file (generator.conf) and set the target host, port, number of
iterations and delay (in seconds) between iterations.
2) cd to the statsd-gen directory
3) Type ./generator.py
4) The tool will send 4 different types of dogstatsd messages and then sleep for
the duration of the delay and then will continue to the next iteration until the
number of iterations is reached.
```