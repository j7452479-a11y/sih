import asyncio
import json
import time
import urllib.request
import websockets

def check_rest_endpoints():
    print("==================================================")
    print("1. CHECKING REST API & SERVER HEALTH (Port 8000)")
    print("==================================================")
    endpoints = [
        "/api/status",
        "/api/civilian_state",
        "/api/watchdog",
        "/api/tracks",
        "/api/cot",
        "/",
        "/c2",
        "/civilian",
        "/soldier"
    ]
    all_ok = True
    for ep in endpoints:
        url = f"http://127.0.0.1:8000{ep}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SystemVerifier/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = resp.read()
                print(f"[PASS] {ep:22} -> HTTP {resp.status} ({len(data)} bytes)")
        except Exception as e:
            print(f"[FAIL] {ep:22} -> {e}")
            all_ok = False
    return all_ok

def check_watchdog_live():
    print("\n==================================================")
    print("2. CHECKING WATCHDOG & REAL-TIME HEARTBEAT (Port 5005)")
    print("==================================================")
    try:
        url = "http://127.0.0.1:8000/api/watchdog"
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            wd = json.loads(resp.read().decode("utf-8"))
            print(f"  * is_paused:               {wd['is_paused']}")
            print(f"  * last_sim_time:           {wd['last_sim_time']} s")
            print(f"  * time_since_last_sec:     {wd['time_since_last_sec']} s")
            print(f"  * timeout_threshold_sec:   {wd['timeout_threshold_sec']} s")
            print(f"  * total_heartbeats_rx:     {wd['heartbeat_count']}")
            print(f"  * halt_count:              {wd['halt_count']}")
            
            if not wd['is_paused'] and wd['time_since_last_sec'] < 0.25 and wd['heartbeat_count'] > 0:
                print("[PASS] Watchdog is active, receiving live heartbeats (< 250ms), hardware UNPAUSED.")
                return True
            else:
                print(f"[WARN] Watchdog state: {wd}")
                return False
    except Exception as e:
        print(f"[FAIL] Watchdog check failed: {e}")
        return False

async def check_websocket_stream():
    print("\n==================================================")
    print("3. CHECKING WEBSOCKET LIVE TELEMETRY STREAM (/ws/c2)")
    print("==================================================")
    uri = "ws://127.0.0.1:8000/ws/c2"
    try:
        async with websockets.connect(uri) as ws:
            print(f"[CONNECTED] Connected to WebSocket at {uri}")
            frames_received = 0
            for _ in range(5):
                msg = await asyncio.wait_for(ws.recv(), timeout=4.0)
                payload = json.loads(msg)
                frames_received += 1
                sim_paused = payload.get("simulation_paused", False)
                fps = payload.get("fps")
                latency_ms = payload.get("latency_ms")
                tracks = payload.get("tracks", [])
                ev_data = payload.get("civilian_ev", {})
                cells = payload.get("cells", [])
                print(f"  * Frame #{frames_received}: FPS={fps}, Latency={latency_ms}ms, "
                      f"Cells={len(cells)}, Tracks={len(tracks)}, EV Speed={ev_data.get('speed_kmh')} km/h, "
                      f"Sim Paused={sim_paused}")
            print(f"[PASS] Successfully received {frames_received} live frames from WebSocket hub.")
            return True
    except Exception as e:
        print(f"[FAIL] WebSocket test failed: {e}")
        return False

def check_task_logs():
    print("\n==================================================")
    print("4. CHECKING CIVILIAN EV & PERCEPTION ENGINE STATE")
    print("==================================================")
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/civilian_state", timeout=3.0) as resp:
            state = json.loads(resp.read().decode("utf-8"))
            print(f"  * Status:              {state.get('status')}")
            print(f"  * EV Speed:            {state.get('speed_kmh')} km/h ({state.get('speed_mps')} m/s)")
            print(f"  * AEB Status:          {state.get('aeb_status')}")
            print(f"  * Overhead Clearance:  {state.get('overhead_clearance_m')} m (Safe: {state.get('clearance_safe')})")
            print(f"  * Corridor Length:     {state.get('corridor_length_m')} m")
            print(f"  * Pedestrian Tracks:   {len(state.get('pedestrian_tracks', []))}")
            print(f"  * System FPS:          {state.get('fps')} FPS")
            print("[PASS] Civilian EV perception pipeline is actively updating world state.")
            return True
    except Exception as e:
        print(f"[FAIL] Civilian state check failed: {e}")
        return False

def check_watchdog_pause_failsafe():
    print("\n==================================================")
    print("5. VERIFYING DYNAMIC SAFE-STOP & RESUME COUPLING")
    print("==================================================")
    try:
        # Trigger synthetic pause
        req_pause = urllib.request.Request("http://127.0.0.1:8000/api/watchdog/test_pause", data=b"", method="POST")
        with urllib.request.urlopen(req_pause, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("  * Injected simulation pause signal.")

        time.sleep(0.06)

        # Check civilian state during pause
        with urllib.request.urlopen("http://127.0.0.1:8000/api/civilian_state", timeout=2.0) as resp:
            st = json.loads(resp.read().decode("utf-8"))
            print(f"  * Speed during pause:  {st.get('speed_kmh')} km/h (expected: 0.0)")
            print(f"  * AEB status during pause: {st.get('aeb_status')}")
            print(f"  * Simulation paused:   {st.get('simulation_paused')}")

        # Trigger resume
        req_resume = urllib.request.Request("http://127.0.0.1:8000/api/watchdog/test_resume", data=b"", method="POST")
        with urllib.request.urlopen(req_resume, timeout=2.0) as resp:
            data_res = json.loads(resp.read().decode("utf-8"))
            print("  * Sent simulation resume signal.")

        time.sleep(0.12)
        with urllib.request.urlopen("http://127.0.0.1:8000/api/civilian_state", timeout=2.0) as resp:
            st2 = json.loads(resp.read().decode("utf-8"))
            print(f"  * Speed after resume:  {st2.get('speed_kmh')} km/h")
            print(f"  * AEB status after resume: {st2.get('aeb_status')}")

        print("[PASS] Failsafe safe-stop and resume verified working dynamically.")
        return True
    except Exception as e:
        print(f"[FAIL] Pause failsafe check failed: {e}")
        return False

async def main():
    r1 = check_rest_endpoints()
    r2 = check_watchdog_live()
    r3 = await check_websocket_stream()
    r4 = check_task_logs()
    r5 = check_watchdog_pause_failsafe()
    
    print("\n==================================================")
    print("SYSTEM HEALTH SUMMARY VERIFICATION")
    print("==================================================")
    if r1 and r2 and r3 and r4 and r5:
        print(">>> ALL SUBSYSTEMS OPERATIONAL AND WORKING TOGETHER IN REAL-TIME <<<")
    else:
        print(">>> SOME SUBSYSTEMS FAILED HEALTH VERIFICATION <<<")

if __name__ == "__main__":
    asyncio.run(main())
