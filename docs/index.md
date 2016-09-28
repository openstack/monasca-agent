# Monasca Agent Documentation

Please refer to the [project readme](https://github.com/openstack/monasca-agent) for Agent documentation.

For full Monasca documentation visit [wiki.openstack.org/wiki/Monasca](https://wiki.openstack.org/wiki/Monasca)

# Working with document updates

    ##### Install mkdocs
    $ sudo pip install mkdocs

    ##### Install Nodejs Package Manager NPM
    https://nodejs.org/download/

    ##### Install doctoc
    $ npm install -g doctoc

    ##### Create a mkdocs project structure
    $ cd source/openstack/monasca/monasca-agent
    $ mkdocs new .

    ##### Edit the mkdocs yaml
    site_name: monasca-agent
    repo_url: https://github.com/openstack/monasca-agent

    ##### Move the existing README.md
    $ mv README.md docs

    ##### Copy/create custom docs to the new docs structure
    $ cp README_CUSTOMIZE.md source/openstack/monasca/monasca-agent/docs

    ##### Update the document table of contents on all docs
    $ cd source/openstack/monasca/monasca-agent
    $ find docs/ -name \*.md -exec doctoc {} \;

    ##### View the results
    $ cd source/openstack/monasca/monasca-agent
    $ mkdocs serve
    http://127.0.0.1:8000/

