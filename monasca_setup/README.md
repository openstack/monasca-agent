# monasca-setup

This script will detect running services and configure monasca-agent to watch them as well as starting the agent and
configuring it to start up on boot.


## Future Considerations
- A good system for specifying active style checks for configuration would be great. Active style checks are those
  which run locally but are checking a remote box.
- The ability to dynamically add detection plugins could be quite valuable. Also it could aid in the active check config.
    - With the ability to dynamically add I should also include the ability to dynamically remove.
- A config file with metadata to assist in automatic configuration could be quite valuable, for example user/pass for
  logging into mysql.
- The current system does not work well in the case of clusters, for example the kafka plugin will end up collecting
  the same data on each node of a cluster.