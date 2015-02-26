Tests for the mon agent.

Run with `nosestests -w tests`

For many tests to work an agent.yaml must be in either /etc/monasca/agent/agent.yaml or in the working directory.

Many tests require specific applications enabled in order for the test to run, these are skipped by default. See
https://nose.readthedocs.org/en/latest/plugins/skip.html for details.
