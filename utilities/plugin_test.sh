#!/bin/sh

script=$1
conf=$2

if [ -z "$2" -o "$1" = "-h" -o "$1" = "--help" ]; then
    cat <<END
Usage: plugin_test.sh [checkname.py] [/path/to/conf.d/checkname.yaml]
Example: ./plugin_test.sh process.py /etc/dd-agent/conf.d/process.yaml
END
    exit 1

fi

cd /usr/share/datadog/agent

# The script we're running should live inside checks.d/
if [ ! -e "checks.d/$script" ]; then
    echo "Check '`pwd`/checks.d/$script' not found on disk"
    exit 1
fi
# Check the full path to the yaml configuration file
if [ ! -e "$conf" ]; then
    echo "Configuration file '$conf' not found on disk"
    exit 1
fi

# Extract the class name out of the check script
class=`grep ^class checks.d/$script |cut -d' ' -f2 |cut -d'(' -f1`

scriptbase=`basename $script .py`

# Look for an identifier that we can print out when iterating scross instances.
#+ Don't try too hard, it's not terribly important, just kind of nice to have.
iname=`grep name: $conf |cut -d: -f1 |uniq |head -1 |sed 's/\s//g'`
# Build a line of Python code that prints out a name for each iteration
if [ -n "$iname" ]; then
    nameline="print \"\\nRunning the check against $iname: %s\" % (instance[\"$iname\"])"
else
    nameline="print 'Iterating...'"
fi


echo "Running $class from $script using $conf, please stand by..."

cat <<EOF |PYTHONPATH=.:./checks.d python
from $scriptbase import *
if __name__ == '__main__':
    check, instances = $class.from_yaml("$conf")
    dir(instances)
    for instance in instances:
        $nameline
        check.check(instance)
        if check.has_events():
            print 'Events: %s' % (check.get_events())
        print 'Metrics: %s' % (check.get_metrics())
EOF
