# Private Chat

Private Chat combines the self-hosted server, Desktop, Android, iOS, and project documentation in one repository.

| Directory | Component |
| --- | --- |
| [`server/`](server/README.md) | Go server and local development stack |
| [`desktop/`](desktop/README.md) | Native Desktop client |
| [`android/`](android/README.md) | Android client |
| [`ios/`](ios/README.md) | iOS client |
| [`docs/`](docs/README.md) | Architecture, migration, and integration documentation |

The components retain their existing build systems and relative directory layout. Local toolchains, third-party dependency builds, application state, and integration logs are ignored by Git.

Start with [`docs/local-integration.md`](docs/local-integration.md) for local setup and [`docs/ci-cd.md`](docs/ci-cd.md) for unified verification and preview packaging. The source and native preview workflows do not establish production readiness. Native signing and the complete multi-client acceptance checks must be verified separately.

The local import workspace retains the five source histories for audit and recovery. [`repository-imports.json`](repository-imports.json) records each source HEAD and tree. The first public release of `shiyi-log/private-chat` is a screened, history-free source snapshot: it contains the five components and the unified CI/CD files, while omitting the imported history that contains a server-side private key. The source repositories remain available as historical inputs; publishing their old histories requires a separate secret-rotation and history-rewrite review.

The public unified repository is `shiyi-log/private-chat`. The next source preview is `v0.2.0-preview.1`. Source push and GitHub Release publication require authenticated GitHub access; until their actual runs are recorded, local checks do not establish a successful remote release.

Each component retains its license and upstream notices. See the LICENSE and other legal notices within its directory before redistribution.
