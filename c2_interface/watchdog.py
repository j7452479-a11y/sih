"""
c2_interface/watchdog.py - Real-Time Hardware Safe-Stop Watchdog Monitor
Enforces tight coupling between Simulation Master Clock and Physical / Return Telemetry Actuators.
If the simulation heartbeat stops for > 250ms (pause, crash, or freeze),
instantly halts physical hardware and overrides return telemetry.
"""

import asyncio
import json
import os
import socket
import sys
import time
from typing import Callable, List, Optional

from config import (
    DEFAULT_RETURN_IP,
    HARDWARE_SERIAL_PORT,
    HEARTBEAT_UDP_PORT,
    TELEMETRY_RETURN_PORT,
    CIVILIAN_TELEMETRY_PORT,
    WATCHDOG_TIMEOUT_SEC,
)


class WatchdogMonitor:
    def __init__(
        self,
        port: int = HEARTBEAT_UDP_PORT,
        timeout_sec: float = WATCHDOG_TIMEOUT_SEC,
        telemetry_return_port: int = TELEMETRY_RETURN_PORT,
        target_ip: str = DEFAULT_RETURN_IP,
        serial_port: Optional[str] = HARDWARE_SERIAL_PORT,
    ):
        self.port = port
        self.timeout_sec = timeout_sec
        self.telemetry_return_port = telemetry_return_port
        self.target_ip = target_ip
        self.serial_port_name = serial_port or os.environ.get("HARDWARE_SERIAL_PORT")
        
        self.last_heartbeat = time.time()
        self.last_unity_heartbeat = 0.0
        self.unity_active = False
        self.last_sim_time = 0.0
        self.is_paused = False
        self.heartbeat_count = 0
        self.halt_count = 0
        
        self._halt_callbacks: List[Callable[[], None]] = []
        self._resume_callbacks: List[Callable[[], None]] = []

        # Setup non-blocking UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception:
            pass
        self.sock.bind(("0.0.0.0", self.port))
        self.sock.setblocking(False)

        # Return socket for immediate hardware emergency halt packet broadcast
        self.halt_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def register_halt_callback(self, cb: Callable[[], None]):
        self._halt_callbacks.append(cb)

    def register_resume_callback(self, cb: Callable[[], None]):
        self._resume_callbacks.append(cb)

    def feed_heartbeat(self, source: str = "unity", sim_time: float = 0.0):
        """Directly feeds a heartbeat from live sensor sweeps (port 5001/5002) or UDP 5005."""
        now = time.time()
        source = str(source).lower()
        if source == "unity":
            self.last_unity_heartbeat = now
            self.unity_active = True

        self.last_heartbeat = now
        if sim_time > 0:
            self.last_sim_time = float(sim_time)
        self.heartbeat_count += 1
        if self.is_paused:
            print(f"[WATCHDOG] Simulation Resumed ({source.upper()}). Hardware Live.")
            sys.stdout.flush()
            self.is_paused = False
            self.trigger_hardware_resume()

    async def monitor_loop(self):
        print(f"[*] Watchdog Monitor active on UDP Port {self.port} (Timeout: {self.timeout_sec * 1000:.0f}ms)")
        sys.stdout.flush()

        while True:
            # 1. Drain incoming heartbeat datagrams
            while True:
                try:
                    data, _ = self.sock.recvfrom(1024)
                    payload = json.loads(data.decode("utf-8"))
                    if "sim_time" in payload:
                        source = str(payload.get("source", "unity")).lower()
                        self.feed_heartbeat(source=source, sim_time=float(payload.get("sim_time", 0.0)))
                except (BlockingIOError, socket.error):
                    break
                except Exception:
                    break

            # 2. Evaluate timeout limit
            now = time.time()
            if self.unity_active:
                time_since_clock = now - self.last_unity_heartbeat
            else:
                time_since_clock = now - self.last_heartbeat

            if time_since_clock > self.timeout_sec and not self.is_paused:
                clock_name = "Unity" if self.unity_active else "Master Clock"
                print(f"[WATCHDOG] CRITICAL: {clock_name} Simulation Paused (>{self.timeout_sec*1000:.0f}ms). Halting Hardware.")
                sys.stdout.flush()
                self.is_paused = True
                self.halt_count += 1
                self.trigger_hardware_halt()

            # If paused, periodically re-broadcast halt packet to ensure failsafe state
            if self.is_paused and (self.halt_count > 0):
                self._dispatch_halt_packet()

            await asyncio.sleep(0.05)  # 20 Hz evaluation loop

    def trigger_hardware_halt(self):
        """Dispatches safe-stop commands to both physical hardware interfaces and network actuators."""
        # 1. Immediate UDP failsafe datagram to Port 5003 (Vehicle Actuators & HUDs)
        self._dispatch_halt_packet()

        # 2. Optional physical serial port command (e.g. Arduino / CAN / ESC motor controller)
        if self.serial_port_name:
            try:
                import serial
                with serial.Serial(self.serial_port_name, 115200, timeout=0.1) as ser_dev:
                    ser_dev.write(b"STOP_MOTORS\n")
                    ser_dev.flush()
            except Exception as ex:
                print(f"[WATCHDOG] Serial halt note: {ex}")
                sys.stdout.flush()

        # 3. Trigger registered engine callbacks
        for cb in self._halt_callbacks:
            try:
                cb()
            except Exception:
                pass

    def trigger_hardware_resume(self):
        """Restores physical hardware and network actuators when simulation unpauses."""
        if self.serial_port_name:
            try:
                import serial
                with serial.Serial(self.serial_port_name, 115200, timeout=0.1) as ser_dev:
                    ser_dev.write(b"RESUME_MOTORS\n")
                    ser_dev.flush()
            except Exception:
                pass

        for cb in self._resume_callbacks:
            try:
                cb()
            except Exception:
                pass

    def _dispatch_halt_packet(self):
        """Sends emergency zero-velocity safe-stop datagram to Port 5003 and 5004."""
        try:
            halt_msg = json.dumps({
                "timestamp": time.time(),
                "status": "SIMULATION_PAUSED_HARDWARE_HALT",
                "simulation_paused": True,
                "emergency_stop": True,
                "target_speed": 0.0,
                "aeb": True,
                "targets": []
            }).encode("utf-8")
            self.halt_socket.sendto(halt_msg, (self.target_ip, self.telemetry_return_port))
            if CIVILIAN_TELEMETRY_PORT != self.telemetry_return_port:
                self.halt_socket.sendto(halt_msg, (self.target_ip, CIVILIAN_TELEMETRY_PORT))
        except Exception:
            pass

    def get_state(self) -> dict:
        now = time.time()
        time_since = (now - self.last_unity_heartbeat) if self.unity_active else (now - self.last_heartbeat)
        return {
            "is_paused": self.is_paused,
            "unity_active": self.unity_active,
            "master_clock": "unity" if self.unity_active else "generic",
            "last_heartbeat_timestamp": round(self.last_unity_heartbeat if self.unity_active else self.last_heartbeat, 3),
            "last_sim_time": round(self.last_sim_time, 3),
            "time_since_last_sec": round(time_since, 3),
            "timeout_threshold_sec": self.timeout_sec,
            "heartbeat_count": self.heartbeat_count,
            "halt_count": self.halt_count,
        }

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
        try:
            self.halt_socket.close()
        except Exception:
            pass
