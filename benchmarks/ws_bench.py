from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
import httpx

try:
    import websockets
except ImportError:
    websockets = None


async def run_websocket_latency_benchmark(
    base_url: str = "http://localhost:8000",
    concurrent_clients: int = 100,
    iterations: int = 20,
) -> None:
    """Measure end-to-end WebSocket broadcast propagation latency across 100 concurrent dashboard clients."""
    if websockets is None:
        print("Error: 'websockets' package is required for WebSocket benchmarking.")
        print("Install via: pip install websockets")
        return

    base_url = base_url.rstrip("/")
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"

    print("==================================================")
    print(" SURAKSHAGRID WEBSOCKET REAL-TIME PROPAGATION BENCHMARK")
    print(f" Target WS Gateway: {ws_url}")
    print(f" Concurrent Dashboard Sockets: {concurrent_clients}")
    print(f" Test Iterations: {iterations}")
    print("==================================================")

    # 1. Open 100 Concurrent WebSocket Connections
    print(f"\n[1/3] Establishing {concurrent_clients} concurrent WebSocket connections...")
    sockets = []
    received_events = asyncio.Queue()

    async def _ws_listener(client_id: int):
        try:
            async with websockets.connect(ws_url) as ws:
                sockets.append(ws)
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if data.get("type") in ("NEW_INCIDENT", "NEW_SOS_ALERT"):
                        recv_ts = time.perf_counter()
                        await received_events.put((client_id, data, recv_ts))
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    listener_tasks = [asyncio.create_task(_ws_listener(i)) for i in range(concurrent_clients)]

    # Wait for connections to complete handshake
    await asyncio.sleep(2.0)
    print(f"      ✓ Successfully connected {len(sockets)} / {concurrent_clients} WebSocket clients.")

    # 2. Trigger HTTP POST SOS Events and Measure End-to-End Latency
    print(f"\n[2/3] Triggering {iterations} emergency SOS HTTP POST requests...")
    propagation_latencies_ms: list[float] = []

    async with httpx.AsyncClient(timeout=10.0) as http_client:
        for i in range(iterations):
            sos_payload = {
                "category": "CRITICAL_TRAPPED",
                "phone": f"+91-999{i:05d}",
                "emergencyType": "CRITICAL_TRAPPED",
                "lat": 28.6321 + i * 0.001,
                "lng": 77.4446 + i * 0.001,
                "notes": f"WebSocket latency benchmark test payload #{i+1}",
            }

            post_start = time.perf_counter()
            res = await http_client.post(f"{base_url}/api/v1/sos/", json=sos_payload)
            assert res.status_code == 201, f"POST failed: {res.text}"

            # Drain received events for this trigger
            collected_for_trigger = 0
            deadline = time.perf_counter() + 2.0
            while collected_for_trigger < len(sockets) and time.perf_counter() < deadline:
                try:
                    client_id, data, recv_ts = await asyncio.wait_for(received_events.get(), timeout=0.2)
                    latency = (recv_ts - post_start) * 1000.0
                    propagation_latencies_ms.append(latency)
                    collected_for_trigger += 1
                except asyncio.TimeoutError:
                    break

            print(f"      Batch {i+1}/{iterations}: Received by {collected_for_trigger}/{len(sockets)} clients.")

    # Clean up listener tasks
    for task in listener_tasks:
        task.cancel()

    # 3. Output Statistical Latency Results
    print("\n[3/3] Performance & Latency Report")
    if propagation_latencies_ms:
        avg_lat = statistics.mean(propagation_latencies_ms)
        p95_lat = sorted(propagation_latencies_ms)[int(len(propagation_latencies_ms) * 0.95)]
        p99_lat = sorted(propagation_latencies_ms)[int(len(propagation_latencies_ms) * 0.99)]

        print(f"      Total Event Frames Delivered: {len(propagation_latencies_ms)}")
        print(f"      Average Latency: {avg_lat:.2f} ms")
        print(f"      95th Percentile (p95): {p95_lat:.2f} ms")
        print(f"      99th Percentile (p99): {p99_lat:.2f} ms")

        if p95_lat < 200.0:
            print(f"\n✓ PASS: Real-time broadcast latency ({p95_lat:.2f} ms) satisfies PRD v1.0.0 target (<200 ms).")
        else:
            print(f"\n⚠️ WARNING: p95 latency ({p95_lat:.2f} ms) exceeded 200 ms target under load.")
    else:
        print("      No WebSocket frames received during test window.")

    print("==================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SurakshaGrid WebSocket Real-Time Latency Benchmark")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--clients", type=int, default=100, help="Number of concurrent WebSocket connections")
    parser.add_argument("--iterations", type=int, default=10, help="Number of test iterations")
    args = parser.parse_args()

    asyncio.run(run_websocket_latency_benchmark(args.url, args.clients, args.iterations))
