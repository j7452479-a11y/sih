"""
tests/test_watchdog.py - Verification of Real-Time Simulation Master Clock & Watchdog Failsafe
"""

import asyncio
import json
import socket
import time
import pytest

from c2_interface.watchdog import WatchdogMonitor


@pytest.mark.anyio
async def test_watchdog_heartbeat_and_timeout():
    # Use dedicated test port to avoid collision
    test_port = 5099
    timeout_sec = 0.20
    watchdog = WatchdogMonitor(port=test_port, timeout_sec=timeout_sec, telemetry_return_port=5098)

    monitor_task = asyncio.create_task(watchdog.monitor_loop())

    tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Give monitor loop time to start
        await asyncio.sleep(0.05)

        # 1. Initially times out because no heartbeat received yet
        await asyncio.sleep(timeout_sec + 0.05)
        assert watchdog.is_paused is True
        assert watchdog.halt_count >= 1

        # 2. Transmit valid simulation heartbeats
        for i in range(5):
            payload = json.dumps({"sim_time": 10.0 + i * 0.1}).encode("utf-8")
            tx_sock.sendto(payload, ("127.0.0.1", test_port))
            await asyncio.sleep(0.05)

        # Monitor should have resumed
        await asyncio.sleep(0.05)
        assert watchdog.is_paused is False
        assert watchdog.heartbeat_count >= 5

        # 3. Simulate pausing the simulation: stop sending heartbeats for > 200ms
        await asyncio.sleep(timeout_sec + 0.10)
        assert watchdog.is_paused is True
        assert watchdog.halt_count >= 2

    finally:
        monitor_task.cancel()
        watchdog.close()
        tx_sock.close()
