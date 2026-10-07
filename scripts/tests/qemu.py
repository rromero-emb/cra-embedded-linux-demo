"""Utilidades comunes para arrancar la imagen en QEMU desde las pruebas."""
import os, socket, subprocess, sys, time

RUN_QEMU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "run-qemu.sh")
BOOT_OK = "CRA-DEMO: BOOT OK"
BOOT_FAIL = ("Kernel panic", "Bad Linux ARM64 Image", "Wrong Image", "Bad Data Hash",
             "Verification failed", "ERROR: can't get kernel image")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Qemu:
    def __init__(self, images, ssh_port=None, echo=True):
        self.images, self.echo = images, echo
        self.ssh_port = ssh_port or free_port()
        self.log, self.proc = "", None

    def __enter__(self):
        env = dict(os.environ, SSH_PORT=str(self.ssh_port))
        self.proc = subprocess.Popen([RUN_QEMU, self.images], env=env, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        os.set_blocking(self.proc.stdout.fileno(), False)
        return self

    def __exit__(self, *exc):
        self.proc.kill()
        self.proc.wait()

    def wait_for(self, ok=BOOT_OK, fail=BOOT_FAIL, timeout=240):
        """Devuelve True si aparece `ok`, False si aparece un fallo o QEMU termina, None si timeout."""
        start = time.time()
        while time.time() - start < timeout:
            chunk = self.proc.stdout.read() or b""
            if chunk:
                text = chunk.decode(errors="replace")
                self.log += text
                if self.echo:
                    sys.stdout.write(text)
                    sys.stdout.flush()
                if ok in self.log:
                    return True
                if any(f in self.log for f in fail):
                    return False
            elif self.proc.poll() is not None:
                return False
            else:
                time.sleep(0.2)
        return None
