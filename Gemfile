# fastlane, for one job only: the manual production release.
#
# Ruby is deliberately confined here. Everything else in this repository that talks to Play is
# Python — the three `aab-*.py` artifact checks, the metadata generator, the release-note renderer —
# and the internal-track workflow never loads this file. What buys the exception is `supply`'s
# handling of one specific transaction: replacing a listing's screenshots means deleting the old set
# before uploading the new one, and a first-time script that dies between those two steps leaves the
# public listing with no screenshots at all. That failure is worth someone else's mileage.
source "https://rubygems.org"

gem "fastlane"
