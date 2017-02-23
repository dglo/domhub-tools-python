# Fabric script for hubmoni installation.  Use
#   fab pack deploy
#
import time
from fabric.api import *
import os.path
import hubmonitools

HUBMONICMD = "~/.local/bin/hubmoni.py"

# Remote hosts list: all of the hubs
hubconf = hubmonitools.HubConfig(hubConfigFile="resources/hubConfig.json")
(host, cluster) = hubmonitools.getHostCluster()
hubhosts = hubconf.hubs(cluster)

def installCronjob(label, job):
    bashstr = '(crontab -l 2>/dev/null | grep -x \"# %s" > /dev/null 2>/dev/null)' % label
    bashstr += ' || (crontab -l 2>/dev/null | { cat; echo; echo \"# %s\";' % label
    bashstr += 'echo \"%s\"; echo; } | crontab -)' % job
    run(bashstr)

def pack():
    # create a new source distribution as tarball
    local('python setup.py sdist --formats=gztar', capture=False)
    
@hosts(hubhosts)
@parallel
def deploy():
    # Stop any existing process
    stop()

    # figure out the release name and version
    dist = local('python setup.py --fullname', capture=True).strip()
    # upload the source tarball to the temporary folder on the server
    put('dist/%s.tar.gz' % dist, '/tmp/%s.tar.gz' % dist)
    # create a place where we can unzip the tarball, then enter
    # that directory and unzip it
    run('[[ -d /tmp/%s ]] || mkdir /tmp/%s' % (dist, dist))
    with cd('/tmp/%s' % dist):
        run('tar xzf /tmp/%s.tar.gz' % dist)
        # now install the package
        run('cd %s; /usr/bin/env python setup.py install --user' % dist)
        # now that all is set up, delete the folder again
        run('rm -rf /tmp/%s /tmp/%s.tar.gz' % (dist, dist))

    # Install the configuration files
    put('resources/hubConfig.json', 'hubConfig.json')

    # Install the cron job
    installCronjob("hubmoni cron", "*/10 * * * * %s" % HUBMONICMD)

@hosts(hubhosts)
def stop():
    run('ps aux | grep %s | grep -v grep | awk \'{print $2}\' | xargs -r kill -TERM' 
        % os.path.basename(HUBMONICMD))

# This doesn't work (see http://www.fabfile.org/faq.html#why-can-t-i-run-programs-in-the-background-with-it-makes-fabric-hang)
#def start():
#    run('nohup %s &' % HUBMONICMD)

@hosts(hubhosts)
def restart():
    stop()
    # Cron will restart for us!
    #time.sleep(1)
    #start()

# the user to use for the remote commands
env.user = 'testdaq'
