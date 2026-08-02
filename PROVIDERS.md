WorkerManager Provider and AppSettings

This document explains the provider pattern used to select and initialize the
WorkerManager implementation for the application. The approach uses Pydantic
settings (AppSettings) and a small factory (create_worker_manager) to allow
switching implementations by environment variables.

Files of interest
- backend/app/settings.py
  - Defines AppSettings (Pydantic BaseSettings) and get_settings() helper.
  - Reads APP_ENV and WORKER_MANAGER_TYPE from environment.

- backend/app/providers/worker_manager_provider.py
  - Implements create_worker_manager(settings: Optional[AppSettings]) -> WorkerManager | MockWorkerManager
  - Provides MockWorkerManager (no-op) for tests/development.
  - Returns real WorkerManager when WORKER_MANAGER_TYPE=real (or production/dev defaults).

How it works
1. Configuration
   - Set environment variables to influence the provider:
     - APP_ENV (optional): development | test | production
     - WORKER_MANAGER_TYPE: real | mock | dev
   - Example:
       export APP_ENV=production
       export WORKER_MANAGER_TYPE=real
     or
       export APP_ENV=test
       export WORKER_MANAGER_TYPE=mock

2. Provider
   - create_worker_manager reads AppSettings (from environment unless provided explicitly) and returns the selected implementation.
   - The provider does not create global singletons. It returns a fresh instance on each call.

3. Protocol / Interface
   - The app defines a WorkerManagerProtocol (app.workers.protocols.WorkerManagerProtocol) that captures the required behaviors (start_all, stop_all, start_camera, stop_camera, restart_camera, status, list_workers, health_check, shutdown).
   - Implementations (RealWorkerManagerAdapter and MockWorkerManager) implement this protocol. Dependencies and routes depend on the protocol, not concrete implementations.

4. Integration with FastAPI
   - The FastAPI lifespan manager in app.main imports and calls create_worker_manager() at startup and stores the instance on app.state.worker_manager.
   - The FastAPI dependency get_worker_manager (in app.dependencies.worker_manager) retrieves that instance from app.state; routes should use Depends(get_worker_manager) to receive the manager. Since the dependency returns the protocol type, routes are decoupled from concrete classes.

Testing
- The tests under backend/app/tests/test_provider_factory.py show example usage:
  - set WORKER_MANAGER_TYPE=mock and ensure create_worker_manager returns MockWorkerManager
  - set WORKER_MANAGER_TYPE=real and ensure it returns a real WorkerManager
  - invalid values raise a ValueError
  - FastAPI can use the factory in its startup to attach the selected implementation to app.state; routes using the dependency receive the same injected instance.

Extending the pattern
- To add a new WorkerManager implementation (e.g., a Redis-backed manager), implement the class and update create_worker_manager to recognize a new type string.
- For other services (repositories, external clients), follow the same pattern:
  - Add a provider module that accepts AppSettings and returns the appropriate implementation
  - Use FastAPI lifespan to attach instances to app.state and provide a dependency function to retrieve them

Notes
- The provider function deliberately returns new instances (no global singletons). Lifespan or DI should govern lifetime.
- Error handling: create_worker_manager raises ValueError for unsupported types; callers should handle it and fail early with useful logs.
