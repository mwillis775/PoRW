# src/porw_blockchain/node/p2p.py
"""
Peer-to-peer networking functionalities for node communication.

Handles discovering, connecting to, and communicating with other nodes
in the PoRW blockchain network.
"""

import asyncio
import dataclasses
import logging
from typing import Set

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
DEFAULT_P2P_PORT = 6888 # Example port, make configurable later
NODE_HOST = "0.0.0.0" # Listen on all available interfaces

# --- Data Structures ---

@dataclasses.dataclass
class Peer:
    """Represents a connected peer node."""
    host: str
    port: int
    reader: asyncio.StreamReader | None = None # Added by Bill for state management
    writer: asyncio.StreamWriter | None = None # Added by Bill for state management
    # Add more state as needed (e.g., connection time, version)

    def __hash__(self):
        # Allow adding Peer objects to sets based on host/port
        return hash((self.host, self.port))

    def __eq__(self, other):
        if not isinstance(other, Peer):
            return NotImplemented
        return (self.host, self.port) == (other.host, other.port)

# --- State Management (Simplified) ---
# A simple way to keep track of connected peers. Might need more robust management later.
connected_peers: Set[Peer] = set() # Added by Bill

# --- P2P Message Handling ---

# Define message types (example structure)
MESSAGE_TYPES = {
    "STATUS_REQUEST": "status_request",
    "STATUS_RESPONSE": "status_response",
    "BLOCK_REQUEST": "block_request",
    "BLOCK_RESPONSE": "block_response",
    "TRANSACTION_BROADCAST": "transaction_broadcast",
}

def process_message(message: str) -> str:
    """
    Processes an incoming P2P message and returns an appropriate response.

    Args:
        message: The raw message string received from a peer.

    Returns:
        A response string to send back to the peer.
    """
    try:
        # Parse the message (assuming JSON format for simplicity)
        import json
        parsed_message = json.loads(message)
        message_type = parsed_message.get("type")

        if message_type == MESSAGE_TYPES["STATUS_REQUEST"]:
            # Example: Respond with node status
            return json.dumps({"type": MESSAGE_TYPES["STATUS_RESPONSE"], "status": "ok"})

        elif message_type == MESSAGE_TYPES["BLOCK_REQUEST"]:
            # Example: Respond with requested block (placeholder logic)
            block_id = parsed_message.get("block_id")
            return json.dumps({"type": MESSAGE_TYPES["BLOCK_RESPONSE"], "block_id": block_id, "data": "block_data_placeholder"})

        elif message_type == MESSAGE_TYPES["TRANSACTION_BROADCAST"]:
            # Example: Acknowledge transaction broadcast
            return json.dumps({"type": "ack", "message": "Transaction received"})

        else:
            return json.dumps({"type": "error", "message": "Unknown message type"})

    except json.JSONDecodeError:
        return json.dumps({"type": "error", "message": "Invalid message format"})

# --- Connection Handling ---

async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """
    Callback function invoked by the asyncio server when a new peer connects.
    Manages the lifecycle of a single peer connection.
    """
    peer_addr = writer.get_extra_info('peername')
    host, port = peer_addr
    peer = Peer(host=host, port=port, reader=reader, writer=writer)
    logger.info(f"Accepted connection from {host}:{port}")
    connected_peers.add(peer) # Track connected peer

    try:
        while True:
            data = await reader.read(1024) # Read up to 1KB
            if not data:
                logger.info(f"Connection closed by {host}:{port}")
                break

            message = data.decode()
            logger.info(f"Received message from {host}:{port}: {message.strip()}")

            # Process the message and generate a response
            response = process_message(message)
            writer.write(response.encode())
            await writer.drain()

    except ConnectionResetError:
        logger.warning(f"Connection reset by {host}:{port}")
    except asyncio.CancelledError:
        logger.info(f"Connection handling cancelled for {host}:{port}")
        raise
    except Exception as e:
        logger.error(f"Error handling connection from {host}:{port}: {e}", exc_info=True)
    finally:
        logger.info(f"Closing connection to {host}:{port}")
        connected_peers.discard(peer)
        try:
            if not writer.is_closing():
                writer.close()
                await writer.wait_closed()
        except Exception as e:
            logger.error(f"Error closing writer for {host}:{port}: {e}", exc_info=False)

async def connect_to_peer(host: str, port: int) -> bool:
    """
    Initiates an outbound connection to a specified peer.

    Args:
        host: The hostname or IP address of the peer.
        port: The port number of the peer.

    Returns:
        True if connection (and handling) was successful, False otherwise.
    """
    logger.info(f"Attempting to connect to peer {host}:{port}...")
    try:
        reader, writer = await asyncio.open_connection(host, port)
        # Connection successful, start handling it (similar to handle_connection)
        # Often, you'd run the handling logic in a separate task
        # For simplicity here, we assume handle_connection logic would run
        logger.info(f"Successfully connected to peer {host}:{port}. Starting handler...")
        # In a real scenario, you might start handle_connection as a task:
        # asyncio.create_task(handle_connection(reader, writer))
        # For now, just log success and maybe add to peer list if needed
        # We don't call handle_connection directly here to avoid blocking
        # and simplify this example function's responsibility.
        # Adding peer directly might be premature without confirmation/handshake.
        return True # Indicate connection attempt was successful

    except ConnectionRefusedError:
        logger.error(f"Connection refused by peer {host}:{port}")
        return False
    except OSError as e: # Handle other potential network errors
        logger.error(f"Error connecting to peer {host}:{port}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error connecting to peer {host}:{port}: {e}", exc_info=True)
        return False


async def start_p2p_server(host: str = NODE_HOST, port: int = DEFAULT_P2P_PORT):
    """
    Starts the P2P server to listen for incoming connections.
    """
    try:
        server = await asyncio.start_server(handle_connection, host, port)
        addr = server.sockets[0].getsockname()
        logger.info(f"P2P Server started, listening on {addr[0]}:{addr[1]}")

        # Keep the server running indefinitely
        async with server:
            await server.serve_forever()

    except OSError as e: # Handle errors like "address already in use"
        logger.error(f"Failed to start P2P server on {host}:{port}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error starting P2P server: {e}", exc_info=True)


# --- Main Execution (Example Usage) ---
async def main():
    """Main async function to start the server and potentially connect to peers."""
    server_task = asyncio.create_task(start_p2p_server())

    # Example: try connecting to a known peer after server starts
    await asyncio.sleep(2) # Give server time to start
    # Replace with actual peer discovery/bootstrap nodes later
    # success = await connect_to_peer("localhost", DEFAULT_P2P_PORT + 1) # Example

    # Wait for server task (runs forever unless cancelled)
    await server_task


# This allows running the p2p server directly for testing, if needed
# Usually, this would be started as part of the main node application lifecycle
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("P2P Server stopped by user.")