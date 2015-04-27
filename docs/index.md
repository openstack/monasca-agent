<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Monasca Agent Documentation](#monasca-agent-documentation)
- [Working with document updates](#working-with-document-updates)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Monasca Agent Documentation

For full documentation visit [wiki.openstack.org/wiki/Monasca](https://wiki.openstack.org/wiki/Monasca)

For project launchpad visit [launchpad.net/monasca](https://launchpad.net/monasca)

Github [github.com/stackforge/monasca-agent/blob/master/docs/](https://github.com/stackforge/monasca-agent/blob/master/docs/)

ReadTheDocs [monasca-agent.readthedocs.org/en/latest/](http://monasca-agent.readthedocs.org/en/latest/)


# Working with document updates

    ##### Install mkdocs
    sudo pip install mkdocs

    ##### Install Nodejs Package Manager NPM
    https://nodejs.org/download/

    ##### Install doctoc
    npm install -g doctoc

    ##### Create a mkdocs project structure
    cd source/openstack/monasca/monasca-agent
    mkdocs new .

    ##### Edit the mkdocs yaml
    site_name: monasca-agent
    repo_url: https://github.com/stackforge/monasca-agent

    ##### Move the existing README.md
    mv README.md docs

    ##### Copy/create custom docs to the new docs structure
    cp README_CUSTOMIZE.md source/openstack/monasca/monasca-agent/docs

    ##### Update the document table of contents on all docs
    cd source/openstack/monasca/monasca-agent
    find docs/ -name \*.md -exec doctoc {} \;

    ##### View the results
    cd source/openstack/monasca/monasca-agent
    mkdocs serve
    http://127.0.0.1:8000/

