"""
Asynchronous Non-Blocking UDP Receiver
Listens for SIH1 binary LiDAR datagrams over local network / localhost.
"""

import asyncio
from typing import Callable, Optional, Tuple
import numpy as np

from config import BIND_IP
from .udp_protocol import SIHHeader, unpack_sih1_packet

class _UdpProtocolHandler(asyncio.DatagramProtocol):
    def __init__(self, on_packet_callback: Callable[[SIHHeader, np.ndarray], None]):
        self.callback = on_packet_callback
        self.transport: Optional[asyncio.DatagramTransport] = None

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        try:
            header, points = unpack_sih1_packet(data)
            self.callback(header, points)
        except Exception:
            # Ignore malformed packets silently to maintain 20 Hz loop
            pass

    def error_received(self, exc: Exception):
        pass

class AsyncUdpReceiver:
    """Async UDP socket server managing non-blocking packet ingestion."""

    def __init__(
        self,
        port: int,
        on_packet: Callable[[SIHHeader, np.ndarray], None],
        host: str = BIND_IP,
    ):
        self.port = port
        self.host = host
        self.on_packet = on_packet
        self.transport: Optional[asyncio.DatagramTransport] = None

    async def start(self):
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _UdpProtocolHandler(self.on_packet),
            local_addr=(self.host, self.port),
        )
        self.transport = transport

    def stop(self):
        if self.transport:
            self.transport.close()
            self.transport = None
