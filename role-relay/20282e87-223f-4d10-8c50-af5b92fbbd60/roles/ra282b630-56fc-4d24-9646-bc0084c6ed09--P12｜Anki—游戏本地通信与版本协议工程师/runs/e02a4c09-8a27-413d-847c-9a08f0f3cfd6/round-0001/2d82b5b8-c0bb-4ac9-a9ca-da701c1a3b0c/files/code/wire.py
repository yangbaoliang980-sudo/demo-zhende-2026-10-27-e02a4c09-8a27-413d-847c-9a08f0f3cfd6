"""One authenticated request per loopback TCP connection; no HTTP or remote fallback.

Frame = uint32 big-endian byte length || UTF-8 JSON || 32-byte HMAC-SHA256.
A fresh 32-byte server challenge binds direction and exact request bytes. The
shared secret is never transmitted. HMAC authenticates, it does not encrypt.
"""
from __future__ import annotations
import hashlib
import hmac
import secrets
import socket
import struct
import time
from dataclasses import dataclass
from .protocol import MAX_FRAME_BYTES, byte_hash, decode_request, decode_response

MAGIC = b'YLAT01'
TIMEOUT_SECONDS = 2.0

class WireError(OSError):
    pass

@dataclass(frozen=True)
class LoopbackAddress:
    port: int = 0
    host: str = '127.0.0.1'

    def __post_init__(self):
        if self.host != '127.0.0.1' or type(self.port) is not int or not 0 <= self.port <= 65535:
            raise ValueError('ONLY_LITERAL_IPV4_LOOPBACK_ALLOWED')

    @property
    def tuple(self):
        return (self.host, self.port)


def read_exact(sock, count, deadline):
    result = bytearray()
    while len(result) < count:
        left = deadline - time.monotonic()
        if left <= 0:
            raise WireError('E_WIRE_DEADLINE')
        sock.settimeout(left)
        chunk = sock.recv(count - len(result))
        if not chunk:
            raise WireError('E_WIRE_TRUNCATED')
        result.extend(chunk)
    return bytes(result)


def mac(secret, context, raw):
    return hmac.new(secret, context + struct.pack('!I', len(raw)) + raw, hashlib.sha256).digest()


def send_frame(sock, secret, context, raw, deadline):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_FRAME_BYTES:
        raise WireError('E_FRAME_LIMIT')
    left = deadline - time.monotonic()
    if left <= 0:
        raise WireError('E_WIRE_DEADLINE')
    sock.settimeout(left)
    sock.sendall(struct.pack('!I', len(raw)) + raw + mac(secret, context, raw))


def recv_frame(sock, secret, context, deadline):
    n = struct.unpack('!I', read_exact(sock, 4, deadline))[0]
    if not 0 < n <= MAX_FRAME_BYTES:
        raise WireError('E_FRAME_LIMIT')
    raw = read_exact(sock, n, deadline)
    signature = read_exact(sock, 32, deadline)
    if not hmac.compare_digest(signature, mac(secret, context, raw)):
        raise WireError('E_AUTHENTICATION')
    return raw


class LoopbackServer:
    def __init__(self, ingress, address=None, *, timeout=TIMEOUT_SECONDS, before_send=None):
        if not 0 < timeout <= 5:
            raise ValueError('BOUNDED_TIMEOUT_REQUIRED')
        address = address or LoopbackAddress()
        self.ingress, self.timeout, self.before_send = ingress, timeout, before_send
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Do not allow SO_REUSEPORT or wildcard binding.
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            self.listener.bind(address.tuple)
            self.listener.listen(8)
            self.listener.settimeout(0.2)
            host, port = self.listener.getsockname()
            self.address = LoopbackAddress(port, host)
        except BaseException:
            self.listener.close()
            raise
        self.closed = False
        self.counters = {'accepted':0, 'completed':0, 'closed_without_ack':0}

    def serve_one(self):
        try:
            connection, peer = self.listener.accept()
        except socket.timeout:
            return False
        except OSError:
            if self.closed:
                return False
            raise
        self.counters['accepted'] += 1
        with connection:
            try:
                if peer[0] != '127.0.0.1':
                    raise WireError('E_NONLOCAL_PEER')
                deadline = time.monotonic() + self.timeout
                nonce = secrets.token_bytes(32)
                connection.settimeout(self.timeout)
                connection.sendall(MAGIC + nonce)
                raw = recv_frame(connection, self.ingress.pairing.secret,
                                 MAGIC + b':request:' + nonce, deadline)
                response = self.ingress.handle(raw)
                if self.before_send is not None:
                    self.before_send(raw, response)
                send_frame(connection, self.ingress.pairing.secret,
                           MAGIC + b':response:' + nonce + hashlib.sha256(raw).digest(),
                           response, deadline)
                self.counters['completed'] += 1
            except (OSError, ValueError):
                # Authentication/frame failures never enter the ledger or emit ACKs.
                self.counters['closed_without_ack'] += 1
        return True

    def serve(self, stop_event):
        while not self.closed and not stop_event.is_set():
            self.serve_one()

    def close(self):
        self.closed = True
        self.listener.close()


class LoopbackClient:
    def __init__(self, address, pairing, *, timeout=TIMEOUT_SECONDS):
        if address.port == 0 or not 0 < timeout <= 5:
            raise ValueError('EXPLICIT_ENDPOINT_AND_BOUNDED_TIMEOUT_REQUIRED')
        self.address, self.pairing, self.timeout = address, pairing, timeout

    def exchange_raw(self, raw):
        # Deliberately separate for malformed-packet contract tests.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            deadline = time.monotonic() + self.timeout
            sock.settimeout(self.timeout)
            sock.connect(self.address.tuple)
            challenge = read_exact(sock, len(MAGIC) + 32, deadline)
            if not challenge.startswith(MAGIC):
                raise WireError('E_HANDSHAKE')
            nonce = challenge[len(MAGIC):]
            send_frame(sock, self.pairing.secret, MAGIC + b':request:' + nonce, raw, deadline)
            return recv_frame(sock, self.pairing.secret,
                              MAGIC + b':response:' + nonce + hashlib.sha256(raw).digest(), deadline)

    def exchange(self, raw):
        from .outbox import check_reply
        decode_request(raw)
        return check_reply(raw, decode_response(self.exchange_raw(raw)), self.pairing)
