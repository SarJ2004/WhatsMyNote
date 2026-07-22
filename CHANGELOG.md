# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2](https://github.com/SarJ2004/WhatsMyNote/compare/v0.2.1...v0.2.2) (2026-07-22)


### Bug Fixes

* disable wait_deploy polling in Render GitHub Action to prevent API crash ([d8848af](https://github.com/SarJ2004/WhatsMyNote/commit/d8848aff213b4ee37b41736120a67cab7343d559))

## [0.2.1](https://github.com/SarJ2004/WhatsMyNote/compare/v0.2.0...v0.2.1) (2026-07-22)


### Bug Fixes

* fallback API_URL to prod when ENV is unset ([c281fa9](https://github.com/SarJ2004/WhatsMyNote/commit/c281fa99e8fc43bf8594b1b08f3187ac027b7509))

## [0.2.0](https://github.com/SarJ2004/WhatsMyNote/compare/v0.1.3...v0.2.0) (2026-07-22)


### Features

* add a TUI interface for login/singnup flow ([0c6392f](https://github.com/SarJ2004/WhatsMyNote/commit/0c6392ff7aef7c4f2cde3ebccb8a2a96df92bb2d))
* add logout support to the TUI ([7d1590c](https://github.com/SarJ2004/WhatsMyNote/commit/7d1590ce09c7b2a97a29a4398026ac14e3588c49))
* add sentry for monitoring and observability support ([09dea77](https://github.com/SarJ2004/WhatsMyNote/commit/09dea77d9b59d67245c934e59ca8929784134765))
* add sentry for monitoring and observability support ([a973296](https://github.com/SarJ2004/WhatsMyNote/commit/a97329621d37338ca9a5f9b5483398f56c37c0b1))
* add sentry support in the cli frontend ([87ab433](https://github.com/SarJ2004/WhatsMyNote/commit/87ab433eb374787cce1ace485bf36f0764c3d577))
* add sentry support in the cli frontend and added logging in both be and fe ([c9dc0bb](https://github.com/SarJ2004/WhatsMyNote/commit/c9dc0bb441242a73826b2fa3c48b4b140eea1d3b))
* added support for the staging env ([a862da5](https://github.com/SarJ2004/WhatsMyNote/commit/a862da59481b4623d14112489547f22cc0706e43))
* finished the first iteration of the textual TUI ([52d30f9](https://github.com/SarJ2004/WhatsMyNote/commit/52d30f9f8483e8a156263ac74d834995cf61c095))
* updated the TUI to add more UI features ([7190c26](https://github.com/SarJ2004/WhatsMyNote/commit/7190c2649e24f888c6f11d50c04c25711e595fda))


### Bug Fixes

* add tags for frontend and backend sentry events ([8d9dbdb](https://github.com/SarJ2004/WhatsMyNote/commit/8d9dbdb955fdebe5bb4b79ea52603a615a0ec1fe))
* add tags for frontend and backend sentry events ([8d2cd3c](https://github.com/SarJ2004/WhatsMyNote/commit/8d2cd3cda13d9ed52bc33ca65d78f6b1325c846b))
* added commands at each step of the entire application, and modify the ui a bit ([a2aec0b](https://github.com/SarJ2004/WhatsMyNote/commit/a2aec0b5683c3085662683dae090d8a341b6b807))
* added commands at each step of the entire application, and modify the ui a bit ([ea76acc](https://github.com/SarJ2004/WhatsMyNote/commit/ea76accfed9fe2b58dee277deed44a4ff1d39cb1))
* improved the guardrails to make the app more robust ([bec5f37](https://github.com/SarJ2004/WhatsMyNote/commit/bec5f3775453e8f6016ce8ccdb06227d1544d918))
* improved the guardrails to make the app more robust ([9d25913](https://github.com/SarJ2004/WhatsMyNote/commit/9d25913117f04740d1c5643c65061fa9cf59f482))
* made the transfer rules stricter, and added Cash support to accounts ([a20259b](https://github.com/SarJ2004/WhatsMyNote/commit/a20259bffd19d81f5a710e963db318c180c2e738))
* update readme, docs and fixed a bug regarding rendering of charts ([e614422](https://github.com/SarJ2004/WhatsMyNote/commit/e614422c33a57c0d9c7aca92e021e34da455b3d3))

## [0.1.3](https://github.com/SarJ2004/WhatsMyNote/compare/v0.1.2...v0.1.3) (2026-07-14)


### Bug Fixes

* add data consistency which was missing in some tables, and added few fallbacks and guards for narrowing down checks on bank accounts and categories ([977bd09](https://github.com/SarJ2004/WhatsMyNote/commit/977bd09808a81f690c4ea783d241f16ea52450dd))
* added atomic record creation/updates to safeguard against partial updates ([b845173](https://github.com/SarJ2004/WhatsMyNote/commit/b845173f30fba5c98a050a6675ba93c496cb4f59))
* added forget password option to reset password across your accounts ([f86364c](https://github.com/SarJ2004/WhatsMyNote/commit/f86364c4baaa9e5d860394d8dbf553585c29da25))
* added forget password option to reset password across your accounts ([b126df1](https://github.com/SarJ2004/WhatsMyNote/commit/b126df1a5633a8ed9c720dca21fb7631c3559e1c))
* applied many tryouts to lessen down response times ([b0dbc0d](https://github.com/SarJ2004/WhatsMyNote/commit/b0dbc0d23ed3b03ee9b28fb47b32bcbed57fc124))
* chart rendering issues that were giving inconsistent results when the the user asked for a plot; sometimes it showed up, sometimes didnt. ([561a162](https://github.com/SarJ2004/WhatsMyNote/commit/561a16210255afbbbcef145b3745df8cf8909909))
* fixed a bug where the agent would repeat success messages, and a closure message after doing an update/delete operation successfully ([1b635cb](https://github.com/SarJ2004/WhatsMyNote/commit/1b635cbfd982a62435952399d9ab1a338b5a264b))
* replace evaluator llm  with light extractor llm to fasten up things, and added a response time debug log ([8904194](https://github.com/SarJ2004/WhatsMyNote/commit/8904194c238e074a25f87ff86c21dedb436b8774))
* tried to optimize query response times ([ea7a6ca](https://github.com/SarJ2004/WhatsMyNote/commit/ea7a6cacc8bc70875109ef700a84736842dac23f))
* update the categories picking system to help the models easily determine the categories, without hallucinating ([d897a08](https://github.com/SarJ2004/WhatsMyNote/commit/d897a08b673f5a60e4b7ecd8a00b5b9c8a25bb2a))
* update the categories picking system to help the models easily determine the categories, without hallucinating ([ccd7fdf](https://github.com/SarJ2004/WhatsMyNote/commit/ccd7fdf6a751598b6ef7032f6477f280ad9a0826))
* updated the backend with necessary fixes, and guardrails that make querying and response generation much more seamless and robust ([c2e109d](https://github.com/SarJ2004/WhatsMyNote/commit/c2e109d7f37e832d87dfd8e461ef3f11cbcedba0))


### Reverts

* added back forks and stars pills ([cd99325](https://github.com/SarJ2004/WhatsMyNote/commit/cd99325441074307b5238301d250249491614d71))


### Documentation

* overhaul documentation and add architecture diagrams ([e03c7f8](https://github.com/SarJ2004/WhatsMyNote/commit/e03c7f8c6609512f478eb1575bb71888fe7ade24))
* update documentation for the latest commits ([36ea9d1](https://github.com/SarJ2004/WhatsMyNote/commit/36ea9d11a34c24f7eb8c2c7bef3921e24e002e94))

## [0.1.2](https://github.com/SarJ2004/WhatsMyNote/compare/v0.1.1...v0.1.2) (2026-07-12)


### Bug Fixes

* update the envs to support local dev, improve post login message UI ([1f51761](https://github.com/SarJ2004/WhatsMyNote/commit/1f5176183b4d8c50bb463b91fddc58614f69d966))
* update the envs to support local dev, improve post login message UI ([3b97946](https://github.com/SarJ2004/WhatsMyNote/commit/3b979460691c47e3e1d18a8cbea4fb2f77e3d657))

## [0.1.1](https://github.com/SarJ2004/WhatsMyNote/compare/v0.1.0...v0.1.1) (2026-07-12)


### Documentation

* add logo asset ([ec49d20](https://github.com/SarJ2004/WhatsMyNote/commit/ec49d205bb9b17181a53e26b6e83fcae6676cfa6))

## [0.1.0] - 2026-07-12
### Added
- Initial PyPI release of the WhatsMyNote CLI.
- AI-powered natural language transaction extraction.
- Local conversational memory state management.
- Integration with Supabase (Auth) and PostgreSQL.
- Support for Accounts, Budgets, Incomes, Expenses, Lending, and Transfers.
