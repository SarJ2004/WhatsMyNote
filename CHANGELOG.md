# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
