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

Start with [`docs/local-integration.md`](docs/local-integration.md) for local setup and [`docs/ci-cd.md`](docs/ci-cd.md) for unified verification and preview packaging. The source and native preview workflows do not establish production readiness. Production signing and distribution remain separate from this local native acceptance.

Local native acceptance on November 5, 2026 verified bidirectional text and file transfers for Android account 101 ↔ iOS account 102 and Desktop account 101 ↔ iOS account 102, including receiver-side opens and SHA-256 checks. Android and Desktop share account 101; Android showed the new Desktop and iOS messages and attachment entries in account history. Android also downloaded and opened the new 79-byte iOS attachment with a matching SHA-256; the new 63-byte Desktop attachment was visible in history but was not separately downloaded or hashed on Android. See the local integration report for exact scope and remaining distribution requirements.

The local import workspace retains the five source histories for audit and recovery. [`repository-imports.json`](repository-imports.json) records each source HEAD and tree. The first public release of `shiyi-log/private-chat` is a screened, history-free source snapshot: it contains the five components and the unified CI/CD files, while omitting the imported history that contains a server-side private key. The source repositories remain available as historical inputs; publishing their old histories requires a separate secret-rotation and history-rewrite review.

The public unified repository is `shiyi-log/private-chat`. `v0.2.0-preview.1` is the candidate five-component source preview. A verified candidate baseline at `83cab6ef6ec66fa452e11f0abb50618d34a5612c` passed CI run `42027610583`; release preview dry run `42028718339` generated its source archive and notes. A published release is established by its tag and the manifest's `source_commit`. See [GitHub Releases](https://github.com/shiyi-log/private-chat/releases) for current availability and the exact published revision.

Each component retains its license and upstream notices. See the LICENSE and other legal notices within its directory before redistribution.
