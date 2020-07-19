# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2020-xx-xx
### Added
- Login Health(SAML) over Basic Authentication
- Added [-H| --hostname] parameter for both checkmetadata and checkhealth
- Added [-p| --port] parameter for both checkmetadata and checkhealth
- Added [-b| --basic_auth] basic authentication login flow

### Fixed

### Changed
- Password short parameter changed from -p to -a
- Replaced [-u| --url] parameter with [-H| --hostname] and [-e| --endpoint]. Both of those are used to construct the metadata endpoint

### Removed
