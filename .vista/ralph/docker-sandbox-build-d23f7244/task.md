Implement the docker-sandbox feature for the Vista plugin, following the 6-phase IMPLEMENTATION_PLAN.md at .vista/features/docker-sandbox/IMPLEMENTATION_PLAN.md.

Work through ALL phases incrementally. Each phase has a test gate — run the tests and get them GREEN before moving to the next phase:

Phase 1: Settings + Docker SDK Connection
  - Extend settings.json with sandbox config
  - Add _SANDBOX_DEFAULTS and get_sandbox_config() to config.py
  - Create sandbox_errors.py exception hierarchy
  - Create docker_client.py lazy wrapper
  - Tests: python -m pytest tests/test_sandbox_config.py tests/test_docker_client.py -v

Phase 2: Container Lifecycle (TDD)
  - Create container_manager.py with state machine, MountSpec, ContainerInfo dataclasses
  - Tests FIRST from TDD diagrams, then implement
  - Tests: python -m pytest tests/test_container_manager.py -v

Phase 3: Credential Mounting (TDD)
  - Create credential_mounter.py with cross-platform path resolution
  - 15 path resolution tests (3 OS x 5 credentials) from TDD decision tree
  - Tests: python -m pytest tests/test_credential_mounter.py -v

Phase 4: Bash Loop Generation (TDD)
  - Add BASH_LOOP_SCRIPT_TEMPLATE to portable/ralph.py
  - Create bash_loop_generator.py
  - Tests: python -m pytest tests/test_bash_loop_generator.py -v

Phase 5: Docker Integration Tests (requires Docker)
  - Create docker/Dockerfile from claudebox base
  - Integration tests with real Docker
  - Tests: python -m pytest tests/integration/test_docker_sandbox.py -v -m docker

Phase 6: End-to-End Ralph Integration
  - Extend ralph_service.py create_job() with sandbox param
  - Extend stop_job() and get_job_status()
  - Add sandbox param to ralph_start MCP tool
  - Add /sandbox/status and /sandbox/build API routes
  - Tests: python -m pytest tests/test_sandbox_integration.py -v

Read ALL specs at .vista/features/docker-sandbox/specs/*.md and ALL TDD diagrams at .vista/features/docker-sandbox/arch/tdd-*.mmd before starting.

IMPORTANT: Run tests from the vista/ directory with: python -m pytest tests/... -v
All test files go under vista/tests/ (not vista/vista/tests/).