"""Server-side rendering for PlantUML and D2 diagrams."""
import hashlib
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError
import zlib
import string

logger = logging.getLogger(__name__)

# Simple in-memory cache keyed by SHA-256 of source content
_svg_cache: dict[str, str] = {}


def _cache_key(source: str, fmt: str) -> str:
    """Generate cache key from source content and format."""
    h = hashlib.sha256(f"{fmt}:{source}".encode("utf-8")).hexdigest()
    return h


def _plantuml_encode(source: str) -> str:
    """Encode PlantUML source for URL-based rendering.

    Uses deflate compression + PlantUML's custom base64 encoding.
    """
    compressed = zlib.compress(source.encode("utf-8"))[2:-4]
    # PlantUML uses a custom base64 alphabet
    alphabet = string.digits + string.ascii_uppercase + string.ascii_lowercase + "-_"
    result = []
    for i in range(0, len(compressed), 3):
        chunk = compressed[i:i + 3]
        if len(chunk) == 3:
            b1, b2, b3 = chunk
            result.append(alphabet[b1 >> 2])
            result.append(alphabet[((b1 & 0x3) << 4) | (b2 >> 4)])
            result.append(alphabet[((b2 & 0xF) << 2) | (b3 >> 6)])
            result.append(alphabet[b3 & 0x3F])
        elif len(chunk) == 2:
            b1, b2 = chunk
            result.append(alphabet[b1 >> 2])
            result.append(alphabet[((b1 & 0x3) << 4) | (b2 >> 4)])
            result.append(alphabet[(b2 & 0xF) << 2])
        elif len(chunk) == 1:
            b1 = chunk[0]
            result.append(alphabet[b1 >> 2])
            result.append(alphabet[(b1 & 0x3) << 4])
    return "".join(result)


PLANTUML_PUBLIC_API = "https://www.plantuml.com/plantuml/svg/"


class RenderService:
    """Renders PlantUML and D2 diagrams to SVG."""

    @staticmethod
    def is_plantuml_available() -> bool:
        """Check if PlantUML rendering is available (public API is always available)."""
        return True  # We use public API as fallback

    @staticmethod
    def is_d2_available() -> bool:
        """Check if D2 CLI binary is on PATH."""
        return shutil.which("d2") is not None

    @staticmethod
    def render_plantuml(source: str) -> dict:
        """Render PlantUML source to SVG via public HTTP API.

        Returns dict with either 'svg' key or 'error' + 'raw_source' keys.
        """
        key = _cache_key(source, "plantuml")
        if key in _svg_cache:
            return {"svg": _svg_cache[key]}

        try:
            encoded = _plantuml_encode(source)
            url = f"{PLANTUML_PUBLIC_API}{encoded}"
            req = Request(url, headers={"User-Agent": "Vista/1.0"})
            with urlopen(req, timeout=15) as resp:
                svg = resp.read().decode("utf-8")
            _svg_cache[key] = svg
            return {"svg": svg}
        except (URLError, TimeoutError) as e:
            logger.warning("PlantUML render failed: %s", e)
            return {"error": f"PlantUML render failed: {e}", "raw_source": source}

    @staticmethod
    def render_d2(source: str) -> dict:
        """Render D2 source to SVG via CLI subprocess.

        Returns dict with either 'svg' key or 'error' + 'raw_source' keys.
        """
        key = _cache_key(source, "d2")
        if key in _svg_cache:
            return {"svg": _svg_cache[key]}

        if not RenderService.is_d2_available():
            return {
                "error": "D2 CLI not installed. Install from https://d2lang.com/",
                "raw_source": source,
            }

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".d2", mode="w", delete=False, encoding="utf-8"
            ) as f:
                f.write(source)
                input_path = Path(f.name)

            output_path = input_path.with_suffix(".svg")
            try:
                result = subprocess.run(
                    ["d2", str(input_path), str(output_path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    return {
                        "error": f"D2 render failed: {result.stderr}",
                        "raw_source": source,
                    }
                svg = output_path.read_text(encoding="utf-8")
                _svg_cache[key] = svg
                return {"svg": svg}
            finally:
                input_path.unlink(missing_ok=True)
                output_path.unlink(missing_ok=True)
        except subprocess.TimeoutExpired:
            return {"error": "D2 render timed out", "raw_source": source}
        except Exception as e:
            logger.warning("D2 render failed: %s", e)
            return {"error": f"D2 render failed: {e}", "raw_source": source}

    @staticmethod
    def render(source: str, format_type: str) -> dict:
        """Dispatch rendering based on format type.

        Args:
            source: Raw diagram source code
            format_type: One of 'plantuml', 'd2'

        Returns dict with 'svg' on success, or 'error' + 'raw_source' on failure.
        """
        if format_type == "plantuml":
            return RenderService.render_plantuml(source)
        elif format_type == "d2":
            return RenderService.render_d2(source)
        else:
            return {"error": f"Unsupported render format: {format_type}", "raw_source": source}
