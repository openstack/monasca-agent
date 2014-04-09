#!/usr/bin/python
import json
import ConfigParser
import random
import time
from statsd import statsd
 
'''
Created on Apr 8, 2014

@author: Gary Hessler
'''

class DSDGenerator(object):
    '''
    Class to generate Dogstatsd metrics
    '''

    def __init__(self, config):
        '''
        Constructor
        '''
        print config
        self.num_of_iterations = int(config["iterations"])
        self.delay = int(config["delay"])
        self.host = config["host"]
        self.port = config["port"]

    def send_messages(self):
        '''
        Main processing for sending messages
        '''
        try:
            statsd.connect(self.host, self.port)
            for index in range(1, self.num_of_iterations + 1):
                print("Starting iteration " + str(index) + " of " + str(self.num_of_iterations))
                statsd.increment('Teraflops', 5)
                statsd.gauge('NumOfTeraflops', random.uniform(1.0, 10.0), tags=['Origin:Dev', 'Environment:Test'])
                statsd.histogram('file.upload.size', random.randrange(1, 100), tags=['Version:1.0'])
                statsd.event("SO MUCH SNOW", "Started yesterday and it won't stop !!", alert_type = "error", tags = ["priority:urgent", "result:endoftheworld"])
                print("Completed iteration " + str(index) + ".  Sleeping for " + str(self.delay) + " seconds...")
                time.sleep(self.delay)
        except:
            print "Error sending statsd messages..."
            raise;
        

def read_config():
    '''
    Read in the config file.
    '''
    config = ConfigParser.ConfigParser()
    config.read("generator.conf")
    config_options = {}
    section = "main"
    options = config.options(section)
    for option in options:
        try:
            config_options[option] = config.get(section, option)
            if config_options[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            config_options[option] = None
    return config_options

def main():
    config = read_config()
    generator = DSDGenerator(config)
    generator.send_messages()

if __name__ == "__main__":
    main()
