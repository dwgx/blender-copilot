"""Helper to execute Python code in Blender via TCP socket."""
import socket, json, sys
sys.stdout.reconfigure(encoding='utf-8')

def exec_blender(code: str, timeout: int = 30) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(('localhost', 9876))
        cmd = json.dumps({'type': 'execute_code', 'params': {'code': code}})
        sock.sendall(cmd.encode('utf-8'))
        data = b''
        while True:
            try:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                data += chunk
                try:
                    json.loads(data.decode('utf-8'))
                    break
                except:
                    continue
            except socket.timeout:
                break
        resp = json.loads(data.decode('utf-8'))
        if resp.get('status') == 'error':
            return f"ERROR: {resp.get('message', 'unknown')}"
        return resp.get('result', {}).get('result', '')
    except Exception as e:
        return f"CONNECTION ERROR: {e}"
    finally:
        sock.close()

if __name__ == '__main__':
    code = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    print(exec_blender(code))
