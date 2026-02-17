"""Exception hierarchy for Docker sandbox operations."""


class SandboxError(Exception):
    """Base class for all sandbox-related errors."""


class DockerNotAvailableError(SandboxError):
    """Docker SDK not installed or daemon not reachable."""

    def __init__(self, message: str = "Docker is not available."):
        super().__init__(message)


class DockerNotInstalledError(DockerNotAvailableError):
    """Docker Python SDK is not installed."""

    def __init__(self):
        super().__init__(
            "Docker SDK not installed. Run: pip install docker"
        )


class DockerDaemonNotRunningError(DockerNotAvailableError):
    """Docker daemon is not running."""

    def __init__(self):
        super().__init__(
            "Docker daemon is not running. Please start Docker Desktop."
        )


class ImageBuildError(SandboxError):
    """Docker image build failed."""

    def __init__(self, message: str = "Docker image build failed.", build_log: str = ""):
        self.build_log = build_log
        super().__init__(message)


class ContainerCreateError(SandboxError):
    """Container creation failed."""


class ContainerStartError(SandboxError):
    """Container start failed."""


class ContainerCrashedError(SandboxError):
    """Container crashed during execution."""


class InvalidStateError(SandboxError):
    """Invalid container state transition attempted."""

    def __init__(self, current_state: str, attempted_action: str):
        self.current_state = current_state
        self.attempted_action = attempted_action
        super().__init__(
            f"Cannot {attempted_action} from state '{current_state}'"
        )


class MountValidationError(SandboxError):
    """Mount specification validation failed."""


class ScriptGenerationError(SandboxError):
    """Bash loop script generation failed."""
