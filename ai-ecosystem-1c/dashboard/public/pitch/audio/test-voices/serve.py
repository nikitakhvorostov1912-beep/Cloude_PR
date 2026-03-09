"""Threaded HTTP server with Range request support for audio playback."""
import http.server
import socketserver
import os
import mimetypes

os.chdir(os.path.dirname(os.path.abspath(__file__)))


class RangeHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler with Range requests (required by Chrome for audio)."""

    def do_GET(self):
        path = self.translate_path(self.path.split("?")[0])
        if not os.path.isfile(path):
            return super().do_GET()

        file_size = os.path.getsize(path)
        range_header = self.headers.get("Range")

        if range_header:
            try:
                range_spec = range_header.replace("bytes=", "")
                parts = range_spec.split("-")
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if parts[1] else file_size - 1
                end = min(end, file_size - 1)
                length = end - start + 1

                self.send_response(206)
                ct = mimetypes.guess_type(path)[0] or "application/octet-stream"
                self.send_header("Content-Type", ct)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(path, "rb") as f:
                    f.seek(start)
                    self.wfile.write(f.read(length))
            except Exception:
                self.send_error(416, "Range Not Satisfiable")
        else:
            self.send_response(200)
            ct = mimetypes.guess_type(path)[0] or "application/octet-stream"
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(path, "rb") as f:
                self.wfile.write(f.read())

    def log_message(self, fmt, *args):
        print(f"  {args[0]}")


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


print("Audio server: http://localhost:8899 (threaded, Range OK)")
print("Press Ctrl+C to stop\n")
ThreadedServer(("", 8899), RangeHTTPHandler).serve_forever()
