import socket
import uvicorn
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

def run():
    port = 8085
    # Create dual-stack socket to support both IPv6 (::1, localhost) and IPv4 (127.0.0.1) on Windows
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    sock.bind(('::', port))
    sock.listen(128)
    
    print(f"Mnemosyne server running at http://localhost:{port}/ (dual-stack IPv4/IPv6)")
    
    config = uvicorn.Config(
        "api.index:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )
    server = uvicorn.Server(config)
    server.run(sockets=[sock])

if __name__ == "__main__":
    run()
