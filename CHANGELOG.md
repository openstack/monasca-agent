Changes
=======

# 1.0.0 / 04-28-2014

## Changes
- Fork from datadog agent 4.2.0
- removed most datadog branding
- removed embeded code
- Cleaned up name of collector/forwarder
- remove pup
- some pep8 changes, lots to go
- removed custom emitters
- removed data dog emitter, insert initial mon emitter
- collector only sends to forwarder now (previously you could optionally have it bypass the forwarder and send to datadogs)
- moved non-code files to root of project
- removed rpm build
