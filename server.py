"""
Local Web-Based Chat Application - Server
==========================================
Author: Chandan Thakur
GitHub: github.com/[your-username]
Description: WebSocket-based real-time chat server supporting
             10+ concurrent users on a local network.
"""

import asyncio
import websockets
import json
from datetime import datetime


# Store connected clients: {websocket: username}
connected_clients = {}


def broadcast_message(message: dict) -> str:
    """Serialize a message dict to JSON string."""
    return json.dumps(message)


async def notify_all(message: dict, exclude=None):
    """Broadcast a message to all connected clients."""
    if connected_clients:
        msg = broadcast_message(message)
        recipients = [
            ws for ws in connected_clients
            if ws != exclude
        ]
        if recipients:
            await asyncio.gather(
                *[ws.send(msg) for ws in recipients],
                return_exceptions=True
            )


async def notify_user_list():
    """Send updated user list to all clients."""
    user_list = list(connected_clients.values())
    await notify_all({
        "type": "user_list",
        "users": user_list,
        "count": len(user_list)
    })


async def handle_client(websocket):
    """Handle individual client connection lifecycle."""
    username = None

    try:
        # Wait for join message with username
        raw = await websocket.recv()
        data = json.loads(raw)

        if data.get("type") != "join":
            await websocket.close()
            return

        username = data.get("username", "Anonymous").strip()
        if not username:
            username = "Anonymous"

        # Ensure username uniqueness
        existing_names = list(connected_clients.values())
        original = username
        counter = 1
        while username in existing_names:
            username = f"{original}_{counter}"
            counter += 1

        # Register client
        connected_clients[websocket] = username
        print(f"[+] {username} joined | Total users: {len(connected_clients)}")

        # Confirm join to the new user
        await websocket.send(broadcast_message({
            "type": "joined",
            "username": username,
            "message": f"Welcome to the chat, {username}!",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }))

        # Announce to all other users
        await notify_all({
            "type": "system",
            "message": f"{username} has joined the chat.",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }, exclude=websocket)

        # Send updated user list
        await notify_user_list()

        # Main message loop
        async for raw_message in websocket:
            try:
                data = json.loads(raw_message)

                if data.get("type") == "message":
                    text = data.get("text", "").strip()
                    if not text:
                        continue

                    print(f"[{username}]: {text}")

                    # Broadcast to all clients including sender
                    await notify_all({
                        "type": "message",
                        "username": username,
                        "text": text,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })

                elif data.get("type") == "typing":
                    # Broadcast typing indicator to others
                    await notify_all({
                        "type": "typing",
                        "username": username,
                        "is_typing": data.get("is_typing", False)
                    }, exclude=websocket)

            except json.JSONDecodeError:
                continue

    except websockets.exceptions.ConnectionClosedOK:
        pass
    except websockets.exceptions.ConnectionClosedError:
        pass
    except Exception as e:
        print(f"[ERROR] {e}")

    finally:
        # Clean up on disconnect
        if websocket in connected_clients:
            del connected_clients[websocket]
            if username:
                print(f"[-] {username} left | Total users: {len(connected_clients)}")
                await notify_all({
                    "type": "system",
                    "message": f"{username} has left the chat.",
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                })
                await notify_user_list()


async def main():
    """Start the WebSocket server."""
    host = "0.0.0.0"
    port = 8765

    print("=" * 50)
    print("  Local Chat Server")
    print("=" * 50)
    print(f"  Server running on ws://{host}:{port}")
    print(f"  Open index.html in your browser")
    print(f"  Share your local IP with friends")
    print(f"  Supports 10+ concurrent users")
    print("=" * 50)
    print("  Press Ctrl+C to stop")
    print("=" * 50)

    async with websockets.serve(handle_client, host, port):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Server stopped]")
