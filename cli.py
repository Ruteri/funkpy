import os
import pty
import select

try:
    from once import Once
except ImportError:
    Once = lambda fn: fn


COMMAND_OUTPUT_TIMEOUT_MS = 60000
READ_TIMEOUT_MS = 100
WRITE_TIMEOUT_MS = 1000


def _get_pty(*argv):
    try:
        (child_pid, pipe_fd) = pty.fork()
    except Exception as e:
        raise RuntimeError('could not fork: ', e)

    if child_pid == 0:
        env = dict(TERM="linux")
        try:
            os.execvpe(argv[0], argv[1:], env)
        except:
            os.exit(1)

    return pipe_fd


class Cli(object):
    """Manage shell-like processes.

    Tool that enables straightforward usage of interactive console commands.
    Made with shell scripts testing and automation in mind.

    Usage:
        cli = Cli('/bin/bash')
        print(cli.call('ls\n'))
        print(cli.call('pwd\n'))

        cli = Cli('psql db')
        cli.call('\\\d\n')
    """
    def __init__(self, *argv):
        self.fd = None
        self.read_poller = None
        self.write_poller = None

        self._fork(*argv)
        self._set_pollers()

    @Once
    def _fork(self, *argv):
        fd = _get_pty(*argv)
        if fd is None:
            raise RuntimeError('fork did not return fd')
        self.fd = fd

    @Once
    def _set_pollers(self):
        if self.fd is None:
            raise RuntimeError('fd is not yet ready')

        self.read_poller = select.poll()
        self.read_poller.register(self.fd, select.POLLIN)

        self.write_poller = select.poll()
        self.write_poller.register(self.fd, select.POLLOUT)

    def readall(self):
        total_output = []
        while self.read_poller.poll(READ_TIMEOUT_MS):
            resp = os.read(self.fd, 1024)
            total_output.append(resp)
        return total_output

    def flush(self):
        if self.read_poller.poll(0):
            _ = self.readall()

    def call(self, command):
        self.flush()
        self.write_poller.poll(WRITE_TIMEOUT_MS)
        os.write(self.fd, command.encode())
        _ = os.read(self.fd, len(command) + 1)
        self.read_poller.poll(COMMAND_OUTPUT_TIMEOUT_MS)
        return self.readall()
