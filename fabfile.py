# Fabric script for hubmoni installation.  
# See the INSTALL file for usage.
#
import sys
import time
from fabric.api import *
import os.path
import hubmonitools

HUBMONICMD = "hubmoni"
CRONCMD = "source /usr/local/pdaq/env/bin/activate && "+HUBMONICMD

INSTALL_USER = "pdaq"
CRON_USER = "testdaq"

# Remote hosts list: all of the hubs on this cluster
hubconf = hubmonitools.HubConfig(hubConfigFile="resources/hubConfig.json")
(host, cluster) = hubmonitools.getHostCluster()
hubhosts = hubconf.hubs(cluster)

# If we didn't get a hub list on the command line, use everything on 
# this cluster
if (len(env.hosts) == 0):
    env.hosts = hubhosts

def installCronjob(label, job):
    bashstr = '(crontab -l 2>/dev/null | grep -x \"# %s" > /dev/null 2>/dev/null)' % label
    bashstr += ' || (crontab -l 2>/dev/null | { cat; echo \"# %s\";' % label
    bashstr += 'echo \"%s\"; } | crontab -)' % job
    run(bashstr)

def removeCronjob(label):
    bashstr = 'crontab -l 2>/dev/null | sed \'/# %s/,+1d\' | crontab -' % label
    run(bashstr)

@runs_once
def pack():
    # create a new source distribution as tarball
    local('python setup.py sdist --formats=gztar', capture=False)
    
@hosts(env.hosts)
@parallel
def deploy():
    # Stop any existing process
    stop()

    with settings(user=INSTALL_USER):
        # figure out the release name and version
        dist = local('python setup.py --fullname', capture=True).strip()
        # upload the source tarball to the temporary folder on the server
        put('dist/%s.tar.gz' % dist, '/tmp/%s.tar.gz' % dist)
        # now install the package with pip
        run('pip install --upgrade /tmp/%s.tar.gz' % dist)
        # delete the tarball
        run('rm -f /tmp/%s.tar.gz' % dist)

    # Install the configuration files
    config()
    # Remove any old cron jobs
    removeCronjob("hubmoni cron")
    removeCronjob("hubmoni-reboot cron")
    # Install the cron jobs
    installCronjob("hubmoni cron", "*/10 * * * * %s" % CRONCMD)
    installCronjob("hubmoni-reboot cron", "@reboot %s" % CRONCMD)

@hosts(env.hosts)
def config():
    # Install the configuration files
    put('resources/hubConfig.json', 'hubConfig.json')
    if os.path.isfile('resources/hubmoni.%s.config' % cluster):
        put('resources/hubmoni.%s.config' % cluster, 'hubmoni.config')
    else:
        put('resources/hubmoni.config', 'hubmoni.config')
    
@hosts(env.hosts)
def stop():
    run('ps aux | grep %s | grep -v grep | awk \'{print $2}\' | xargs -r kill -TERM' 
        % os.path.basename(HUBMONICMD))

# This doesn't work
# (see http://www.fabfile.org/faq.html#why-can-t-i-run-programs-in-the-background-with-it-makes-fabric-hang)
#def start():
#    run('nohup %s &' % HUBMONICMD)

@hosts(env.hosts)
def restart():
    stop()
    # Cron will restart for us!
    #time.sleep(1)
    #start()

# the user to use for the remote commands
env.user = CRON_USER
