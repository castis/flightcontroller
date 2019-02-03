#!/usr/bin/env python
# kill $(ps aux | grep tower.p[y] | awk '{print $2}')

import sys
import os
import socket
import logging
import psutil

from argparse import ArgumentParser
from paramiko import ECDSAKey, SFTPClient, SSHClient
from paramiko.ssh_exception import SSHException, AuthenticationException
from time import sleep, strftime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


parser = ArgumentParser(description="Tower, ground control utility")

parser.add_argument(
    "host", nargs="?", default="currant", help="Hostname of the vehicle"
)
parser.add_argument("-u", "--user", default="root", help="Valid SSH user name")
parser.add_argument(
    "-i",
    "--identity",
    default="~/.ssh/currant_ecdsa",
    help="Path to an SSH key file",
)
parser.add_argument(
    "-l",
    "--local-dir",
    default="./currant",
    help="Local directory to watch and sync from",
)
parser.add_argument(
    "-r",
    "--remote-dir",
    default="/opt/currant",
    help="Remote directory to sync to",
)
parser.add_argument(
    "-c",
    "--configure",
    action="store_true",
    help="Run ansible setup and exit",
)

args = parser.parse_args()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger()


if args.configure:
    # run ansible playbooks
    logger.info("here is where we run ansible playbooks")
    exit(0)


try:
    key_file = os.path.expanduser(args.identity)
    ssh_kwargs = {
        "username": args.user,
        "pkey": ECDSAKey.from_private_key_file(key_file),
    }
except FileNotFoundError as e:
    logger.error(f"{args.identity} not found")
    exit(1)


try:
    ssh = SSHClient()
    ssh.load_system_host_keys()
    ssh.connect(args.host, **ssh_kwargs)
except AuthenticationException as e:
    logger.error("Authentication error")
    raise
except socket.timeout:
    logger.error("Connection timeout, is the Pi awake?")
    raise
except socket.error:
    logger.error("Socket error")
    raise


class SFTPClient(SFTPClient):
    # modified to recursively sync a directory tree
    def put_dir(self, source, target):
        for item in os.listdir(source):
            source_path = os.path.join(source, item)
            target_path = f"{target}/{item}"
            if os.path.isfile(source_path):
                self.put(source_path, target_path)
            else:
                self.mkdir(target_path, ignore_existing=True)
                self.put_dir(source_path, target_path)

    def mkdir(self, path, mode=511, ignore_existing=False):
        try:
            super(SFTPClient, self).mkdir(path, mode)
        except IOError:
            if not ignore_existing:
                raise


sftp = SFTPClient.from_transport(ssh.get_transport())


class FSEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        # when this file is modified, restart this process
        if os.path.basename(event.src_path) == os.path.basename(__file__):
            logger.info("Restarting")
            try:
                p = psutil.Process(os.getpid())
                for handler in p.open_files() + p.connections():
                    os.close(handler.fd)
            except Exception as e:
                logging.error(e)

            os.execl(sys.executable, sys.executable, *sys.argv)

        elif event.src_path.startswith(args.local_dir):
            sync_code_folder()


def sync_code_folder():
    logger.info("Syncing")
    try:
        sftp.put_dir(args.local_dir, args.remote_dir)
        ssh.exec_command(f'find {args.remote_dir} -type f -iname "*.pyc" -delete')
        # ssh.exec_command("kill -SIGUSR1 $(ps aux | grep fly.p[y] | awk '{print $2}')")
        # ssh.exec_command("systemctl restart currant.service")
    except Exception as e:
        logger.error(e)


observer = Observer()
observer.schedule(FSEventHandler(), ".", recursive=True)

try:
    logger.info("Watching for changes")
    observer.start()

    date = strftime("%m%d%H%M%Y.%S")
    logger.info(f"Set vehicle clock to {date}")
    ssh.exec_command(f"date {date}")

    sync_code_folder()

    # if args.getlogs:
    #     logger.info('Fetching debug logs')
    #     os.system(f'rsync -a {args.host}:{args.remote_dir}/logs ./')
    #     ssh.exec_command(f'find {args.remote_dir}/logs -type f -delete')

    while True:
        sleep(1)

except KeyboardInterrupt:
    logger.info("Caught ^C, quitting")

except Exception as e:
    logger.error(e)

finally:
    observer.stop()
    sftp.close()
    ssh.close()

logger.info("Aviation!")
